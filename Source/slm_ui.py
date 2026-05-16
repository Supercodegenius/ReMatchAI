import os
from pathlib import Path
from difflib import SequenceMatcher

import pandas as pd
import streamlit as st
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

FAVICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "favicon.png.jpeg")

try:
    from Source.normalise import normalise_name
except Exception:
    try:
        from normalise import normalise_name
    except Exception:
        # Fallback keeps the app usable even if normalization module changes.
        def normalise_name(value: str) -> str:
            return value


def _safe_set_page_config(**kwargs) -> None:
    try:
        st.set_page_config(**kwargs)
    except Exception:
        # Ignore duplicate page config errors when launched from a parent app.
        pass


_safe_set_page_config(
    page_title="SLM Name Matching Tester",
    page_icon=FAVICON_PATH,
    layout="wide",
)


@st.cache_resource(show_spinner=False)
def resolve_model_dir() -> str:
    script_dir = Path(__file__).resolve().parent
    candidates = [
        Path("./outputs/biencoder"),
        script_dir / "outputs" / "biencoder",
        script_dir.parent / "outputs" / "biencoder",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return str(candidate.resolve())

    checked = "\n".join(f"- {c.resolve()}" for c in candidates)
    raise FileNotFoundError(
        "Could not find model directory. Expected one of:\n"
        f"{checked}\n"
        "Create/download the model artifacts into outputs/biencoder."
    )


@st.cache_resource(show_spinner=True)
def load_model():
    model_dir = resolve_model_dir()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,
        use_fast=True,
    )
    try:
        encoder = AutoModel.from_pretrained(
            model_dir,
            local_files_only=True,
            low_cpu_mem_usage=True,
        ).to(device)
    except Exception:
        encoder = AutoModel.from_pretrained(
            model_dir,
            local_files_only=True,
        ).to(device)
    encoder.eval()
    return tokenizer, encoder, device, model_dir


def _mean_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    # Sentence-transformer backbones work better with mask-aware mean pooling than raw CLS.
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = torch.sum(last_hidden_state * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


def embed(text: str, tokenizer, encoder, device) -> torch.Tensor:
    encoded = tokenizer(
        text,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=64,
    )
    encoded = {key: value.to(device) for key, value in encoded.items()}

    with torch.no_grad():
        output = encoder(**encoded)
        pooled = _mean_pool(output.last_hidden_state, encoded["attention_mask"])
        return F.normalize(pooled, p=2, dim=1)


def _embed_with_debug(text: str, tokenizer, encoder, device) -> tuple[torch.Tensor, dict[str, object]]:
    encoded = tokenizer(
        text,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=64,
    )
    token_ids = encoded["input_ids"][0].tolist()
    attention_values = encoded["attention_mask"][0].tolist()
    active_token_count = int(sum(attention_values))
    preview_token_ids = token_ids[: min(active_token_count, 12)]
    preview_tokens = tokenizer.convert_ids_to_tokens(preview_token_ids)

    encoded = {key: value.to(device) for key, value in encoded.items()}

    with torch.no_grad():
        output = encoder(**encoded)
        pooled = _mean_pool(output.last_hidden_state, encoded["attention_mask"])
        normalized = F.normalize(pooled, p=2, dim=1)

    debug_info = {
        "text": text,
        "input_ids_shape": list(encoded["input_ids"].shape),
        "attention_mask_shape": list(encoded["attention_mask"].shape),
        "active_token_count": active_token_count,
        "preview_tokens": preview_tokens,
        "last_hidden_state_shape": list(output.last_hidden_state.shape),
        "pooled_shape": list(pooled.shape),
        "normalized_embedding_shape": list(normalized.shape),
    }
    return normalized, debug_info


def _prepare_score_inputs(name_a: str, name_b: str, normalize: bool) -> dict[str, object]:
    original_a = name_a
    original_b = name_b
    trace_lines = [
        "1. Score Pair button clicked in Single Pair Test tab.",
        "2. slm_ui.py calls score_pair(name_a, name_b, tokenizer, encoder, device, normalize=True/False).",
    ]

    if normalize:
        normalized_a = normalise_name(original_a)
        normalized_b = normalise_name(original_b)
        trace_lines.append(
            f"3. normalise_name applied: A='{normalized_a}', B='{normalized_b}'."
        )

        use_original = (
            not normalized_a
            or not normalized_b
            or (
                normalized_a == normalized_b
                and original_a.strip().lower() != original_b.strip().lower()
            )
        )
        if use_original:
            a, b = original_a, original_b
            trace_lines.append(
                "4. Guard rejected normalized values, so original inputs were used for scoring."
            )
        else:
            a, b = normalized_a, normalized_b
            trace_lines.append(
                "4. Normalized values were accepted and used for scoring."
            )
    else:
        normalized_a = original_a
        normalized_b = original_b
        a, b = original_a, original_b
        trace_lines.append("3. Normalization disabled, so original inputs were used.")

    return {
        "original_a": original_a,
        "original_b": original_b,
        "normalized_a": normalized_a,
        "normalized_b": normalized_b,
        "scored_a": a,
        "scored_b": b,
        "trace_lines": trace_lines,
    }


def score_pair(name_a: str, name_b: str, tokenizer, encoder, device, normalize: bool) -> float:
    prepared = _prepare_score_inputs(name_a, name_b, normalize)
    a = str(prepared["scored_a"])
    b = str(prepared["scored_b"])

    emb_a = embed(a, tokenizer, encoder, device)
    emb_b = embed(b, tokenizer, encoder, device)
    score = float((emb_a * emb_b).sum().item())
    return max(-1.0, min(1.0, score))


def _lexical_guard_metrics(text_a: str, text_b: str) -> dict[str, float | int]:
    a = str(text_a or "").strip().lower()
    b = str(text_b or "").strip().lower()

    if not a or not b:
        return {
            "sequence_ratio": 0.0,
            "token_overlap_count": 0,
            "token_overlap_ratio": 0.0,
        }

    seq_ratio = float(SequenceMatcher(None, a, b).ratio())
    tokens_a = {tok for tok in a.split() if tok}
    tokens_b = {tok for tok in b.split() if tok}
    overlap_count = len(tokens_a & tokens_b)
    overlap_ratio = (
        overlap_count / max(1, min(len(tokens_a), len(tokens_b)))
        if tokens_a and tokens_b
        else 0.0
    )

    return {
        "sequence_ratio": seq_ratio,
        "token_overlap_count": overlap_count,
        "token_overlap_ratio": float(overlap_ratio),
    }


def classify_pair(score: float, threshold: float, scored_a: str, scored_b: str) -> str:
    metrics = _lexical_guard_metrics(scored_a, scored_b)

    # Guardrail: block obvious false positives from high embedding similarity.
    if (
        metrics["sequence_ratio"] < 0.45
        and metrics["token_overlap_count"] == 0
        and metrics["token_overlap_ratio"] == 0.0
    ):
        return "NO MATCH"

    return classify_score(score, threshold)


def score_pair_with_trace(
    name_a: str,
    name_b: str,
    tokenizer,
    encoder,
    device,
    normalize: bool,
    threshold: float,
) -> dict[str, object]:
    prepared = _prepare_score_inputs(name_a, name_b, normalize)
    scored_a = str(prepared["scored_a"])
    scored_b = str(prepared["scored_b"])

    emb_a, debug_a = _embed_with_debug(scored_a, tokenizer, encoder, device)
    emb_b, debug_b = _embed_with_debug(scored_b, tokenizer, encoder, device)
    score = max(-1.0, min(1.0, float((emb_a * emb_b).sum().item())))
    prediction = classify_pair(score, threshold, scored_a, scored_b)
    lexical_metrics = _lexical_guard_metrics(scored_a, scored_b)
    guard_triggered = (
        lexical_metrics["sequence_ratio"] < 0.45
        and lexical_metrics["token_overlap_count"] == 0
        and lexical_metrics["token_overlap_ratio"] == 0.0
    )

    trace_lines = list(prepared["trace_lines"])
    trace_lines.extend(
        [
            f"5. embed() tokenized A and B with max_length=64 on device '{device}'.",
            "6. AutoModel generated token embeddings for each input.",
            "7. _mean_pool() reduced token embeddings into sentence vectors.",
            "8. F.normalize() converted both sentence vectors to unit length.",
            f"9. Cosine similarity computed as {score:.6f}.",
            (
                f"10. Lexical guard metrics: sequence_ratio={float(lexical_metrics['sequence_ratio']):.3f}, "
                f"token_overlap_count={int(lexical_metrics['token_overlap_count'])}, "
                f"token_overlap_ratio={float(lexical_metrics['token_overlap_ratio']):.3f}."
            ),
            (
                f"11. classify_pair() applied threshold {threshold:.2f} -> {prediction}"
                + (" (guard forced NO MATCH)." if guard_triggered else ".")
            ),
        ]
    )

    return {
        **prepared,
        "score": score,
        "prediction": prediction,
        "trace_lines": trace_lines,
        "debug": {
            "device": device,
            "threshold": threshold,
            "lexical_guard_triggered": guard_triggered,
            "lexical_metrics": lexical_metrics,
            "name_a": debug_a,
            "name_b": debug_b,
        },
    }


def classify_score(score: float, threshold: float) -> str:
    return "MATCH" if score >= threshold else "NO MATCH"


def _find_best_threshold(scores: list[float], labels: list[int]) -> tuple[float, float, float]:
    # Evaluate all score cut points and return threshold maximizing F1, then accuracy.
    if not scores or len(scores) != len(labels):
        return 0.9, 0.0, 0.0

    unique_thresholds = sorted(set(scores))
    if not unique_thresholds:
        return 0.9, 0.0, 0.0

    best_threshold = unique_thresholds[0]
    best_f1 = -1.0
    best_accuracy = -1.0

    for threshold in unique_thresholds:
        tp = fp = tn = fn = 0
        for score, label in zip(scores, labels):
            pred = 1 if score >= threshold else 0
            if pred == 1 and label == 1:
                tp += 1
            elif pred == 1 and label == 0:
                fp += 1
            elif pred == 0 and label == 0:
                tn += 1
            else:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        accuracy = (tp + tn) / len(scores)

        if f1 > best_f1 or (f1 == best_f1 and accuracy > best_accuracy):
            best_f1 = f1
            best_accuracy = accuracy
            best_threshold = threshold

    return float(best_threshold), float(best_f1), float(best_accuracy)


def _parse_binary_label(value) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "match", "matched", "positive", "pos"}:
        return 1
    if text in {"0", "false", "f", "no", "n", "no match", "non-match", "nonmatch", "negative", "neg"}:
        return 0
    return None


st.title("SLM Name Matching Tester")
st.caption("Test pairwise and batch name matching using the local bi-encoder model.")

try:
    tokenizer, encoder, device, model_dir = load_model()
except Exception as exc:
    st.error(f"Model load failed: {exc}")
    st.stop()

col_a, col_b = st.columns([1, 1])
with col_a:
    st.info(f"Model directory: {model_dir}")
with col_b:
    st.info(f"Device: {device}")

if "slm_threshold" not in st.session_state:
    st.session_state["slm_threshold"] = 0.90

threshold = st.slider(
    "Match threshold",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    key="slm_threshold",
)
apply_normalization = st.checkbox("Apply normalization before scoring", value=True)

single_tab, batch_tab, calibration_tab = st.tabs([
    "Single Pair Test",
    "Batch CSV Test",
    "Threshold Calibration",
])

with single_tab:
    left, right = st.columns(2)
    with left:
        name_a = st.text_input("Name A", value="Swiss Re Europe SA")
    with right:
        name_b = st.text_input("Name B", value="Swiss Re UK Branch")

    if st.button("Score Pair", type="primary"):
        trace_result = score_pair_with_trace(
            name_a,
            name_b,
            tokenizer,
            encoder,
            device,
            apply_normalization,
            threshold,
        )
        st.session_state["slm_score_pair_trace"] = trace_result
        score = float(trace_result["score"])
        prediction = str(trace_result["prediction"])

        m1, m2 = st.columns(2)
        m1.metric("Cosine Similarity", f"{score:.6f}")
        m2.metric("Prediction", prediction)

        if apply_normalization:
            st.write("Normalized A:", trace_result["normalized_a"])
            st.write("Normalized B:", trace_result["normalized_b"])

with batch_tab:
    st.write("Upload a CSV with columns: name_a, name_b")
    uploaded = st.file_uploader("CSV file", type=["csv"])

    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")
            st.stop()

        required = {"name_a", "name_b"}
        if not required.issubset(df.columns):
            st.error("CSV must contain name_a and name_b columns.")
            st.stop()

        if st.button("Run Batch Scoring", type="primary"):
            result_df = df.copy()
            scores = []
            predictions = []

            for _, row in result_df.iterrows():
                a = "" if pd.isna(row["name_a"]) else str(row["name_a"])
                b = "" if pd.isna(row["name_b"]) else str(row["name_b"])
                score = score_pair(a, b, tokenizer, encoder, device, apply_normalization)
                prepared = _prepare_score_inputs(a, b, apply_normalization)
                scores.append(score)
                predictions.append(
                    classify_pair(
                        score,
                        threshold,
                        str(prepared["scored_a"]),
                        str(prepared["scored_b"]),
                    )
                )

            result_df["score"] = scores
            result_df["prediction"] = predictions

            st.dataframe(result_df, use_container_width=True)

            matched = int((result_df["prediction"] == "MATCH").sum())
            total = len(result_df)
            st.write(f"Matched rows: {matched}/{total}")

            csv_bytes = result_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Results CSV",
                data=csv_bytes,
                file_name="slm_name_matching_results.csv",
                mime="text/csv",
            )

with calibration_tab:
    st.write("Upload a labeled CSV with columns: name_a, name_b, label")
    calibration_file = st.file_uploader("Calibration CSV file", type=["csv"], key="slm_calibration_csv")

    if calibration_file is not None:
        try:
            calibration_df = pd.read_csv(calibration_file)
        except Exception as exc:
            st.error(f"Could not read calibration CSV: {exc}")
            st.stop()

        required_cols = {"name_a", "name_b", "label"}
        if not required_cols.issubset(calibration_df.columns):
            st.error("Calibration CSV must contain name_a, name_b, and label columns.")
            st.stop()

        st.caption("Label values accepted: 1/0, true/false, yes/no, match/no match.")
        st.dataframe(calibration_df.head(25), use_container_width=True)

        if st.button("Calibrate Threshold", type="primary", key="slm_calibrate_threshold"):
            eval_scores: list[float] = []
            eval_labels: list[int] = []
            total_rows = len(calibration_df)
            skipped_invalid_label = 0
            skipped_empty_pair = 0

            for _, row in calibration_df.iterrows():
                a = "" if pd.isna(row["name_a"]) else str(row["name_a"])
                b = "" if pd.isna(row["name_b"]) else str(row["name_b"])

                if not a.strip() and not b.strip():
                    skipped_empty_pair += 1
                    continue

                label = _parse_binary_label(row["label"])
                if label is None:
                    skipped_invalid_label += 1
                    continue

                eval_scores.append(score_pair(a, b, tokenizer, encoder, device, apply_normalization))
                eval_labels.append(label)

            used_rows = len(eval_scores)
            skipped_rows = total_rows - used_rows
            st.write(
                f"Calibration rows: used {used_rows}/{total_rows}, skipped {skipped_rows}."
            )
            if skipped_rows:
                st.caption(
                    f"Skipped due to invalid label: {skipped_invalid_label}; "
                    f"skipped due to empty pair: {skipped_empty_pair}."
                )

            if not eval_scores:
                st.error("No valid labeled rows found. Check labels and input pair values.")
            else:
                best_threshold, best_f1, best_accuracy = _find_best_threshold(eval_scores, eval_labels)
                st.session_state["slm_threshold"] = round(best_threshold, 2)
                st.success(
                    f"Calibrated threshold: {best_threshold:.4f} | "
                    f"F1: {best_f1:.4f} | Accuracy: {best_accuracy:.4f}"
                )
                st.info("The threshold slider has been updated using this calibration.")


trace_result = st.session_state.get("slm_score_pair_trace")
if trace_result is not None:
    st.divider()
    st.subheader("Score Pair Trace")
    st.caption("This trace shows the call flow and the values used for the most recent single-pair score.")

    detail_col_a, detail_col_b = st.columns(2)
    with detail_col_a:
        st.write("Original A:", trace_result["original_a"])
        st.write("Original B:", trace_result["original_b"])
        st.write("Normalized A:", trace_result["normalized_a"])
        st.write("Normalized B:", trace_result["normalized_b"])
    with detail_col_b:
        st.write("Scored A:", trace_result["scored_a"])
        st.write("Scored B:", trace_result["scored_b"])
        st.write("Score:", f"{float(trace_result['score']):.6f}")
        st.write("Prediction:", trace_result["prediction"])

    st.code("\n".join(str(line) for line in trace_result["trace_lines"]), language="text")

    with st.expander("Deep Debug Details"):
        debug = trace_result.get("debug", {})
        st.write("Device:", debug.get("device", ""))
        st.write("Threshold:", f"{float(debug.get('threshold', 0.0)):.2f}")

        debug_col_a, debug_col_b = st.columns(2)
        with debug_col_a:
            st.markdown("**Name A embedding debug**")
            st.json(debug.get("name_a", {}))
        with debug_col_b:
            st.markdown("**Name B embedding debug**")
            st.json(debug.get("name_b", {}))

