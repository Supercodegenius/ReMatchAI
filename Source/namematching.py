from __future__ import annotations

# Build with AI: AI-Powered Name Matching 
# Dashboards with Streamlit
# Name Matching Algorithms

# Developed By Ambuj Kumar

import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Literal

try:
    from Source.slm_country_codes import SLM_COUNTRY_CODE_MAP
except Exception:
    from slm_country_codes import SLM_COUNTRY_CODE_MAP

SLM_COUNTRY_CODE_MAP.update(
    {
        "ae": "united arab emirates",
        "are": "united arab emirates",
        "gb": "united kingdom",
        "gbr": "united kingdom",
        "kr": "south korea",
        "kor": "south korea",
        "kp": "north korea",
        "prk": "north korea",
        "ru": "russia",
        "rus": "russia",
        "sa": "saudi arabia",
        "sau": "saudi arabia",
        "sy": "syria",
        "syr": "syria",
        "tr": "turkey",
        "tur": "turkey",
        "tw": "taiwan",
        "twn": "taiwan",
        "us": "united states",
        "usa": "united states",
        "vn": "vietnam",
        "vnm": "vietnam",
    }
)

if TYPE_CHECKING:
    import pandas as pd

try:
    from rapidfuzz import distance as _rf_distance
    from rapidfuzz import fuzz as _rf_fuzz
    from rapidfuzz import process as _rf_process
except Exception:
    _rf_distance = None
    _rf_fuzz = None
    _rf_process = None

MatchMethod = Literal["exact", "fuzzy", "levenshtein", "jaro_winkler", "soundex", "ai_advanced", "slm"]
LevenshteinEngine = Literal["auto", "rapidfuzz", "python"]

_TERMINAL_LEGAL_SUFFIX_VARIANTS = {
    "a g": "ag",
    "c o": "co",
    "b v": "bv",
    "c o m p a n y": "company",
    "g m b h": "gmbh",
    "k g": "kg",
    "k g a a": "kgaa",
    "l l c": "llc",
    "l l p": "llp",
    "l p": "lp",
    "l t d": "ltd",
    "n v": "nv",
    "o y": "oy",
    "p l c": "plc",
    "p t e": "pte",
    "p v t": "pvt",
    "s p z o o": "spzoo",
    "s a": "sa",
    "s a r l": "sarl",
    "s a s": "sas",
    "s p a": "spa",
}

_DASH_RE = re.compile(r"[\u2010-\u2015\u2212\u002d]")
_NON_ALNUM_SPACE_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_TERMINAL_SUFFIX_TOKEN_MAP = {
    tuple(variant.split()): canonical
    for variant, canonical in _TERMINAL_LEGAL_SUFFIX_VARIANTS.items()
}
_MAX_TERMINAL_SUFFIX_TOKENS = max((len(tokens) for tokens in _TERMINAL_SUFFIX_TOKEN_MAP), default=0)


def _canonicalize_terminal_legal_suffix(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""

    tokens = normalized.split()
    if not tokens:
        return ""

    max_len = min(len(tokens), _MAX_TERMINAL_SUFFIX_TOKENS)
    for suffix_len in range(max_len, 0, -1):
        tail = tuple(tokens[-suffix_len:])
        canonical = _TERMINAL_SUFFIX_TOKEN_MAP.get(tail)
        if canonical is None:
            continue
        tokens = tokens[:-suffix_len] + [canonical]
        break
    return " ".join(tokens)

_LEGAL_SUFFIXES = {
    "ltd", "limited", "plc", "llc", "inc", "corp", "co", "company",
    "ag", "sa", "spa", "gmbh", "bv", "nv", "oy", "ab",
    "pte", "pvt", "kg", "kgaa", "sas", "sarl", "llp", "lp",
}


@lru_cache(maxsize=250000)
def _normalize_name_cached(raw_text: str) -> str:
    text = raw_text.strip().lower()
    text = _DASH_RE.sub(" ", text)  # replace hyphens/dashes with space before encoding
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = _NON_ALNUM_SPACE_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = _canonicalize_terminal_legal_suffix(text)
    tokens = [t for t in text.split() if t not in _LEGAL_SUFFIXES]
    return " ".join(tokens)


def normalize_name(value: str) -> str:
    """Normalize names for more reliable comparisons."""
    return _normalize_name_cached(str(value or ""))


def fuzzy_score(a: str, b: str) -> int:
    """Return similarity score in [0, 100]."""
    if _rf_fuzz is not None:
        return int(round(_rf_fuzz.ratio(a, b)))
    return int(round(100 * SequenceMatcher(None, a, b).ratio()))


def soundex_code(value: str) -> str:
    """Return 4-character Soundex code for a name."""
    letters = re.sub(r"[^a-z]", "", str(value).lower())
    if not letters:
        return ""

    first_letter = letters[0].upper()
    mapping = {
        "b": "1",
        "f": "1",
        "p": "1",
        "v": "1",
        "c": "2",
        "g": "2",
        "j": "2",
        "k": "2",
        "q": "2",
        "s": "2",
        "x": "2",
        "z": "2",
        "d": "3",
        "t": "3",
        "l": "4",
        "m": "5",
        "n": "5",
        "r": "6",
    }

    encoded_digits: list[str] = []
    prev_digit = mapping.get(letters[0], "")
    for ch in letters[1:]:
        digit = mapping.get(ch, "0")
        if digit != "0" and digit != prev_digit:
            encoded_digits.append(digit)
        prev_digit = digit

    code = first_letter + "".join(encoded_digits)
    return (code + "000")[:4]


def levenshtein_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(
                min(
                    prev[j] + 1,  # deletion
                    curr[j - 1] + 1,  # insertion
                    prev[j - 1] + cost,  # substitution
                )
            )
        prev = curr
    return prev[-1]


def levenshtein_distance_bounded(a: str, b: str, max_dist: int) -> int:
    """
    Compute Levenshtein distance with an upper bound.

    Returns max_dist + 1 when true distance is greater than max_dist.
    """
    if a == b:
        return 0
    if max_dist < 0:
        return max_dist + 1
    if not a:
        return len(b) if len(b) <= max_dist else max_dist + 1
    if not b:
        return len(a) if len(a) <= max_dist else max_dist + 1

    len_a = len(a)
    len_b = len(b)
    if abs(len_a - len_b) > max_dist:
        return max_dist + 1

    if len_a > len_b:
        a, b = b, a
        len_a, len_b = len_b, len_a

    inf = max_dist + 1

    prev_start = 0
    prev_end = min(len_b, max_dist)
    prev = list(range(prev_start, prev_end + 1))

    for i in range(1, len_a + 1):
        start = max(0, i - max_dist)
        end = min(len_b, i + max_dist)
        curr = [inf] * (end - start + 1)
        row_min = inf
        ai = a[i - 1]

        for j in range(start, end + 1):
            curr_idx = j - start

            if prev_start <= j <= prev_end:
                delete_cost = prev[j - prev_start] + 1
            else:
                delete_cost = inf

            if j == 0:
                insert_cost = i
            elif j - 1 >= start:
                insert_cost = curr[curr_idx - 1] + 1
            else:
                insert_cost = inf

            if prev_start <= j - 1 <= prev_end:
                substitute_cost = prev[j - 1 - prev_start] + (0 if ai == b[j - 1] else 1)
            else:
                substitute_cost = inf

            val = delete_cost if delete_cost < insert_cost else insert_cost
            if substitute_cost < val:
                val = substitute_cost

            curr[curr_idx] = val
            if val < row_min:
                row_min = val

        if row_min > max_dist:
            return inf

        prev = curr
        prev_start = start
        prev_end = end

    if prev_start <= len_b <= prev_end:
        result = prev[len_b - prev_start]
        return result if result <= max_dist else inf
    return inf


def jaro_similarity(a: str, b: str) -> float:
    """Compute Jaro similarity in [0.0, 1.0]."""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0

    a_len = len(a)
    b_len = len(b)
    match_window = max(a_len, b_len) // 2 - 1
    if match_window < 0:
        match_window = 0

    a_matches = [False] * a_len
    b_matches = [False] * b_len

    matches = 0
    for i, ca in enumerate(a):
        start = max(0, i - match_window)
        end = min(i + match_window + 1, b_len)
        for j in range(start, end):
            if b_matches[j]:
                continue
            if ca != b[j]:
                continue
            a_matches[i] = True
            b_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    a_match_chars: list[str] = [a[i] for i in range(a_len) if a_matches[i]]
    b_match_chars: list[str] = [b[j] for j in range(b_len) if b_matches[j]]

    transpositions = 0
    for ac, bc in zip(a_match_chars, b_match_chars):
        if ac != bc:
            transpositions += 1
    transpositions /= 2

    return (
        (matches / a_len)
        + (matches / b_len)
        + ((matches - transpositions) / matches)
    ) / 3.0


def jaro_winkler_similarity(a: str, b: str, *, prefix_scale: float = 0.1) -> float:
    """Compute Jaro-Winkler similarity in [0.0, 1.0]."""
    jaro = jaro_similarity(a, b)
    if jaro == 0.0:
        return 0.0

    max_prefix = 4
    prefix = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        prefix += 1
        if prefix >= max_prefix:
            break

    jw = jaro + prefix * prefix_scale * (1.0 - jaro)
    if jw > 1.0:
        return 1.0
    if jw < 0.0:
        return 0.0
    return jw


def jaro_winkler_score(a: str, b: str) -> int:
    """Return Jaro-Winkler similarity score in [0, 100]."""
    if _rf_distance is not None:
        return int(round(100 * _rf_distance.JaroWinkler.similarity(a, b)))
    return int(round(100 * jaro_winkler_similarity(a, b)))


def token_set_score(a: str, b: str) -> int:
    """Return token-overlap score in [0, 100]."""
    left_tokens = set(a.split())
    right_tokens = set(b.split())
    if not left_tokens and not right_tokens:
        return 100
    if not left_tokens or not right_tokens:
        return 0
    overlap = len(left_tokens & right_tokens)
    total = len(left_tokens | right_tokens)
    return int(round(100 * (overlap / total)))


def _token_set_score_from_sets(left_tokens: set[str], right_tokens: set[str]) -> int:
    if not left_tokens and not right_tokens:
        return 100
    if not left_tokens or not right_tokens:
        return 0
    overlap = len(left_tokens & right_tokens)
    total = len(left_tokens | right_tokens)
    return int(round(100 * (overlap / total)))


def _first_token(text: str) -> str:
    return text.split(" ", 1)[0] if text else ""


COMMON_COMPANY_TOKENS = {
    "ltd",
    "limited",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "llc",
    "plc",
    "pte",
    "pty",
    "gmbh",
    "sa",
    "sarl",
    "ag",
    "bv",
}


def _core_token_list(text: str) -> list[str]:
    tokens = text.split()
    if not tokens:
        return []
    return [tok for tok in tokens if tok not in COMMON_COMPANY_TOKENS]


def _expand_slm_country_code(text: str, target_exact_map: dict[str, str]) -> str:
    text = str(text).strip().lower()
    if not text:
        return text

    # Single-token: if the entire string is a country code that expands to a known target, swap it.
    if " " not in text:
        expanded = SLM_COUNTRY_CODE_MAP.get(text)
        if expanded and expanded in target_exact_map:
            return expanded
        return text

    # Multi-word phrase: expand any token that is a known country code within the phrase.
    tokens = text.split()
    expanded_tokens = []
    changed = False
    for tok in tokens:
        expansion = SLM_COUNTRY_CODE_MAP.get(tok)
        if expansion:
            expanded_tokens.append(expansion)
            changed = True
        else:
            expanded_tokens.append(tok)
    return " ".join(expanded_tokens) if changed else text


def _initials_from_tokens(tokens: list[str]) -> str:
    if not tokens:
        return ""
    initials = "".join(tok[0] for tok in tokens if tok)
    return initials[:6]


def _ai_weighted_score(
    fuzzy: int,
    jaro: int,
    token: int,
    *,
    first_token_bonus: bool,
) -> int:
    score = (0.45 * jaro) + (0.35 * fuzzy) + (0.20 * token)
    if first_token_bonus:
        score += 5
    score = max(0.0, min(100.0, score))
    return int(round(score))


def ai_advanced_score(a: str, b: str) -> int:
    """Weighted hybrid score designed for robust person-name matching."""
    fuzzy = fuzzy_score(a, b)
    jaro = jaro_winkler_score(a, b)
    token = token_set_score(a, b)

    left_first = _first_token(a)
    right_first = _first_token(b)
    return _ai_weighted_score(
        fuzzy,
        jaro,
        token,
        first_token_bonus=bool(left_first and left_first == right_first),
    )


def _slm_lexical_guard_passes(a: str, b: str) -> bool:
    if len(a) <= 2 or len(b) <= 2:
        return a == b

    seq_ratio = float(SequenceMatcher(None, a, b).ratio()) if a and b else 0.0
    tokens_a = {tok for tok in a.split() if tok}
    tokens_b = {tok for tok in b.split() if tok}
    overlap = len(tokens_a & tokens_b)
    overlap_ratio = (
        overlap / max(1, min(len(tokens_a), len(tokens_b)))
        if tokens_a and tokens_b
        else 0.0
    )
    return not (seq_ratio < 0.45 and overlap == 0 and overlap_ratio == 0.0)


@lru_cache(maxsize=1)
def _load_slm_runtime():
    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer
    try:
        import faiss
    except Exception:
        faiss = None

    script_dir = Path(__file__).resolve().parent
    candidates = [
        Path("./outputs/biencoder"),
        script_dir / "outputs" / "biencoder",
        script_dir.parent / "outputs" / "biencoder",
    ]

    model_dir = None
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            model_dir = str(candidate.resolve())
            break

    if model_dir is None:
        checked = "\n".join(str(c.resolve()) for c in candidates)
        raise FileNotFoundError(
            "Could not find SLM model directory. Checked:\n"
            f"{checked}"
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Force local model resolution to avoid remote hub checks during cold start.
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    encoder = AutoModel.from_pretrained(model_dir, local_files_only=True).to(device)
    encoder.eval()
    embedding_cache: dict[str, torch.Tensor] = {}

    def _mean_pool(last_hidden_state, attention_mask):
        mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        summed = torch.sum(last_hidden_state * mask, dim=1)
        counts = torch.clamp(mask.sum(dim=1), min=1e-9)
        return summed / counts

    def _embed_many(texts: list[str], batch_size: int = 128):
        if not texts:
            hidden = encoder.config.hidden_size
            return torch.empty((0, hidden), device=device)

        missing_texts = [text for text in dict.fromkeys(texts) if text not in embedding_cache]
        if missing_texts:
            with torch.inference_mode():
                for start in range(0, len(missing_texts), batch_size):
                    chunk = missing_texts[start:start + batch_size]
                    encoded = tokenizer(
                        chunk,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=64,
                    )
                    encoded = {k: v.to(device) for k, v in encoded.items()}
                    autocast_enabled = device == "cuda"
                    with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=autocast_enabled):
                        output = encoder(**encoded)
                        pooled = _mean_pool(output.last_hidden_state, encoded["attention_mask"])
                    normalized = F.normalize(pooled.float(), p=2, dim=1).detach().cpu()
                    for i, text in enumerate(chunk):
                        embedding_cache[text] = normalized[i]

        vectors = [embedding_cache[text] for text in texts]
        if not vectors:
            hidden = encoder.config.hidden_size
            return torch.empty((0, hidden), device=device)
        return torch.stack(vectors, dim=0).to(device)

    return {
        "torch": torch,
        "embed_many": _embed_many,
        "faiss": faiss,
    }


def warmup_slm_runtime() -> None:
    runtime = _load_slm_runtime()
    embed_many = runtime["embed_many"]
    embed_many(["slm warmup"])


def prime_slm_match_runtime(
    target_names: Iterable[str] | None = None,
    source_names: Iterable[str] | None = None,
) -> dict[str, int]:
    """
    Prime SLM runtime caches so first user-visible matching run is faster.

    This prepares model/runtime, text embeddings, and ANN index (when FAISS is available)
    using the currently loaded source/target names.
    """
    runtime = _load_slm_runtime()
    embed_many = runtime["embed_many"]

    def _normalize_unique(values: Iterable[str] | None) -> list[str]:
        if values is None:
            return []
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            normalized = normalize_name(str(raw or ""))
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered

    target_normalized = _normalize_unique(target_names)
    source_normalized = _normalize_unique(source_names)

    warmup_texts = ["slm warmup"]
    warmup_texts.extend(target_normalized)
    warmup_texts.extend(source_normalized)

    if warmup_texts:
        embed_many(warmup_texts)

    if target_normalized:
        _build_slm_ann_assets(tuple(target_normalized))

    return {
        "target_count": len(target_normalized),
        "source_count": len(source_normalized),
    }


@lru_cache(maxsize=2)
def _build_slm_ann_assets(target_normalized_tuple: tuple[str, ...]) -> dict[str, object] | None:
    if not target_normalized_tuple:
        return None

    runtime = _load_slm_runtime()
    faiss = runtime.get("faiss")
    if faiss is None:
        return None

    embed_many = runtime["embed_many"]
    try:
        target_embeddings = (
            embed_many(list(target_normalized_tuple))
            .detach()
            .cpu()
            .numpy()
            .astype("float32", copy=False)
        )
        ann_index = faiss.IndexFlatIP(target_embeddings.shape[1])
        ann_index.add(target_embeddings)
        return {
            "index": ann_index,
        }
    except Exception:
        return None


def _build_candidate_getter(target_normalized: list[str]) -> Callable[[str], list[int]]:
    """
    Return a fast candidate lookup function.

    For small target lists we keep full-scan behavior to preserve exact ranking.
    For larger lists we use lightweight blocking and bounded fallbacks.
    """
    target_count = len(target_normalized)
    if target_count <= 1500:
        all_indices = list(range(target_count))
        return lambda _src_n: all_indices

    first_char_index: dict[str, list[int]] = defaultdict(list)
    prefix_index: dict[str, list[int]] = defaultdict(list)
    token_index: dict[str, list[int]] = defaultdict(list)
    length_index: dict[int, list[int]] = defaultdict(list)

    for idx, tgt_n in enumerate(target_normalized):
        length_index[len(tgt_n)].append(idx)
        if not tgt_n:
            continue
        first_char_index[tgt_n[0]].append(idx)
        prefix_index[tgt_n[:3]].append(idx)
        for token in {tok for tok in tgt_n.split() if len(tok) >= 2}:
            token_index[token].append(idx)

    all_indices = list(range(target_count))

    max_candidates = 320
    max_pool = 640
    max_bucket_take = 200

    def get_candidates(src_n: str) -> list[int]:
        if not src_n:
            return all_indices

        seen: set[int] = set()
        ordered: list[int] = []

        def add_indices(indices: list[int], limit: int | None = None) -> None:
            if not indices:
                return
            added = 0
            for idx in indices:
                if idx in seen:
                    continue
                seen.add(idx)
                ordered.append(idx)
                added += 1
                if len(ordered) >= max_pool:
                    return
                if limit is not None and added >= limit:
                    return

        add_indices(prefix_index.get(src_n[:3], []))
        add_indices(first_char_index.get(src_n[:1], []))

        src_tokens = [tok for tok in src_n.split() if len(tok) >= 2]
        src_tokens.sort(key=len, reverse=True)
        for token in src_tokens[:4]:
            add_indices(token_index.get(token, []), max_bucket_take)
            if len(ordered) >= max_pool:
                break

        src_len = len(src_n)
        for delta in range(0, 3):
            near_lengths = [src_len - delta] if delta == 0 else [src_len - delta, src_len + delta]
            for length_val in near_lengths:
                if length_val < 0:
                    continue
                add_indices(length_index.get(length_val, []), max_bucket_take)
                if len(ordered) >= max_pool:
                    break
            if len(ordered) >= max_pool:
                break

        if not ordered:
            return all_indices

        if len(ordered) > max_candidates:
            return ordered[:max_candidates]
        return ordered

    return get_candidates


def match_names(
    source_names: Iterable[str],
    target_names: Iterable[str],
    *,
    method: MatchMethod,
    fuzzy_threshold: int = 75,
    lev_max_distance: int = 2,
    lev_engine: LevenshteinEngine = "auto",
) -> pd.DataFrame:
    """Return match results for each source name against a target list."""
    import pandas as pd

    src_series = pd.Series(list(source_names)).fillna("").astype(str)
    tgt_series = pd.Series(list(target_names)).fillna("").astype(str)

    src_norm = src_series.map(normalize_name)
    tgt_norm = tgt_series.map(normalize_name)

    right_lookup = pd.DataFrame(
        {"target_original": tgt_series, "target_normalized": tgt_norm}
    ).drop_duplicates(subset=["target_normalized"], keep="first")

    results: list[dict] = []

    if method == "exact":
        right_map = dict(
            zip(right_lookup["target_normalized"], right_lookup["target_original"])
        )
        for src, src_n in zip(src_series, src_norm):
            matched = right_map.get(src_n)
            results.append(
                {
                    "source_name": src,
                    "source_normalized": src_n,
                    "matched_name": matched if matched is not None else "",
                    "score": 100 if matched is not None else 0,
                    "is_match": matched is not None,
                }
            )
        return pd.DataFrame(results)

    target_originals = right_lookup["target_original"].tolist()
    target_normalized = right_lookup["target_normalized"].tolist()
    target_lengths = [len(name) for name in target_normalized]
    target_exact_map = dict(zip(target_normalized, target_originals))
    get_candidates = _build_candidate_getter(target_normalized)

    if method == "fuzzy":
        best_cache: dict[str, dict] = {}
        all_indices = list(range(len(target_originals)))
        use_rapidfuzz = _rf_process is not None and _rf_fuzz is not None
        target_first_chars = [name[:1] for name in target_normalized]
        fuzzy_shortlist_max = 250
        fuzzy_large_shortlist_trigger = 350
        for src, src_n in zip(src_series, src_norm):
            if src_n not in best_cache:
                exact_match = target_exact_map.get(src_n)
                if exact_match is not None:
                    best_cache[src_n] = {
                        "source_normalized": src_n,
                        "matched_name": exact_match,
                        "score": 100,
                        "is_match": True,
                    }
                    results.append({"source_name": src, **best_cache[src_n]})
                    continue

                candidate_indices = get_candidates(src_n)
                if not candidate_indices:
                    candidate_indices = all_indices
                elif (
                    not use_rapidfuzz
                    and len(candidate_indices) > fuzzy_large_shortlist_trigger
                ):
                    src_len = len(src_n)
                    src_first_char = src_n[:1]
                    candidate_indices = sorted(
                        candidate_indices,
                        key=lambda idx: (
                            abs(target_lengths[idx] - src_len),
                            0 if target_first_chars[idx] == src_first_char else 1,
                        ),
                    )[:fuzzy_shortlist_max]

                best_name = ""
                best_score = 0
                if use_rapidfuzz:
                    candidate_names = [target_normalized[idx] for idx in candidate_indices]
                    best_hit = _rf_process.extractOne(
                        src_n,
                        candidate_names,
                        scorer=_rf_fuzz.ratio,
                        processor=None,
                    )
                    if best_hit is not None:
                        best_score = int(round(best_hit[1]))
                        best_name = target_originals[candidate_indices[int(best_hit[2])]]
                else:
                    for idx in candidate_indices:
                        score = fuzzy_score(src_n, target_normalized[idx])
                        if score > best_score:
                            best_score = score
                            best_name = target_originals[idx]
                            if best_score == 100:
                                break
                best_cache[src_n] = {
                    "source_normalized": src_n,
                    "matched_name": best_name,
                    "score": best_score,
                    "is_match": best_score >= fuzzy_threshold,
                }

            results.append({"source_name": src, **best_cache[src_n]})
        return pd.DataFrame(results)

    if method == "soundex":
        soundex_lookup = right_lookup.copy()
        soundex_lookup["target_soundex"] = soundex_lookup["target_normalized"].map(soundex_code)
        right_map = dict(
            zip(soundex_lookup["target_soundex"], soundex_lookup["target_original"])
        )
        for src, src_n in zip(src_series, src_norm):
            src_soundex = soundex_code(src_n)
            matched = right_map.get(src_soundex)
            results.append(
                {
                    "source_name": src,
                    "source_normalized": src_n,
                    "source_soundex": src_soundex,
                    "matched_name": matched if matched is not None else "",
                    "score": 100 if matched is not None else 0,
                    "is_match": matched is not None,
                }
            )
        return pd.DataFrame(results)

    if method == "jaro_winkler":
        best_cache = {}
        all_indices = list(range(len(target_originals)))
        use_rapidfuzz = _rf_process is not None and _rf_distance is not None
        target_first_chars = [name[:1] for name in target_normalized]
        jw_shortlist_max = 250
        jw_large_shortlist_trigger = 350
        for src, src_n in zip(src_series, src_norm):
            if src_n not in best_cache:
                exact_match = target_exact_map.get(src_n)
                if exact_match is not None:
                    best_cache[src_n] = {
                        "source_normalized": src_n,
                        "matched_name": exact_match,
                        "score": 100,
                        "is_match": True,
                    }
                    results.append({"source_name": src, **best_cache[src_n]})
                    continue

                candidate_indices = get_candidates(src_n)
                if not candidate_indices:
                    candidate_indices = all_indices
                elif (
                    not use_rapidfuzz
                    and len(candidate_indices) > jw_large_shortlist_trigger
                ):
                    src_len = len(src_n)
                    src_first_char = src_n[:1]
                    candidate_indices = sorted(
                        candidate_indices,
                        key=lambda idx: (
                            abs(target_lengths[idx] - src_len),
                            0 if target_first_chars[idx] == src_first_char else 1,
                        ),
                    )[:jw_shortlist_max]

                best_name = ""
                best_score = 0
                if use_rapidfuzz:
                    candidate_names = [target_normalized[idx] for idx in candidate_indices]
                    best_hit = _rf_process.extractOne(
                        src_n,
                        candidate_names,
                        scorer=_rf_distance.JaroWinkler.similarity,
                        processor=None,
                    )
                    if best_hit is not None:
                        best_score = int(round(100 * float(best_hit[1])))
                        best_name = target_originals[candidate_indices[int(best_hit[2])]]
                else:
                    for idx in candidate_indices:
                        score = jaro_winkler_score(src_n, target_normalized[idx])
                        if score > best_score:
                            best_score = score
                            best_name = target_originals[idx]
                            if best_score == 100:
                                break
                best_cache[src_n] = {
                    "source_normalized": src_n,
                    "matched_name": best_name,
                    "score": best_score,
                    "is_match": best_score >= fuzzy_threshold,
                }

            results.append({"source_name": src, **best_cache[src_n]})
        return pd.DataFrame(results)

    if method == "levenshtein":
        best_cache = {}
        all_indices = list(range(len(target_originals)))
        lev_fallback_max = 80
        use_rapidfuzz = (
            lev_engine == "auto" and _rf_process is not None and _rf_distance is not None
        ) or (lev_engine == "rapidfuzz" and _rf_process is not None and _rf_distance is not None)
        for src, src_n in zip(src_series, src_norm):
            if src_n not in best_cache:
                exact_match = target_exact_map.get(src_n)
                if exact_match is not None:
                    best_cache[src_n] = {
                        "source_normalized": src_n,
                        "matched_name": exact_match,
                        "distance": 0,
                        "score": 100,
                        "is_match": True,
                    }
                    results.append({"source_name": src, **best_cache[src_n]})
                    continue

                best_name = ""
                best_distance = 10**9
                best_target_norm = ""

                candidate_indices = get_candidates(src_n)
                if not candidate_indices:
                    candidate_indices = all_indices
                elif len(candidate_indices) <= 256:
                    # For small candidate sets, sort by length to tighten bounds quickly.
                    src_len = len(src_n)
                    candidate_indices = sorted(
                        candidate_indices,
                        key=lambda idx: abs(len(target_normalized[idx]) - src_len),
                    )

                # For large datasets, use a (slightly) adaptive max distance to filter candidates early.
                src_len = len(src_n)
                adaptive_max_distance = lev_max_distance
                if src_len >= 12:
                    adaptive_max_distance = max(lev_max_distance, int(round(src_len * 0.12)))
                adaptive_max_distance = min(adaptive_max_distance, 12)
                distance_cutoff = None
                if adaptive_max_distance is not None and adaptive_max_distance >= 0 and candidate_indices:
                    filtered = [
                        idx
                        for idx in candidate_indices
                        if abs(target_lengths[idx] - src_len) <= adaptive_max_distance
                    ]
                    if filtered:
                        candidate_indices = filtered
                        distance_cutoff = adaptive_max_distance
                    else:
                        # Fall back to a small length-based shortlist to keep things fast.
                        candidate_indices = sorted(
                            candidate_indices,
                            key=lambda idx: abs(target_lengths[idx] - src_len),
                        )[:lev_fallback_max]

                if use_rapidfuzz:
                    candidate_names = [target_normalized[idx] for idx in candidate_indices]
                    best_hit = None
                    if candidate_names:
                        best_hit = _rf_process.extractOne(
                            src_n,
                            candidate_names,
                            scorer=_rf_distance.Levenshtein.distance,
                            processor=None,
                            score_cutoff=distance_cutoff,
                        )
                        if best_hit is None and distance_cutoff is not None:
                            best_hit = _rf_process.extractOne(
                                src_n,
                                candidate_names,
                                scorer=_rf_distance.Levenshtein.distance,
                                processor=None,
                            )
                    if best_hit is not None:
                        best_target_norm = best_hit[0]
                        best_distance = int(best_hit[1])
                        best_name = target_originals[candidate_indices[int(best_hit[2])]]
                else:
                    if distance_cutoff is not None:
                        best_distance = distance_cutoff + 1
                    for idx in candidate_indices:
                        tgt_n = target_normalized[idx]
                        if best_distance != 10**9 and abs(len(src_n) - len(tgt_n)) >= best_distance:
                            continue

                        if best_distance == 10**9:
                            dist = levenshtein_distance(src_n, tgt_n)
                        else:
                            dist = levenshtein_distance_bounded(src_n, tgt_n, best_distance - 1)
                            if dist >= best_distance:
                                continue

                        if dist < best_distance:
                            best_distance = dist
                            best_name = target_originals[idx]
                            best_target_norm = tgt_n
                            if best_distance == 0:
                                break
                    if best_name == "" and distance_cutoff is not None and candidate_indices:
                        best_distance = 10**9
                        for idx in candidate_indices:
                            tgt_n = target_normalized[idx]
                            dist = levenshtein_distance(src_n, tgt_n)
                            if dist < best_distance:
                                best_distance = dist
                                best_name = target_originals[idx]
                                best_target_norm = tgt_n
                                if best_distance == 0:
                                    break

                max_len = max(len(src_n), len(best_target_norm), 1)
                similarity_score = int(round(100 * (1 - (best_distance / max_len))))
                best_cache[src_n] = {
                    "source_normalized": src_n,
                    "matched_name": best_name,
                    "distance": best_distance,
                    "score": similarity_score,
                    "is_match": best_distance <= adaptive_max_distance,
                }

            results.append({"source_name": src, **best_cache[src_n]})
        return pd.DataFrame(results)

    if method == "ai_advanced":
        best_cache = {}
        target_first_tokens = [_first_token(name) for name in target_normalized]
        target_token_sets = [set(name.split()) for name in target_normalized]
        target_core_token_sets = [set(_core_token_list(name)) for name in target_normalized]
        target_initials = [
            _initials_from_tokens(_core_token_list(name) or name.split())
            for name in target_normalized
        ]
        ai_shortlist_max = 80
        ai_large_shortlist_trigger = 100
        ai_early_exit_score = 97
        all_indices = list(range(len(target_originals)))
        for src, src_n in zip(src_series, src_norm):
            if src_n not in best_cache:
                exact_match = target_exact_map.get(src_n)
                if exact_match is not None:
                    best_cache[src_n] = {
                        "source_normalized": src_n,
                        "matched_name": exact_match,
                        "score": 100,
                        "ai_fuzzy_score": 100,
                        "ai_jaro_winkler_score": 100,
                        "ai_token_score": 100,
                        "is_match": True,
                    }
                    results.append({"source_name": src, **best_cache[src_n]})
                    continue

                candidate_indices = get_candidates(src_n)
                if not candidate_indices:
                    candidate_indices = all_indices
                elif len(candidate_indices) > ai_large_shortlist_trigger:
                    if _rf_process is not None and _rf_fuzz is not None:
                        candidate_names = [target_normalized[idx] for idx in candidate_indices]
                        shortlist_hits = _rf_process.extract(
                            src_n,
                            candidate_names,
                            scorer=_rf_fuzz.ratio,
                            processor=None,
                            limit=ai_shortlist_max,
                        )
                        candidate_indices = [candidate_indices[int(hit[2])] for hit in shortlist_hits]
                    else:
                        src_len = len(src_n)
                        src_first_char = src_n[:1]
                        candidate_indices = sorted(
                            candidate_indices,
                            key=lambda idx: (
                                abs(target_lengths[idx] - src_len),
                                0 if target_normalized[idx][:1] == src_first_char else 1,
                            ),
                        )[:ai_shortlist_max]

                src_first_token = _first_token(src_n)
                src_token_list = src_n.split()
                src_token_set = set(src_token_list)
                src_core_list = _core_token_list(src_n)
                src_core_set = set(src_core_list)
                src_initials = _initials_from_tokens(src_core_list or src_token_list)
                best_name = ""
                best_score = 0
                best_fuzzy = 0
                best_jaro = 0
                best_token = 0
                for idx in candidate_indices:
                    tgt_n = target_normalized[idx]
                    fuzzy = fuzzy_score(src_n, tgt_n)
                    wratio = (
                        int(round(_rf_fuzz.WRatio(src_n, tgt_n)))
                        if _rf_fuzz is not None
                        else fuzzy
                    )
                    first_token_bonus = bool(
                        src_first_token and src_first_token == target_first_tokens[idx]
                    )
                    upper = max(fuzzy, wratio)
                    max_possible = int(round((0.35 * upper) + 60 + (5 if first_token_bonus else 0)))
                    if max_possible <= best_score:
                        continue

                    token = _token_set_score_from_sets(src_token_set, target_token_sets[idx])
                    core_token = _token_set_score_from_sets(
                        src_core_set, target_core_token_sets[idx]
                    )
                    jaro = jaro_winkler_score(src_n, tgt_n)
                    score = _ai_weighted_score(
                        max(fuzzy, wratio),
                        jaro,
                        max(token, core_token),
                        first_token_bonus=first_token_bonus,
                    )
                    if core_token >= 80:
                        score = min(100, score + 4)
                    if (
                        src_core_set
                        and target_core_token_sets[idx]
                        and (src_core_set <= target_core_token_sets[idx]
                             or target_core_token_sets[idx] <= src_core_set)
                        and min(len(src_core_set), len(target_core_token_sets[idx])) >= 2
                    ):
                        score = min(100, score + 6)
                    if src_initials and src_initials == target_initials[idx]:
                        score = min(100, score + 4)
                    if score > best_score:
                        best_score = score
                        best_name = target_originals[idx]
                        best_fuzzy = fuzzy
                        best_jaro = jaro
                        best_token = max(token, core_token)
                        if best_score >= ai_early_exit_score:
                            break
                best_cache[src_n] = {
                    "source_normalized": src_n,
                    "matched_name": best_name,
                    "score": best_score,
                    "ai_fuzzy_score": best_fuzzy,
                    "ai_jaro_winkler_score": best_jaro,
                    "ai_token_score": best_token,
                    "is_match": best_score >= fuzzy_threshold,
                }

            results.append({"source_name": src, **best_cache[src_n]})
        return pd.DataFrame(results)

    if method == "slm":
        slm_runtime = _load_slm_runtime()
        torch = slm_runtime["torch"]
        embed_many = slm_runtime["embed_many"]
        faiss = slm_runtime.get("faiss")
        best_cache = {}
        all_indices = list(range(len(target_originals)))
        slm_shortlist_max = 80
        slm_large_shortlist_trigger = 100
        slm_threshold = max(0.0, min(1.0, float(fuzzy_threshold) / 100.0))
        src_slm_query = src_norm.map(lambda n: _expand_slm_country_code(n, target_exact_map))
        unique_source_norm = list(dict.fromkeys(src_slm_query.tolist()))
        source_embeddings = embed_many(unique_source_norm)
        source_embedding_map = {
            name: source_embeddings[idx]
            for idx, name in enumerate(unique_source_norm)
        }

        ann_best_map: dict[str, tuple[int, float]] = {}
        if faiss is not None and target_normalized:
            try:
                ann_assets = _build_slm_ann_assets(tuple(target_normalized))
                if ann_assets is None:
                    raise RuntimeError("ANN assets unavailable")
                ann_index = ann_assets["index"]
                source_embeddings_np = (
                    source_embeddings.detach().cpu().numpy().astype("float32", copy=False)
                )
                ann_scores, ann_indices = ann_index.search(source_embeddings_np, 1)
                for idx, src_n in enumerate(unique_source_norm):
                    best_idx = int(ann_indices[idx][0])
                    best_score = float(ann_scores[idx][0])
                    ann_best_map[src_n] = (best_idx, best_score)
            except Exception:
                ann_best_map = {}

        candidate_map: dict[str, list[int]] = {}
        if not ann_best_map:
            required_target_indices: set[int] = set()
            for src_n in unique_source_norm:
                if src_n in target_exact_map:
                    continue

                candidate_indices = get_candidates(src_n)
                if not candidate_indices:
                    candidate_indices = all_indices
                elif len(candidate_indices) > slm_large_shortlist_trigger:
                    if _rf_process is not None and _rf_fuzz is not None:
                        candidate_names = [target_normalized[idx] for idx in candidate_indices]
                        shortlist_hits = _rf_process.extract(
                            src_n,
                            candidate_names,
                            scorer=_rf_fuzz.ratio,
                            processor=None,
                            limit=slm_shortlist_max,
                        )
                        candidate_indices = [candidate_indices[int(hit[2])] for hit in shortlist_hits]
                    else:
                        src_len = len(src_n)
                        src_first_char = src_n[:1]
                        candidate_indices = sorted(
                            candidate_indices,
                            key=lambda idx: (
                                abs(target_lengths[idx] - src_len),
                                0 if target_normalized[idx][:1] == src_first_char else 1,
                            ),
                        )[:slm_shortlist_max]

                candidate_map[src_n] = candidate_indices
                required_target_indices.update(candidate_indices)

            if required_target_indices:
                required_index_list = sorted(required_target_indices)
                required_target_texts = [target_normalized[idx] for idx in required_index_list]
                required_target_embeddings = embed_many(required_target_texts)
                required_index_to_pos = {
                    idx: pos for pos, idx in enumerate(required_index_list)
                }
                candidate_pos_map = {
                    src_n: [required_index_to_pos[idx] for idx in idx_list]
                    for src_n, idx_list in candidate_map.items()
                }
            else:
                required_target_embeddings = torch.empty(
                    (0, source_embeddings.shape[1]),
                    device=source_embeddings.device,
                )
                required_index_to_pos = {}
                candidate_pos_map = {}

        for src, src_n, src_query_n in zip(src_series, src_norm, src_slm_query):
            if src_n not in best_cache:
                exact_match = target_exact_map.get(src_query_n)
                if exact_match is not None:
                    best_cache[src_n] = {
                        "source_normalized": src_n,
                        "slm_query_normalized": src_query_n,
                        "matched_name": exact_match,
                        "score": 100,
                        "slm_score": 1.0,
                        "slm_raw_score": 1.0,
                        "slm_guard_passed": True,
                        "is_match": True,
                    }
                    results.append({"source_name": src, **best_cache[src_n]})
                    continue

                best_name = ""
                best_slm_score = -1.0
                best_target_norm = ""

                ann_hit = ann_best_map.get(src_query_n)
                if ann_hit is not None:
                    best_idx, best_slm_score = ann_hit
                    if 0 <= best_idx < len(target_originals):
                        if best_slm_score < -1.0:
                            best_slm_score = -1.0
                        elif best_slm_score > 1.0:
                            best_slm_score = 1.0
                        best_name = target_originals[best_idx]
                        best_target_norm = target_normalized[best_idx]
                else:
                    candidate_indices = candidate_map.get(src_query_n, all_indices)
                    src_embedding = source_embedding_map[src_query_n]
                    if candidate_indices:
                        candidate_positions = candidate_pos_map.get(src_query_n)
                        if candidate_positions is None:
                            candidate_positions = [required_index_to_pos[idx] for idx in candidate_indices]
                        candidate_tensor = required_target_embeddings[candidate_positions]
                        similarities = torch.matmul(candidate_tensor, src_embedding)
                        best_pos = int(torch.argmax(similarities).item())
                        best_idx = candidate_indices[best_pos]
                        best_slm_score = float(similarities[best_pos].item())
                        if best_slm_score < -1.0:
                            best_slm_score = -1.0
                        elif best_slm_score > 1.0:
                            best_slm_score = 1.0
                        best_name = target_originals[best_idx]
                        best_target_norm = target_normalized[best_idx]

                guard_ok = _slm_lexical_guard_passes(src_query_n, best_target_norm)
                score_0_100 = int(round((best_slm_score + 1.0) * 50.0))
                is_final_match = best_slm_score >= slm_threshold and guard_ok
                best_cache[src_n] = {
                    "source_normalized": src_n,
                    "slm_query_normalized": src_query_n,
                    "matched_name": best_name if is_final_match else "",
                    "score": score_0_100 if is_final_match else 0,
                    "slm_score": best_slm_score if is_final_match else 0.0,
                    "slm_raw_score": best_slm_score,
                    "slm_guard_passed": guard_ok,
                    "is_match": is_final_match,
                }

            results.append({"source_name": src, **best_cache[src_n]})
        return pd.DataFrame(results)

    raise ValueError(f"Unknown method: {method}")
