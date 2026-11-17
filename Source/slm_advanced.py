"""Advanced SLM capabilities: augmentation, calibration, explainability, attributes,
hierarchy, re-ranking, evaluation slices, multilingual folding and a persisted vector index."""
from __future__ import annotations

import json
import math
import random
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

LEGAL = {"ltd", "limited", "llc", "inc", "incorporated", "plc", "sa", "ag", "se", "nv", "bv", "gmbh",
         "co", "corp", "corporation", "company", "lp", "llp", "spa", "srl", "pte", "pty", "kk", "ab", "as"}
GEO = {"uk", "usa", "us", "europe", "asia", "america", "americas", "africa", "global", "international",
       "intl", "branch", "london", "bermuda", "singapore", "switzerland", "germany", "france", "japan",
       "canada", "australia", "ireland", "dubai", "hong", "kong", "zurich", "holdings", "group"}
ABBREV = {"reinsurance": "re", "insurance": "ins", "assurance": "assur", "international": "intl",
          "corporation": "corp", "company": "co", "limited": "ltd", "incorporated": "inc"}
INDEX_DIR = Path("outputs/slm_index")
GOLDEN_PATH = Path("data/golden_pairs.csv")
BAND_PATH = Path("outputs/review_band.json")


# ---- 9. multilingual / unicode folding -------------------------------------------------
def fold(text: str) -> str:
    """Accent-fold and lowercase so 'Münchener Rück' == 'munchener ruck'; common German digraphs mapped."""
    s = str(text).replace("ü", "ue").replace("ö", "oe").replace("ä", "ae").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def tokens(text: str) -> list[str]:
    return fold(text).split()


# ---- 5/6. attributes and hierarchy -----------------------------------------------------
def attributes(name: str) -> dict:
    t = tokens(name)
    return {"legal": [x for x in t if x in LEGAL], "geo": [x for x in t if x in GEO],
            "core": [x for x in t if x not in LEGAL and x not in GEO]}


def parent_key(name: str) -> str:
    """Group key: the core name without legal form, geography or branch words."""
    return " ".join(attributes(name)["core"]) or fold(name)


def build_hierarchy(names: list[str]) -> pd.DataFrame:
    df = pd.DataFrame({"name": names})
    df["parent"] = df["name"].map(parent_key)
    sizes = df.groupby("parent")["name"].transform("count")
    df["group_size"] = sizes
    return df.sort_values(["parent", "name"]).reset_index(drop=True)


def attribute_penalty(a: str, b: str) -> tuple[float, list[str]]:
    """Penalty for conflicting geography/legal form between otherwise similar names."""
    x, y = attributes(a), attributes(b)
    pen, why = 0.0, []
    gx, gy = set(x["geo"]), set(y["geo"])
    if gx and gy and not (gx & gy):
        pen += 0.15
        why.append(f"different geography ({', '.join(sorted(gx))} vs {', '.join(sorted(gy))})")
    lx, ly = set(x["legal"]), set(y["legal"])
    if lx and ly and not (lx & ly):
        pen += 0.05
        why.append(f"different legal form ({', '.join(sorted(lx))} vs {', '.join(sorted(ly))})")
    return pen, why


# ---- 8. explainability -----------------------------------------------------------------
def explain(a: str, b: str, slm_score: float | None = None) -> dict:
    ta, tb = tokens(a), tokens(b)
    sa, sb = set(ta), set(tb)
    shared = [t for t in ta if t in sb]
    only_a = [t for t in ta if t not in sb]
    only_b = [t for t in tb if t not in sa]
    core_a, core_b = set(attributes(a)["core"]), set(attributes(b)["core"])
    core_overlap = len(core_a & core_b) / max(1, len(core_a | core_b))
    pen, reasons = attribute_penalty(a, b)
    notes = []
    if shared:
        notes.append(f"shared tokens: {', '.join(shared)}")
    if only_a or only_b:
        notes.append(f"unmatched: {', '.join(only_a) or '-'} | {', '.join(only_b) or '-'}")
    notes += reasons
    if parent_key(a) == parent_key(b):
        notes.append("same parent entity after stripping legal/geo words")
    return {"shared": shared, "only_a": only_a, "only_b": only_b, "core_overlap": round(core_overlap, 3),
            "attribute_penalty": pen, "same_parent": parent_key(a) == parent_key(b),
            "slm_score": slm_score, "notes": notes}


# ---- 3. re-ranking (composite; optional LLM judge) -------------------------------------
def rerank(source: str, candidates: list[tuple[str, float]]) -> list[dict]:
    """Re-rank (name, slm_score) candidates using core-token overlap and attribute penalties."""
    out = []
    for name, s in candidates:
        e = explain(source, name, s)
        final = 0.65 * s + 0.35 * e["core_overlap"] - e["attribute_penalty"]
        out.append({"candidate": name, "slm_score": s, "final": round(max(0.0, final), 4), "notes": e["notes"]})
    return sorted(out, key=lambda r: r["final"], reverse=True)


def llm_judge(source: str, candidate: str) -> dict | None:
    """Optional second opinion via OpenAI (needs OPENAI_API_KEY). Returns None when unavailable."""
    import os
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI
        r = OpenAI().chat.completions.create(
            model=os.getenv("DECISION_LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content":
                       f'Are "{source}" and "{candidate}" the same legal reinsurance entity? '
                       'Reply JSON: {"same": true|false, "confidence": 0-1, "reason": "..."}'}],
            response_format={"type": "json_object"})
        return json.loads(r.choices[0].message.content)
    except Exception:
        return None


# ---- 2. augmentation / hard negatives --------------------------------------------------
def augment_pairs(names: list[str], seed: int = 42, per_name: int = 2) -> pd.DataFrame:
    """Synthetic positives (case/suffix/abbreviation/word-order) and hard negatives (geo/first-token swap)."""
    rnd = random.Random(seed)
    rows = []
    uniq = sorted({n for n in names if str(n).strip()})
    for n in uniq:
        toks = str(n).split()
        variants = {n.upper(), n.lower(), re.sub(r"[.,]", "", n)}
        abbr = " ".join(ABBREV.get(t.lower(), t) for t in toks)
        variants.add(abbr)
        if len(toks) > 2:
            variants.add(" ".join(toks[:-1]))
        for v in rnd.sample(sorted(variants - {n}), min(per_name, len(variants - {n}))):
            rows.append((n, v, 1))
        a = attributes(n)
        if a["core"]:
            other_geo = rnd.choice(sorted(GEO - set(a["geo"])))
            rows.append((n, f"{' '.join(a['core'])} {other_geo}".title(), 0))
        others = [m for m in uniq if parent_key(m) != parent_key(n)]
        same_tok = [m for m in others if tokens(m)[:1] == tokens(n)[:1]]
        if same_tok:
            rows.append((n, rnd.choice(same_tok), 0))
    return pd.DataFrame(rows, columns=["name_a", "name_b", "label"]).drop_duplicates()


# ---- 4. calibration and review band ----------------------------------------------------
def fit_calibrator(scores, labels, iters: int = 2000, lr: float = 0.5) -> dict:
    """Platt scaling: P(match) = sigmoid(a*score + b), fitted by gradient descent."""
    x = np.asarray(scores, float)
    y = np.asarray(labels, float)
    a, b = 1.0, 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(a * x + b)))
        a -= lr * float(np.mean((p - y) * x))
        b -= lr * float(np.mean(p - y))
    return {"a": float(a), "b": float(b)}


def calibrated_prob(score: float, cal: dict) -> float:
    return 1 / (1 + math.exp(-(cal["a"] * score + cal["b"])))


def review_band(scores, labels, target_precision: float = 0.98, target_reject_recall: float = 0.98) -> dict:
    """auto_accept above `hi` (precision >= target); auto_reject below `lo` (almost no true matches);
    anything in between goes to human review."""
    pairs = sorted(zip(map(float, scores), map(int, labels)))
    cand = sorted({s for s, _ in pairs})
    hi = max(cand) if cand else 1.0
    for t in cand:
        sel = [l for s, l in pairs if s >= t]
        if sel and sum(sel) / len(sel) >= target_precision:
            hi = t
            break
    lo = min(cand) if cand else 0.0
    total_pos = max(1, sum(l for _, l in pairs))
    for t in cand:
        if sum(l for s, l in pairs if s <= t) / total_pos <= (1 - target_reject_recall):
            lo = t
        else:
            break
    lo = min(lo, hi)
    n = max(1, len(pairs))
    review = sum(1 for s, _ in pairs if lo < s < hi)
    return {"auto_accept_at": hi, "auto_reject_at": lo, "review_share": round(review / n, 3)}


def decide(score: float, band: dict) -> str:
    if score >= band["auto_accept_at"]:
        return "auto_accept"
    if score <= band["auto_reject_at"]:
        return "auto_reject"
    return "review"


# ---- 7. evaluation with slices ---------------------------------------------------------
def _prf(scores, labels, thr):
    tp = sum(1 for s, l in zip(scores, labels) if s >= thr and l == 1)
    fp = sum(1 for s, l in zip(scores, labels) if s >= thr and l == 0)
    fn = sum(1 for s, l in zip(scores, labels) if s < thr and l == 1)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0}


def slice_of(a: str, b: str) -> str:
    pen, _ = attribute_penalty(a, b)
    if parent_key(a) == parent_key(b) and pen > 0:
        return "same_parent_diff_attribute"
    if tokens(a)[:1] == tokens(b)[:1]:
        return "shared_first_token"
    if fold(a) == fold(b):
        return "exact_after_fold"
    return "other"


def evaluate_slices(df: pd.DataFrame, scores, threshold: float) -> pd.DataFrame:
    """Per-slice precision/recall/F1 so a model can't pass by being good on easy pairs only."""
    d = df.reset_index(drop=True).copy()
    d["score"] = list(scores)
    d["slice"] = [slice_of(a, b) for a, b in zip(d["name_a"], d["name_b"])]
    rows = [{"slice": "ALL", "n": len(d), **_prf(d["score"], d["label"], threshold)}]
    for k, g in d.groupby("slice"):
        rows.append({"slice": k, "n": len(g), **_prf(g["score"], g["label"], threshold)})
    return pd.DataFrame(rows)


def passes_gate(candidate: pd.DataFrame, live: pd.DataFrame | None, tolerance: float = 0.02) -> tuple[bool, list[str]]:
    """Candidate must not regress overall or on any slice (with n >= 5) by more than `tolerance` F1."""
    if live is None:
        return True, []
    issues = []
    lv = live.set_index("slice")
    for _, r in candidate.iterrows():
        if r["slice"] in lv.index and r["n"] >= 5 and r["f1"] < lv.loc[r["slice"], "f1"] - tolerance:
            issues.append(f"{r['slice']}: F1 {r['f1']:.3f} < live {lv.loc[r['slice'], 'f1']:.3f}")
    return not issues, issues


def load_band() -> dict | None:
    p = BAND_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_band(band: dict) -> None:
    BAND_PATH.parent.mkdir(parents=True, exist_ok=True)
    BAND_PATH.write_text(json.dumps(band, indent=2), encoding="utf-8")


def embed_names(names: list[str], model_dir: Path) -> np.ndarray:
    """Embed names with the fine-tuned bi-encoder (mean pooled, L2 normalised)."""
    import torch
    from transformers import AutoTokenizer

    from Source import train_biencoder as tb

    tok_src = model_dir if (Path(model_dir) / "tokenizer_config.json").exists() else tb.MODEL_NAME
    tok = AutoTokenizer.from_pretrained(str(tok_src))
    model = tb.BiEncoder(str(model_dir)).to(tb.DEVICE).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(names), 64):
            enc = tok([fold(n) for n in names[i:i + 64]], padding=True, truncation=True,
                      max_length=64, return_tensors="pt").to(tb.DEVICE)
            out.append(model.encode(enc["input_ids"], enc["attention_mask"]).cpu().numpy())
    return np.vstack(out) if out else np.zeros((0, 384), dtype="float32")


def build_index_from_model(names: list[str], model_dir: Path = Path("outputs/biencoder")) -> int:
    names = sorted({n for n in names if str(n).strip()})
    save_index(names, embed_names(names, model_dir))
    return len(names)


# ---- 9. persisted vector index ---------------------------------------------------------
def save_index(names: list[str], embeddings: np.ndarray, index_dir: Path = INDEX_DIR) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    np.save(index_dir / "embeddings.npy", embeddings.astype("float32"))
    (index_dir / "names.json").write_text(json.dumps(names), encoding="utf-8")


def load_index(index_dir: Path = INDEX_DIR):
    if not (index_dir / "embeddings.npy").exists():
        return None
    return json.loads((index_dir / "names.json").read_text(encoding="utf-8")), np.load(index_dir / "embeddings.npy")


def search_index(query_vec: np.ndarray, names: list[str], emb: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    e = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    sims = e @ q
    top = np.argsort(-sims)[:k]
    return [(names[i], float(sims[i])) for i in top]
