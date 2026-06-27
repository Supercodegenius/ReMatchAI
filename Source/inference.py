import torch
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
from difflib import SequenceMatcher
import re
import unicodedata

try:
    from Source.namematching import (
        normalize_name as _normalize_name_prod,
        _slm_lexical_guard_passes as _slm_lexical_guard_prod,
    )
except Exception:
    try:
        from namematching import (
            normalize_name as _normalize_name_prod,
            _slm_lexical_guard_passes as _slm_lexical_guard_prod,
        )
    except Exception:
        _normalize_name_prod = None
        _slm_lexical_guard_prod = None

MODEL_DIR = "./outputs/biencoder"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
encoder = AutoModel.from_pretrained(MODEL_DIR).to(DEVICE)
encoder.eval()

_DASH_RE = re.compile(r"[\-\u2010-\u2015]")
_NON_ALNUM_SPACE_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_LEGAL_SUFFIXES = {
    "ltd", "limited", "plc", "llc", "inc", "corp", "co", "company",
    "ag", "sa", "spa", "gmbh", "bv", "nv", "oy", "ab",
    "pte", "pvt", "kg", "kgaa", "sas", "sarl", "llp", "lp",
}


def _mean_pool(last_hidden_state, attention_mask):
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = torch.sum(last_hidden_state * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


def _normalize_name_local(value: str) -> str:
    text = str(value or "").strip().lower()
    text = _DASH_RE.sub(" ", text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = _NON_ALNUM_SPACE_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    tokens = [t for t in text.split() if t not in _LEGAL_SUFFIXES]
    return " ".join(tokens)


def normalize_name(value: str) -> str:
    if _normalize_name_prod is not None:
        return _normalize_name_prod(str(value or ""))
    return _normalize_name_local(value)


def _slm_lexical_guard_local(a: str, b: str) -> bool:
    if len(a) <= 2 or len(b) <= 2:
        return a == b

    seq_ratio = float(SequenceMatcher(None, a, b).ratio()) if a and b else 0.0
    tokens_a = {tok for tok in a.split() if tok}
    tokens_b = {tok for tok in b.split() if tok}
    overlap = len(tokens_a & tokens_b)

    if overlap == 0:
        if len(tokens_a) == 1 and len(tokens_b) == 1:
            return seq_ratio >= 0.72
        if len(tokens_a) > 1 and len(tokens_b) > 1:
            return seq_ratio >= 0.65
        return seq_ratio >= 0.58

    return True


def slm_lexical_guard_passes(name_a: str, name_b: str) -> bool:
    if _slm_lexical_guard_prod is not None:
        return bool(_slm_lexical_guard_prod(name_a, name_b))
    return _slm_lexical_guard_local(name_a, name_b)


def embed(name):
    enc = tokenizer(
        name,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=64,
    )
    for k in enc:
        enc[k] = enc[k].to(DEVICE)

    with torch.no_grad():
        out = encoder(**enc)
        pooled = _mean_pool(out.last_hidden_state, enc["attention_mask"])
        return F.normalize(pooled, p=2, dim=1).cpu().numpy()[0]


def match_score_details(name_a, name_b):
    normalized_a = normalize_name(name_a)
    normalized_b = normalize_name(name_b)
    guard_ok = slm_lexical_guard_passes(normalized_a, normalized_b)

    emb_a = embed(normalized_a)
    emb_b = embed(normalized_b)
    raw_score = float((emb_a * emb_b).sum())  # cosine similarity
    raw_score = max(-1.0, min(1.0, raw_score))

    # Matcher-aligned behavior: block final acceptance when lexical guard fails.
    final_score = raw_score if guard_ok else -1.0
    return {
        "name_a": name_a,
        "name_b": name_b,
        "normalized_a": normalized_a,
        "normalized_b": normalized_b,
        "slm_raw_score": raw_score,
        "slm_guard_passed": guard_ok,
        "slm_score": final_score,
    }


def match_score(name_a, name_b):
    return float(match_score_details(name_a, name_b)["slm_score"])


if __name__ == "__main__":
    details = match_score_details("AXA XL Reinsurance Ltd", "AXA XL Re")
    print("Normalized A:", details["normalized_a"])
    print("Normalized B:", details["normalized_b"])
    print("Raw Similarity:", details["slm_raw_score"])
    print("Lexical Guard:", details["slm_guard_passed"])
    print("Final Similarity:", details["slm_score"])