"""Feedback -> training data -> gated retraining -> promotion/rollback for the SLM bi-encoder."""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from Source.namematching import normalize_name
except Exception:  # pragma: no cover
    try:
        from namematching import normalize_name
    except Exception:
        def normalize_name(value: str) -> str:
            return str(value).strip().lower()

OUTPUTS = Path("outputs")
FEEDBACK_DB = OUTPUTS / "match_feedback.db"
LIVE_DIR = OUTPUTS / "biencoder"
CANDIDATE_DIR = OUTPUTS / "biencoder_candidate"
BACKUP_DIR = OUTPUTS / "biencoder_backups"
HISTORY_PATH = OUTPUTS / "retrain_history.json"
BASE_TRAIN_PATH = Path("data/train.csv")
FEEDBACK_TRAIN_PATH = OUTPUTS / "feedback_train.csv"
HOLDOUT_PATH = OUTPUTS / "feedback_holdout.csv"

COLUMNS = ["name_a", "name_b", "label"]
FEEDBACK_WEIGHT = 3  # human labels are repeated so they outweigh the base set
MAX_CROSS_NEGATIVES_PER_SOURCE = 3


def load_feedback_labels(db_path: Path = FEEDBACK_DB) -> pd.DataFrame:
    """Latest verdict per (source, target) pair. Columns: name_a, name_b, label."""
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=COLUMNS)
    with sqlite3.connect(db_path) as conn:
        try:
            rows = pd.read_sql_query(
                "SELECT source_name, matched_name, is_correct FROM match_feedback ORDER BY id", conn
            )
        except Exception:
            return pd.DataFrame(columns=COLUMNS)
    if rows.empty:
        return pd.DataFrame(columns=COLUMNS)
    rows = rows.rename(columns={"source_name": "name_a", "matched_name": "name_b", "is_correct": "label"})
    rows["name_a"] = rows["name_a"].fillna("").astype(str).str.strip()
    rows["name_b"] = rows["name_b"].fillna("").astype(str).str.strip()
    rows = rows[(rows["name_a"] != "") & (rows["name_b"] != "")]
    rows["label"] = pd.to_numeric(rows["label"], errors="coerce")
    rows = rows[rows["label"].isin([0, 1])].copy()
    rows["label"] = rows["label"].astype(int)
    rows["_key"] = rows["name_a"].map(normalize_name) + "||" + rows["name_b"].map(normalize_name)
    rows = rows.drop_duplicates("_key", keep="last")
    return rows[COLUMNS].reset_index(drop=True)


def mine_hard_negatives(labels: pd.DataFrame) -> pd.DataFrame:
    """Pair each approved source with approved targets of *other* sources that share a first token.

    Those targets look similar but were confirmed to belong to a different entity.
    """
    pos = labels[labels["label"] == 1]
    if pos.empty:
        return pd.DataFrame(columns=COLUMNS)
    known = {(normalize_name(a), normalize_name(b)) for a, b in zip(labels["name_a"], labels["name_b"])}
    by_token: dict[str, list[tuple[str, str]]] = {}
    for a, b in zip(pos["name_a"], pos["name_b"]):
        toks = normalize_name(b).split()
        if toks:
            by_token.setdefault(toks[0], []).append((a, b))
    out = []
    for a, b in zip(pos["name_a"], pos["name_b"]):
        toks = normalize_name(b).split()
        if not toks:
            continue
        added = 0
        for other_a, other_b in by_token.get(toks[0], []):
            if normalize_name(other_b) == normalize_name(b):
                continue
            if (normalize_name(a), normalize_name(other_b)) in known:
                continue
            out.append({"name_a": a, "name_b": other_b, "label": 0})
            added += 1
            if added >= MAX_CROSS_NEGATIVES_PER_SOURCE:
                break
    return pd.DataFrame(out, columns=COLUMNS)


def build_training_sets(
    db_path: Path = FEEDBACK_DB,
    base_path: Path = BASE_TRAIN_PATH,
    holdout_frac: float = 0.2,
    seed: int = 42,
) -> dict:
    """Write feedback_train.csv (train) and feedback_holdout.csv (fixed evaluation set)."""
    labels = load_feedback_labels(db_path)
    holdout_parts, train_parts = [], []

    if not labels.empty:
        shuffled = labels.sample(frac=1.0, random_state=seed)
        n_hold = int(round(len(shuffled) * holdout_frac)) if len(shuffled) >= 10 else 0
        holdout_parts.append(shuffled.iloc[:n_hold])
        fb_train = shuffled.iloc[n_hold:]
        hard = mine_hard_negatives(fb_train)
        train_parts.append(pd.concat([fb_train] * FEEDBACK_WEIGHT + [hard]))

    base_rows = 0
    if Path(base_path).exists():
        base = pd.read_csv(base_path)
        if set(COLUMNS) <= set(base.columns):
            base = base[COLUMNS].dropna()
            base["label"] = pd.to_numeric(base["label"], errors="coerce")
            base = base[base["label"].isin([0, 1])]
            base_rows = len(base)
            base = base.sample(frac=1.0, random_state=seed)
            n_hold = max(1, int(len(base) * 0.05)) if len(base) >= 20 else 0
            holdout_parts.append(base.iloc[:n_hold])
            train_parts.append(base.iloc[n_hold:])

    train = pd.concat(train_parts, ignore_index=True) if train_parts else pd.DataFrame(columns=COLUMNS)
    holdout = pd.concat(holdout_parts, ignore_index=True) if holdout_parts else pd.DataFrame(columns=COLUMNS)
    train = train.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    train.to_csv(FEEDBACK_TRAIN_PATH, index=False)
    holdout.to_csv(HOLDOUT_PATH, index=False)
    return {
        "feedback_labels": int(len(labels)),
        "approved": int((labels["label"] == 1).sum()) if not labels.empty else 0,
        "rejected": int((labels["label"] == 0).sum()) if not labels.empty else 0,
        "base_rows": int(base_rows),
        "train_rows": int(len(train)),
        "holdout_rows": int(len(holdout)),
        "holdout_positives": int((holdout["label"] == 1).sum()) if len(holdout) else 0,
        "holdout_negatives": int((holdout["label"] == 0).sum()) if len(holdout) else 0,
    }


def load_history() -> list[dict]:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _append_history(entry: dict) -> None:
    hist = load_history()
    hist.append(entry)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(hist, indent=2), encoding="utf-8")


def new_labels_since_last_train(db_path: Path = FEEDBACK_DB) -> int:
    total = len(load_feedback_labels(db_path))
    trained = [h.get("feedback_labels", 0) for h in load_history() if h.get("status") in ("promoted", "rejected")]
    return max(0, total - (trained[-1] if trained else 0))


def _score_dir(model_dir: Path, holdout: pd.DataFrame) -> list[float]:
    from Source import slm_advanced as adv

    a = adv.embed_names(holdout["name_a"].astype(str).tolist(), model_dir)
    b = adv.embed_names(holdout["name_b"].astype(str).tolist(), model_dir)
    return (a * b).sum(axis=1).tolist()


def _evaluate_dir(model_dir: Path, holdout: pd.DataFrame) -> dict:
    from transformers import AutoTokenizer

    from Source import train_biencoder as tb

    tok_src = model_dir if (Path(model_dir) / "tokenizer_config.json").exists() else tb.MODEL_NAME
    tok = AutoTokenizer.from_pretrained(str(tok_src))
    model = tb.BiEncoder(str(model_dir)).to(tb.DEVICE)
    loader = tb.make_loader(tb.clean_pairs(holdout), tok)
    return tb.evaluate_model(model, loader)


def retrain_candidate(epochs: int = 3, lr: float = 1e-5, min_labels: int = 10) -> dict:
    """Fine-tune the live model on feedback into a candidate dir and compare with the live model."""
    from Source import train_biencoder as tb

    stats = build_training_sets()
    if stats["feedback_labels"] < min_labels:
        return {"status": "skipped", "reason": f"Need at least {min_labels} feedback labels (have {stats['feedback_labels']}).", **stats}
    if stats["holdout_rows"] < 2 or stats["holdout_positives"] == 0 or stats["holdout_negatives"] == 0:
        return {"status": "skipped", "reason": "Holdout needs both approved and rejected pairs; collect more feedback.", **stats}

    holdout = pd.read_csv(HOLDOUT_PATH)
    if CANDIDATE_DIR.exists():
        shutil.rmtree(CANDIDATE_DIR)
    base = str(LIVE_DIR) if (LIVE_DIR / "config.json").exists() else None

    summary = tb.main(
        train_path=FEEDBACK_TRAIN_PATH,
        output_dir=CANDIDATE_DIR,
        base_model=base,
        epochs=epochs,
        lr=lr,
        val_df=holdout,
    )
    cand = _evaluate_dir(CANDIDATE_DIR, holdout)
    live = _evaluate_dir(LIVE_DIR, holdout) if base else None
    result = {
        "status": "candidate_ready",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "candidate": {"f1": cand["f1"], "precision": cand["precision"], "recall": cand["recall"], "threshold": cand["threshold"]},
        "live": None if live is None else {"f1": live["f1"], "precision": live["precision"], "recall": live["recall"], "threshold": live["threshold"]},
        "epochs": epochs,
        **stats,
    }
    result["better"] = live is None or cand["f1"] >= live["f1"]

    from Source import slm_advanced as adv

    h = tb.clean_pairs(holdout).reset_index(drop=True)
    cand_scores = _score_dir(CANDIDATE_DIR, h)
    cand_slices = adv.evaluate_slices(h, cand_scores, cand["threshold"])
    live_slices = adv.evaluate_slices(h, _score_dir(LIVE_DIR, h), live["threshold"]) if live else None
    slice_ok, slice_issues = adv.passes_gate(cand_slices, live_slices)
    result["slices"] = cand_slices.to_dict("records")
    result["slice_issues"] = slice_issues
    result["better"] = bool(result["better"] and slice_ok)
    result["review_band"] = adv.review_band(cand_scores, h["label"].tolist())
    (CANDIDATE_DIR / "candidate_eval.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def promote_candidate(force: bool = False) -> dict:
    """Back up the live model and replace it with the candidate (only if it is not worse)."""
    eval_path = CANDIDATE_DIR / "candidate_eval.json"
    if not eval_path.exists():
        return {"status": "error", "reason": "No candidate available. Run retraining first."}
    result = json.loads(eval_path.read_text(encoding="utf-8"))
    if not result.get("better") and not force:
        result["status"] = "rejected"
        _append_history(result)
        return result

    backup = None
    if LIVE_DIR.exists():
        backup = BACKUP_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(LIVE_DIR, backup)
        shutil.rmtree(LIVE_DIR)
    shutil.copytree(CANDIDATE_DIR, LIVE_DIR, ignore=shutil.ignore_patterns("candidate_eval.json"))

    # Record the threshold re-tuned on the holdout so the runtime can use it.
    summary_path = LIVE_DIR / "training_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    summary["best_threshold"] = float(result["candidate"]["threshold"])
    summary["retrained_from_feedback"] = result["timestamp"]
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if result.get("review_band"):
        from Source import slm_advanced as adv

        adv.save_band(result["review_band"])

    result.update(status="promoted", backup=str(backup) if backup else None)
    _append_history(result)
    return result


def list_backups() -> list[str]:
    return sorted((p.name for p in BACKUP_DIR.iterdir() if p.is_dir()), reverse=True) if BACKUP_DIR.exists() else []


def rollback(backup_name: str | None = None) -> dict:
    names = list_backups()
    if not names:
        return {"status": "error", "reason": "No backups available."}
    name = backup_name or names[0]
    src = BACKUP_DIR / name
    if not src.exists():
        return {"status": "error", "reason": f"Backup {name} not found."}
    if LIVE_DIR.exists():
        shutil.rmtree(LIVE_DIR)
    shutil.copytree(src, LIVE_DIR)
    entry = {"status": "rolled_back", "timestamp": datetime.now().isoformat(timespec="seconds"), "restored": name}
    _append_history(entry)
    return entry
