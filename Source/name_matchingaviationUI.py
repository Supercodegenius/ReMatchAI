# Build with AI: AI-Powered Name Matching
# Dashboards with Streamlit
# Name Matching UI Building with Streamlit and Python

# Developed By Ambuj Kumar

import os
import runpy
import base64
import json
import importlib.util
import re
import sqlite3
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import get_args

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

FAVICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "favicon.png.jpeg")


def _safe_set_page_config(**kwargs) -> None:
    try:
        st.set_page_config(**kwargs)
    except Exception:
        # Ignore duplicate page config errors when launched from a parent app.
        pass


_safe_set_page_config(
    page_title="Name Matching",
    page_icon=FAVICON_PATH,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --nm-page-bg: #e8edf6;
        --nm-hero-blue-deep: #13347f;
        --nm-hero-blue-mid: #1b4aa8;
        --nm-hero-blue-soft: #2558be;
        --nm-ink: #132b54;
        --nm-muted: #4e6180;
        --nm-chip-bg: rgba(255,255,255,0.15);
        --nm-chip-border: rgba(255,255,255,0.35);
      }
      .stApp {
        background:
          radial-gradient(1100px 500px at 12% -10%, #f5f9ff 0%, transparent 58%),
          radial-gradient(900px 420px at 100% 0%, #dde8fb 0%, transparent 55%),
          linear-gradient(180deg, #edf2f9 0%, var(--nm-page-bg) 55%);
      }
      html, body { margin: 0; }

            /* Keep Streamlit header visible so the sidebar expand toggle is always available. */
      div[data-testid="stDecoration"],
      #MainMenu,
      footer {
        display: none !important;
      }

            /* Keep toolbar visible for sidebar expand/collapse control. */
            div[data-testid="stToolbar"] {
                display: block !important;
            }

            /* Remove visible white header strip while keeping header controls available. */
            header[data-testid="stHeader"] {
                background: transparent !important;
                height: 0 !important;
                border: 0 !important;
            }

            /* Remove Deploy button from header area. */
            button[data-testid="stAppDeployButton"] {
                display: none !important;
            }

            /* Keep collapsed sidebar expander visible on the light header. */
            div[data-testid="collapsedControl"] {
                z-index: 1000 !important;
                opacity: 1 !important;
                visibility: visible !important;
            }
            div[data-testid="collapsedControl"] button,
            button[aria-label="Show sidebar"],
            button[title="View sidebar"] {
                opacity: 1 !important;
                visibility: visible !important;
                color: #12356f !important;
                border: 1px solid rgba(18, 53, 111, 0.35) !important;
                background: rgba(255, 255, 255, 0.92) !important;
                border-radius: 0.5rem !important;
            }
            div[data-testid="collapsedControl"] svg,
            button[aria-label="Show sidebar"] svg,
            button[title="View sidebar"] svg {
                fill: #12356f !important;
                stroke: #12356f !important;
            }
            button[data-testid="stExpandSidebarButton"] {
                position: fixed !important;
                top: 0.55rem !important;
                left: 0.6rem !important;
                z-index: 1001 !important;
                width: 2.2rem !important;
                height: 2.2rem !important;
                border-radius: 0.6rem !important;
                border: 1px solid rgba(18, 53, 111, 0.38) !important;
                background: rgba(255, 255, 255, 0.96) !important;
                box-shadow: 0 3px 10px rgba(18, 53, 111, 0.14) !important;
                color: #12356f !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                opacity: 1 !important;
                visibility: visible !important;
            }
            button[data-testid="stExpandSidebarButton"] span,
            button[data-testid="stExpandSidebarButton"] div {
                color: #12356f !important;
                font-size: 1.25rem !important;
                line-height: 1 !important;
            }

      div[data-testid="stAppViewContainer"],
      section.main,
      div[data-testid="stAppViewContainer"] > .main,
      section[data-testid="stMain"],
      div[data-testid="stMain"] {
        margin-top: 0 !important;
                                padding-top: 0.35rem !important;
      }

      div[data-testid="stMainBlockContainer"],
      .block-container {
                padding-top: 0.25rem !important;
        padding-bottom: 1.6rem;
      }
      .nm-hero {
        padding: 0.95rem 1.05rem 0.9rem 1.05rem;
        border: 1px solid rgba(20,50,112,0.2);
        border-radius: 0.65rem;
        background: linear-gradient(135deg, var(--nm-hero-blue-deep), var(--nm-hero-blue-mid) 52%, var(--nm-hero-blue-soft));
        box-shadow: 0 14px 28px rgba(15, 38, 86, 0.25);
        margin-bottom: 1.15rem;
      }
      .nm-hero h1 {
        margin: 0 0 0.2rem 0;
        font-size: 1.45rem;
        color: #f7fbff;
        line-height: 1.15;
      }
      .nm-hero-title-row {
        display: flex;
        align-items: baseline;
        justify-content: flex-start;
        gap: 0.45rem;
        flex-wrap: nowrap;
      }
      .nm-powered-by {
        color: #ff4d4d;
        font-size: 1.45rem;
        font-weight: 700;
        line-height: 1.15;
        white-space: nowrap;
        animation: nm-rainbow-blink 3.4s linear infinite;
      }
      .nm-powered-by a {
        color: inherit;
        text-decoration: underline;
      }
      .nm-powered-by a:hover {
        color: #ffffff;
      }
      @keyframes nm-rainbow-blink {
        0%   { color: #ff4d4d; opacity: 1; }
        58%  { color: #ff4d4d; opacity: 1; }
        64%  { color: #ff9f43; opacity: 0.2; }
        70%  { color: #ffe66d; opacity: 1; }
        76%  { color: #2ed573; opacity: 0.2; }
        82%  { color: #1e90ff; opacity: 1; }
        88%  { color: #5352ed; opacity: 0.2; }
        94%  { color: #a55eea; opacity: 1; }
        100% { color: #ff4d4d; opacity: 0.2; }
      }
      .nm-hero p {
        margin: 0;
        color: rgba(245, 251, 255, 0.9);
        max-width: 72rem;
        font-size: 1.02rem;
      }
      .nm-chip-row {
        margin-top: 0.7rem;
        display: flex;
        gap: 0.55rem;
        flex-wrap: wrap;
      }
      .nm-chip {
        border: 1px solid var(--nm-chip-border);
        border-radius: 999px;
        padding: 0.2rem 0.6rem;
        background: var(--nm-chip-bg);
        color: #ecf5ff;
        font-weight: 600;
      }
      h2, h3, .st-emotion-cache-10trblm, .st-emotion-cache-16idsys p {
        color: var(--nm-ink);
      }
      div[data-testid="stMetric"] {
        border: 1px solid rgba(47, 77, 131, 0.18);
        border-radius: 0.6rem;
        padding: 0.9rem 1rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(245,249,255,0.8));
        box-shadow: 0 6px 16px rgba(16, 40, 84, 0.08);
      }
      div[data-testid="stDataFrame"] {
        border: 1px solid rgba(47, 77, 131, 0.18);
        border-radius: 0.5rem;
        overflow: hidden;
        box-shadow: 0 6px 16px rgba(16, 40, 84, 0.08);
      }
      div[data-testid="stDataFrame"] [role="columnheader"] {
        font-weight: 700 !important;
      }
      div[data-testid="stFileUploaderDropzone"] {
        background: linear-gradient(180deg, #f9fbff 0%, #f2f6fc 100%);
        border: 1px solid #aec0dc;
        border-radius: 0.85rem;
      }
      div[data-testid="stFileUploaderDropzone"] section {
        color: #1b335e;
      }
      div[data-testid="stFileUploaderDropzone"] small {
        color: #657a99;
      }
      div[data-testid="stFileUploaderDropzone"] button {
        border-radius: 0.7rem;
        border: 1px solid #b5c2d6;
        background: linear-gradient(180deg, #f7faff, #edf2f8);
        color: #1b335e;
      }
      div[data-testid="stAlert"] {
        border-radius: 0.75rem;
        border: 1px solid #b7d2c4;
        box-shadow: 0 4px 12px rgba(31, 104, 77, 0.09);
      }
      div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 0.9rem;
        border: 1px solid #afc0d9 !important;
        background: linear-gradient(180deg, #f2f6fb 0%, #ebf1f8 100%);
        box-shadow: 0 8px 20px rgba(20, 46, 93, 0.07);
      }
      .nm-muted { opacity: 0.7; font-size: 0.88rem; }
      .nm-chat-shell {
        margin-top: 1rem;
        border: 1px solid rgba(20,40,80,0.12);
        border-radius: 1rem;
        padding: 0.95rem 1rem 1rem 1rem;
        background: linear-gradient(180deg, #f3f7fc 0%, #e8eef6 100%);
        box-shadow: 0 10px 20px rgba(20, 46, 93, 0.08);
      }
      .nm-chat-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.8rem;
        margin-bottom: 0.25rem;
      }
      .nm-chat-head h3 {
        margin: 0;
        color: #132b54;
        font-size: 1.05rem;
      }
      .nm-chat-badge {
        border: 1px solid #9eb2d6;
        border-radius: 999px;
        padding: 0.16rem 0.78rem;
        background: #dfe7f3;
        color: #2a4f8b;
        font-size: 0.86rem;
        font-weight: 600;
      }
      div[data-testid="stSidebar"] div[role="radiogroup"] label {
        background: #343a4c;
        border-radius: 999px;
        padding: 0.55rem 0.9rem;
        margin-bottom: 0.7rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 6px 14px rgba(22, 28, 42, 0.18);
      }
      div[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #2d3342;
      }
      div[data-testid="stSidebar"] div[role="radiogroup"] label div {
        color: #f2f5fb !important;
        font-weight: 700;
        font-size: 0.98rem;
      }
      div[data-testid="stSidebar"] div[role="radiogroup"] input:checked + div {
        color: #ffffff !important;
      }
            div[data-testid="stSidebarUserContent"] {
                padding-top: 0.3rem;
            }
            .nm-sidebar-menu {
                margin-top: -0.65rem;
                margin-bottom: 0.25rem;
            }
            div[data-testid="stSidebar"] .stButton > button {
                justify-content: flex-start;
                text-align: left;
                padding: 0.3rem 1rem;
                min-height: 2.05rem;
            }
      div[data-testid="stSidebar"] .stButton > button span {
        width: 100%;
        text-align: left;
      }
            div[data-testid="stSidebar"] .stButton {
                margin-bottom: 0.2rem;
            }
            div[data-testid="stSidebar"] .stButton:first-of-type {
                margin-top: -0.15rem;
            }
      .nm-chat-quick {
        margin-top: 0.35rem;
        margin-bottom: 0.25rem;
        color: #132b54;
        font-size: 1.08rem;
        font-weight: 700;
      }
      .nm-muted { color: var(--nm-muted); opacity: 1; }
      .stButton > button[kind="primary"] {
        border: 0;
        border-radius: 0.6rem;
        background: linear-gradient(90deg, #143f98 0%, #1e54bc 100%);
        color: #f6faff;
        box-shadow: 0 8px 18px rgba(20, 63, 152, 0.28);
      }
      .stButton > button[kind="primary"]:hover {
        filter: brightness(1.03);
      }
      .nm-footer {
        margin-top: 1.2rem;
        padding-top: 0.6rem;
        border-top: 1px solid rgba(19, 43, 84, 0.2);
        text-align: center;
        color: #4e6180;
        font-size: 0.86rem;
      }
            @media (max-width: 900px) {
                .block-container {
                    padding-left: 0.8rem !important;
                    padding-right: 0.8rem !important;
                }
                .nm-hero {
                    padding: 0.9rem;
                    margin-bottom: 0.95rem;
                }
                .nm-hero-title-row,
                .nm-chat-head {
                    align-items: flex-start;
                    flex-wrap: wrap;
                }
                .nm-hero h1,
                .nm-powered-by {
                    font-size: 1.1rem;
                    line-height: 1.25;
                }
                .nm-powered-by {
                    white-space: normal;
                }
                .nm-hero p {
                    font-size: 0.95rem;
                }
                div[data-testid="stMain"] div[data-testid="stHorizontalBlock"] {
                    flex-direction: column;
                    gap: 0.75rem;
                }
                div[data-testid="stMain"] div[data-testid="column"] {
                    width: 100% !important;
                    min-width: 100% !important;
                    flex: 1 1 100% !important;
                }
            }
      /* Hide Streamlit footer/status, keep header so sidebar toggle is visible */
      footer,
      div[data-testid="stDecoration"],
      div[data-testid="stStatusWidget"] {
        visibility: hidden;
        height: 0;
        position: fixed;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("_from_main_matcher_ui", False):
        st.markdown(
                """
                <div class="nm-hero">
                    <div class="nm-hero-title-row">
                        <h1 style="margin:0;">AI Powered Name Matching</h1>
                        <div class="nm-powered-by">By BrainCal Tech Team <a href="https://braincal.com" target="_blank" rel="noopener noreferrer">https://braincal.com</a></div>
                    </div>
                    <p>Enterprise-grade name matching with ENCCLT, FNCCLT, SNCCLT, JNCCLT, LNCCLT, AINCCLT, and SLM methods.</p>
                    <div class="nm-chip-row">
                        <span class="nm-chip">Operational Data Quality</span>
                        <span class="nm-chip">Customer Record Matching</span>
                        <span class="nm-chip">AI Assistant Enabled</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
        )

BASE_DIR = os.path.dirname(__file__)
DEMO_SOURCE_PATH = os.path.join(BASE_DIR, "demo_data", "source_names.csv")
DEMO_TARGET_PATH = os.path.join(BASE_DIR, "demo_data", "target_names.csv")
DATA_UPLOAD_DB_PATH = os.path.join(BASE_DIR, "data_upload.db")
FEEDBACK_DB_PATH = os.path.join(BASE_DIR, "..", "outputs", "match_feedback.db")
CONTROL_SETTINGS_XML_PATH = os.path.join(BASE_DIR, "control_settings.xml")

CONTROL_REGISTRY = [
    {"id": "data_upload_button", "type": "button", "label": "Data Upload"},
    {"id": "data_preview_button", "type": "button", "label": "Data Preview"},
    {"id": "run_name_matching_button", "type": "button", "label": "Run Name Matching"},
    {"id": "clear_chat_button", "type": "button", "label": "Clear chat"},
    {"id": "best_method_button", "type": "button", "label": "Best method?"},
    {"id": "tune_threshold_button", "type": "button", "label": "Tune threshold"},
    {"id": "explain_mismatch_button", "type": "button", "label": "Explain mismatch"},
    {"id": "show_data_previews_checkbox", "type": "checkbox", "label": "Show data previews"},
    {"id": "show_only_matches_checkbox", "type": "checkbox", "label": "Show only matched rows"},
    {"id": "include_location_checkbox", "type": "checkbox", "label": "Include Schedule"},
    {"id": "include_industry_checkbox", "type": "checkbox", "label": "Include Airline Code"},
    {"id": "include_app_context_checkbox", "type": "checkbox", "label": "Include current app context"},
]


def _default_control_settings() -> dict[str, bool]:
    return {control["id"]: True for control in CONTROL_REGISTRY}


def _load_control_settings(xml_path: str = CONTROL_SETTINGS_XML_PATH) -> dict[str, bool]:
    settings = _default_control_settings()
    if not os.path.exists(xml_path):
        _save_control_settings(settings, xml_path)
        return settings

    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        _save_control_settings(settings, xml_path)
        return settings

    for control_elem in root.findall("control"):
        control_id = control_elem.get("id", "").strip()
        enabled_value = str(control_elem.get("enabled", "true")).strip().lower()
        if control_id in settings:
            settings[control_id] = enabled_value in {"1", "true", "yes", "on"}
    return settings


def _save_control_settings(settings: dict[str, bool], xml_path: str = CONTROL_SETTINGS_XML_PATH) -> None:
    root = ET.Element("controls")
    for control in CONTROL_REGISTRY:
        control_id = control["id"]
        ET.SubElement(
            root,
            "control",
            attrib={
                "id": control_id,
                "type": control["type"],
                "label": control["label"],
                "enabled": "true" if bool(settings.get(control_id, True)) else "false",
            },
        )

    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


control_settings = _load_control_settings()


def _is_control_enabled(control_id: str) -> bool:
    return bool(control_settings.get(control_id, True))


def _file_mtime_iso(path: str) -> str:
    try:
        return pd.Timestamp.fromtimestamp(os.path.getmtime(path)).isoformat()
    except OSError:
        return "unknown"


def _clean_display_path(path: str) -> str:
    normalized = os.path.normpath(path)
    try:
        return os.path.relpath(normalized, start=os.getcwd())
    except ValueError:
        return normalized


def _slm_health_status() -> dict[str, object]:
    dependency_status = {
        "torch": importlib.util.find_spec("torch") is not None,
        "transformers": importlib.util.find_spec("transformers") is not None,
    }
    missing_deps = [name for name, is_ok in dependency_status.items() if not is_ok]

    script_dir = os.path.dirname(__file__)
    model_candidates = [
        os.path.join(".", "outputs", "biencoder"),
        os.path.join(script_dir, "outputs", "biencoder"),
        os.path.join(os.path.dirname(script_dir), "outputs", "biencoder"),
    ]
    available_model_dir = next(
        (candidate for candidate in model_candidates if os.path.isdir(candidate)),
        None,
    )

    health: dict[str, object] = {
        "dependency_status": dependency_status,
        "missing_dependencies": missing_deps,
        "model_candidates": model_candidates,
        "available_model_dir": available_model_dir,
        "backend_import_error": None,
        "method_supported": True,
        "reason": None,
        "ready": False,
    }

    if missing_deps:
        health["reason"] = (
            "SLM dependencies are missing: "
            + ", ".join(missing_deps)
            + ". Add them to requirements.txt and redeploy."
        )
        return health

    try:
        from Source import name_matchingaviation as nm
    except Exception as exc:
        health["backend_import_error"] = str(exc)
        health["reason"] = f"SLM backend import failed: {exc}"
        return health

    match_method = getattr(nm, "MatchMethod", None)
    supported_methods = set(get_args(match_method)) if match_method is not None else set()
    method_supported = not supported_methods or "slm" in supported_methods
    health["method_supported"] = method_supported
    if not method_supported:
        health["reason"] = "SLM Match is unavailable in this deployment."
        return health

    if available_model_dir is None:
        health["reason"] = "SLM model files are not deployed."
        return health

    health["ready"] = True
    return health


def _slm_matching_available() -> tuple[bool, str | None]:
    health = _slm_health_status()
    return bool(health.get("ready", False)), health.get("reason")


def _parse_ctx_value(app_context: str, key: str) -> str:
    """Extract a value from the app_context string by key label."""
    for line in app_context.splitlines():
        if line.strip().lower().startswith(key.lower()):
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return ""


def _extract_name_pair(question: str) -> tuple[str, str] | None:
    """
    Try to extract two quoted names from the question, e.g.:
      'why does "AXA XL" match "AXA XL Re"?'
      "explain 'British Airways' vs 'BA'"
    Returns (name_a, name_b) or None if not found.
    """
    import re as _re
    patterns = [
        r'["\u2018\u2019\u201c\u201d]([^"\']+)["\u2018\u2019\u201c\u201d]\s*(?:vs?\.?|and|versus|match|compare)?\s*["\u2018\u2019\u201c\u201d]([^"\']+)["\u2018\u2019\u201c\u201d]',
        r"'([^']+)'\s*(?:vs?\.?|and|versus|match|compare)?\s*'([^']+)'",
    ]
    for pat in patterns:
        m = _re.search(pat, question, _re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    return None


def _slm_trace_explanation(name_a: str, name_b: str, threshold_str: str) -> str:
    """Run score_pair_with_trace on the SLM and return a human-readable explanation."""
    try:
        from Source.slm_ui import load_model, score_pair_with_trace
    except ImportError:
        try:
            from slm_ui import load_model, score_pair_with_trace
        except ImportError:
            return (
                f"Could not load the SLM model to score **{name_a}** vs **{name_b}**. "
                "Ensure the model files are present in `outputs/biencoder/`."
            )

    try:
        threshold = float(threshold_str) if threshold_str else 0.75
        # SLM threshold is stored as 0-100 in the UI slider but used as 0-1 internally
        if threshold > 1.0:
            threshold = threshold / 100.0
    except ValueError:
        threshold = 0.75

    try:
        tokenizer, encoder, device, _ = load_model()
        trace = score_pair_with_trace(
            name_a, name_b, tokenizer, encoder, device,
            normalize=True, threshold=threshold
        )
    except Exception as exc:
        return f"SLM scoring failed for **{name_a}** vs **{name_b}**: `{type(exc).__name__}: {exc}`"

    score = float(trace["score"])
    prediction = trace["prediction"]
    norm_a = trace["normalized_a"]
    norm_b = trace["normalized_b"]
    lm = trace["debug"]["lexical_metrics"]
    guard = trace["debug"]["lexical_guard_triggered"]
    seq_ratio = float(lm["sequence_ratio"])
    tok_overlap = int(lm["token_overlap_count"])
    tok_ratio = float(lm["token_overlap_ratio"])

    verdict = "✅ **MATCH**" if prediction == "MATCH" else "❌ **NO MATCH**"

    lines = [
        f"### SLM Analysis: `{name_a}` vs `{name_b}`",
        "",
        f"**Verdict**: {verdict}  |  **Score**: `{score:.4f}`  |  **Threshold**: `{threshold:.2f}`",
        "",
        "#### Normalisation",
        f"- Input A → `{norm_a}`",
        f"- Input B → `{norm_b}`",
        "",
        "#### Lexical Guard Metrics",
        f"- Sequence similarity: `{seq_ratio:.3f}` {'⚠️ low' if seq_ratio < 0.45 else '✔'}",
        f"- Shared token count: `{tok_overlap}`",
        f"- Token overlap ratio: `{tok_ratio:.3f}`",
    ]

    if guard:
        lines += [
            "",
            "#### Why no match?",
            "The **lexical guard** blocked this pair. The names share no common tokens and have "
            f"very low character-level similarity (`{seq_ratio:.3f}`), so the SLM's high embedding "
            "score was overridden to prevent a false positive.",
        ]
    elif prediction == "NO MATCH":
        lines += [
            "",
            "#### Why no match?",
            f"The cosine similarity `{score:.4f}` is below the threshold `{threshold:.2f}`. "
            "The names are semantically different in the embedding space.",
        ]
    else:
        lines += [
            "",
            "#### Why matched?",
            f"Cosine similarity `{score:.4f}` ≥ threshold `{threshold:.2f}` and the lexical guard "
            f"passed (sequence ratio `{seq_ratio:.3f}`, token overlap `{tok_overlap}`). "
            "The SLM considers these names semantically equivalent.",
        ]

    return "\n".join(lines)


def _generate_slm_explanation(user_question: str, app_context: str = "") -> str:
    """
    Generate a specific, data-driven explanation using the SLM model.
    All processing is local — no external API calls.
    """
    question_lower = user_question.lower()

    # --- Specific pair scoring: detect quoted name pairs in the question ---
    pair = _extract_name_pair(user_question)
    if pair:
        threshold_str = _parse_ctx_value(app_context, "Fuzzy threshold")
        return _slm_trace_explanation(pair[0], pair[1], threshold_str)

    # --- Questions about the current results ---
    result_df: pd.DataFrame | None = st.session_state.get("result_df")
    current_method = _parse_ctx_value(app_context, "Selected method")
    current_threshold = _parse_ctx_value(app_context, "Fuzzy threshold")
    rows_in_result = _parse_ctx_value(app_context, "Rows in result")
    method_key_val = _parse_ctx_value(app_context, "Method key")

    if "how many" in question_lower or "count" in question_lower or "summary" in question_lower:
        if result_df is not None and not result_df.empty:
            total = len(result_df)
            matched = int(result_df["is_match"].sum()) if "is_match" in result_df.columns else "N/A"
            unmatched = total - matched if matched != "N/A" else "N/A"
            match_rate = f"{matched / total * 100:.1f}%" if matched != "N/A" and total > 0 else "N/A"
            return (
                f"### Current Result Summary\n\n"
                f"| Metric | Value |\n|---|---|\n"
                f"| Total rows | `{total}` |\n"
                f"| Matched | `{matched}` |\n"
                f"| Unmatched | `{unmatched}` |\n"
                f"| Match rate | `{match_rate}` |\n"
                f"| Method used | `{current_method}` |\n"
                f"| Threshold | `{current_threshold}` |"
            )
        return "No match results are available yet. Run matching first, then ask for a summary."

    if "unmatched" in question_lower or "failed" in question_lower or "did not match" in question_lower:
        if result_df is not None and "is_match" in result_df.columns:
            unmatched_df = result_df[~result_df["is_match"]]
            count = len(unmatched_df)
            if count == 0:
                return f"All `{len(result_df)}` rows matched successfully with method **{current_method}** at threshold `{current_threshold}`."
            # Show first few unmatched source names
            src_col = next((c for c in result_df.columns if "source" in c.lower() or c.lower() in ("name_a", "name a")), None)
            if src_col:
                samples = unmatched_df[src_col].dropna().head(10).tolist()
                sample_list = "\n".join(f"- `{n}`" for n in samples)
                return (
                    f"**{count}** rows did not match (out of `{len(result_df)}` total) "
                    f"using **{current_method}** at threshold `{current_threshold}`.\n\n"
                    f"**Sample unmatched source names:**\n{sample_list}\n\n"
                    f"To investigate a specific pair, ask: *why does \"NameA\" not match \"NameB\"?*"
                )
            return (
                f"**{count}** rows did not match out of `{len(result_df)}` total. "
                f"Method: **{current_method}**, threshold: `{current_threshold}`."
            )
        return "No result data available. Run matching first."

    if "best method" in question_lower or "which method" in question_lower:
        ctx = f" (you are currently using **{current_method}**)" if current_method else ""
        return (
            f"**Recommended methods by use case{ctx}:**\n\n"
            "| Use Case | Recommended Method |\n|---|---|\n"
            "| Exact name matching | `Exact` |\n"
            "| Slight typos / abbreviations | `SLM` or `Fuzzy` |\n"
            "| Phonetic variants (e.g. colour/color) | `Soundex` |\n"
            "| Aviation/ICAO code expansion | `SLM Adaptive` |\n"
            "| Highest semantic accuracy | `SLM` or `Vector Similarity` |\n\n"
            "The **SLM** method uses your locally trained transformer to embed names and compare "
            "them as vectors — best for messy, real-world data with abbreviations and word-order variations."
            + (f"\n\n**App context:**\n{app_context}" if app_context else "")
        )

    if "threshold" in question_lower or "tune" in question_lower or "false positive" in question_lower or "false negative" in question_lower:
        ctx_threshold = f"Your current threshold is `{current_threshold}`." if current_threshold else ""
        score_dist = ""
        if result_df is not None and "score" in result_df.columns:
            scores = result_df["score"].dropna()
            if not scores.empty:
                score_dist = (
                    f"\n\n**Score distribution in current results** (`{len(scores)}` rows):\n"
                    f"- Min: `{scores.min():.4f}` | Max: `{scores.max():.4f}` | Mean: `{scores.mean():.4f}` | Median: `{scores.median():.4f}`"
                )
        return (
            f"**Threshold tuning guide:**\n\n"
            f"{ctx_threshold}\n\n"
            "| Threshold range | Effect |\n|---|---|\n"
            "| `0.85 – 1.00` | Very strict — only near-identical names match |\n"
            "| `0.70 – 0.84` | Balanced — catches common variations |\n"
            "| `0.55 – 0.69` | Lenient — higher recall, more false positives |\n\n"
            "**Tip:** Score specific borderline pairs by asking: "
            "*\"why does \\\"Name A\\\" match \\\"Name B\\\"?\"* to see the exact SLM score."
            + score_dist
        )

    if "explain" in question_lower or "how does" in question_lower or "how it works" in question_lower:
        return (
            "### How the SLM Matcher Works\n\n"
            "1. **Normalisation** — Legal suffixes (Ltd, GmbH, Plc…), punctuation, and accents are stripped. "
            "Aviation codes are expanded to full names.\n"
            "2. **Tokenisation** — Each normalised name is split into subword tokens (max 64 tokens).\n"
            "3. **Embedding** — Your fine-tuned transformer encodes each token sequence into a dense vector.\n"
            "4. **Mean Pooling** — Token vectors are averaged (attention-mask-weighted) to produce a single sentence vector.\n"
            "5. **Cosine Similarity** — The two unit-normalised vectors are dot-producted to get a score in `[-1, 1]`.\n"
            "6. **Lexical Guard** — If sequence ratio < 0.45 AND zero shared tokens, the pair is forced to NO MATCH "
            "regardless of embedding score (prevents false positives).\n"
            "7. **Threshold Decision** — Score ≥ threshold → **MATCH**, else **NO MATCH**.\n\n"
            "To score a specific pair, ask: *why does \"Name A\" match \"Name B\"?*"
            + (f"\n\n**Current config:** {app_context}" if app_context else "")
        )

    if "troubleshoot" in question_lower or "not match" in question_lower or "mismatch" in question_lower or "miss" in question_lower:
        ctx_threshold = f"current threshold `{current_threshold}`" if current_threshold else "your threshold"
        return (
            f"**Troubleshooting mismatches** (method: **{current_method or 'unknown'}**, {ctx_threshold}):\n\n"
            "1. **Score too low** — Lower the threshold slightly. Ask the assistant to score the specific pair to see exactly where it falls.\n"
            "2. **Lexical guard triggered** — If names share zero words and have very different character patterns, "
            "the guard blocks the match. Consider adding the shared context (e.g. country, IATA code) as extra columns.\n"
            "3. **Normalisation mismatch** — Unusual legal suffixes or special characters may not normalise correctly. "
            "Check the 'Score Pair' trace in the SLM Tester tab.\n"
            "4. **Wrong method** — Phonetic variants may need `Soundex`; structural variations need `SLM`.\n\n"
            "**Quick debug:** Ask *\"why does \\\"Name A\\\" not match \\\"Name B\\\"?\"* and the SLM will score it live."
            + (f"\n\n**Rows in current result:** {rows_in_result}" if rows_in_result else "")
        )

    # Fallback: still contextual based on what's loaded
    loaded_info = ""
    if result_df is not None:
        total = len(result_df)
        matched = int(result_df["is_match"].sum()) if "is_match" in result_df.columns else "?"
        loaded_info = f"\n\nYou have **{total}** rows loaded with **{matched}** matches using **{current_method}** at threshold `{current_threshold}`."
    return (
        "I can answer specific questions about your name matching results.\n\n"
        "**Try asking:**\n"
        "- *Why does \"British Airways\" match \"BA\"?*  ← scores the pair live with the SLM\n"
        "- *How many rows did not match?*\n"
        "- *How do I tune the threshold?*\n"
        "- *Explain how the SLM matcher works*\n"
        "- *Troubleshoot my mismatches*"
        + loaded_info
    )


@st.cache_data(show_spinner=False)
def _read_table_from_bytes(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(BytesIO(file_bytes))
    return pd.read_excel(BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def _read_demo_csv(path: str, file_mtime: float) -> pd.DataFrame:
    _ = file_mtime  # cache key includes mtime so updates invalidate cache
    return pd.read_csv(path)


def _uploaded_file_signature(uploaded_file) -> str:
    file_id = getattr(uploaded_file, "file_id", None)
    return f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}:{file_id}"


def read_table(uploaded_file):
    if uploaded_file is None:
        return None

    cache_key = "_uploaded_table_cache"
    cache = st.session_state.setdefault(cache_key, {})
    signature = _uploaded_file_signature(uploaded_file)

    if signature in cache:
        return cache[signature]

    df = _read_table_from_bytes(uploaded_file.getvalue(), uploaded_file.name)
    cache[signature] = df

    # Keep cache bounded for long sessions with many uploads.
    if len(cache) > 10:
        oldest_key = next(iter(cache))
        del cache[oldest_key]

    return df


def _init_data_upload_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_upload_batches (
                upload_id TEXT PRIMARY KEY,
                source_filename TEXT NOT NULL,
                uploaded_at_utc TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                column_count INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_upload_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id TEXT NOT NULL,
                row_number INTEGER NOT NULL,
                row_data_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_upload_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id TEXT NOT NULL,
                source_column TEXT NOT NULL,
                destination_column TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _save_data_upload_to_db(
    source_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    source_filename: str,
    db_path: str = DATA_UPLOAD_DB_PATH,
) -> tuple[str, int]:
    _init_data_upload_db(db_path)
    upload_id = pd.Timestamp.utcnow().strftime("upload_%Y%m%d%H%M%S%f")
    upload_time = pd.Timestamp.utcnow().isoformat()

    safe_source_df = source_df.astype(object).where(pd.notna(source_df), None)
    row_payloads = [
        (upload_id, idx + 1, json.dumps(record, ensure_ascii=True))
        for idx, record in enumerate(safe_source_df.to_dict(orient="records"))
    ]
    mapping_payloads = [
        (upload_id, str(row["Source Column"]), str(row["Destination Column"]))
        for _, row in mapping_df.iterrows()
    ]

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO data_upload_batches (
                upload_id, source_filename, uploaded_at_utc, row_count, column_count
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (upload_id, source_filename, upload_time, len(source_df), len(source_df.columns)),
        )
        conn.executemany(
            """
            INSERT INTO data_upload_rows (upload_id, row_number, row_data_json)
            VALUES (?, ?, ?)
            """,
            row_payloads,
        )
        conn.executemany(
            """
            INSERT INTO data_upload_mappings (upload_id, source_column, destination_column)
            VALUES (?, ?, ?)
            """,
            mapping_payloads,
        )
        conn.commit()

    return upload_id, len(row_payloads)


def _compose_match_values(
    df: pd.DataFrame,
    primary_col: str,
    extra_cols: list[str] | None = None,
) -> pd.Series:
    primary_values = df[primary_col].fillna("").astype(str).str.strip()
    if not extra_cols:
        return primary_values

    combined_values = primary_values.copy()
    for col_name in extra_cols:
        col_values = df[col_name].fillna("").astype(str).str.strip()
        combined_values = combined_values.where(col_values.eq(""), combined_values + " " + col_values)
    return combined_values.str.replace(r"\s+", " ", regex=True).str.strip()


def _normalize_header_token(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _drop_header_like_rows(
    df: pd.DataFrame,
    selected_cols: list[str],
    *,
    scan_rows: int = 3,
) -> tuple[pd.DataFrame, int]:
    """Drop leading rows that look like duplicated headers in selected columns."""
    if df.empty:
        return df, 0

    cols = [col for col in selected_cols if col in df.columns]
    if not cols:
        return df, 0

    primary_col = cols[0]
    to_drop: list[object] = []
    max_scan = min(len(df), max(1, int(scan_rows)))

    for pos in range(max_scan):
        idx = df.index[pos]
        row = df.loc[idx]

        primary_value = _normalize_header_token(str(row.get(primary_col, "")))
        if not primary_value or primary_value != _normalize_header_token(primary_col):
            continue

        compared = 0
        matched = 0
        for col in cols:
            raw_value = str(row.get(col, "")).strip()
            if not raw_value:
                continue
            compared += 1
            if _normalize_header_token(raw_value) == _normalize_header_token(col):
                matched += 1

        if compared == 1 and matched == 1:
            to_drop.append(idx)
        elif compared >= 2 and matched >= 2:
            to_drop.append(idx)

    if not to_drop:
        return df, 0

    cleaned = df.drop(index=to_drop).reset_index(drop=True)
    return cleaned, len(to_drop)


def _fast_series_signature(values: pd.Series, sample_size: int = 256) -> str:
    total = len(values)
    if total == 0:
        return "0:0"

    if total > sample_size:
        head_size = sample_size // 2
        tail_size = sample_size - head_size
        sample = pd.concat(
            [values.head(head_size), values.tail(tail_size)],
            ignore_index=True,
        )
    else:
        sample = values

    sample_hash = int(pd.util.hash_pandas_object(sample, index=False).sum())
    return f"{total}:{sample_hash}"


def _feedback_cache_token(db_path: str = FEEDBACK_DB_PATH) -> str:
    """Return a stable token that changes whenever feedback DB content changes."""
    try:
        stat_result = os.stat(db_path)
        return f"{int(stat_result.st_mtime_ns)}:{int(stat_result.st_size)}"
    except OSError:
        return "0:0"


@st.cache_data(show_spinner=False)
def run_matching(
    left_values: tuple[str, ...],
    right_values: tuple[str, ...],
    method_value: str,
    fuzzy_threshold: int,
    levenshtein_max_distance: int,
    levenshtein_engine: str,
    feedback_token: str = "",
) -> pd.DataFrame:
    from Source.name_matchingaviation import load_match_feedback, match_names

    feedback = load_match_feedback(FEEDBACK_DB_PATH)

    return match_names(
        list(left_values),
        list(right_values),
        method=method_value,
        fuzzy_threshold=fuzzy_threshold,
        lev_max_distance=levenshtein_max_distance,
        lev_engine=levenshtein_engine,
        feedback=feedback,
    )


@st.cache_data(show_spinner=False)
def run_matching_staged(
    left_values: tuple[str, ...],
    left_locs: tuple[str, ...],
    right_values: tuple[str, ...],
    right_locs: tuple[str, ...],
    method_value: str,
    fuzzy_threshold: int,
    levenshtein_max_distance: int,
    levenshtein_engine: str,
    feedback_token: str = "",
    location_threshold: int = 85,
) -> pd.DataFrame:
    """Two-stage matching: filter reference rows by location first, then match on name within those candidates."""
    from collections import defaultdict
    from Source.name_matchingaviation import (
        load_match_feedback,
        match_names,
        normalize_name,
        fuzzy_score,
    )
    try:
        from rapidfuzz import fuzz as rf_fuzz
        from rapidfuzz import process as rf_process
    except Exception:
        rf_fuzz = None
        rf_process = None

    left_list = list(left_values)
    left_locs_list = list(left_locs)
    right_list = list(right_values)
    right_locs_list = list(right_locs)
    feedback = load_match_feedback(FEEDBACK_DB_PATH)

    right_locs_norm = [normalize_name(loc) for loc in right_locs_list]
    left_locs_norm = [normalize_name(loc) for loc in left_locs_list]
    all_right_indices = list(range(len(right_list)))

    tgt_loc_to_indices: dict[str, list[int]] = defaultdict(list)
    for idx, tgt_loc_n in enumerate(right_locs_norm):
        tgt_loc_to_indices[tgt_loc_n].append(idx)
    unique_tgt_locs = list(tgt_loc_to_indices.keys())

    # Group source indices by their normalized location
    loc_to_src_indices: dict[str, list[int]] = defaultdict(list)
    for i, loc_n in enumerate(left_locs_norm):
        loc_to_src_indices[loc_n].append(i)

    # For each unique source location, find reference rows whose location matches
    loc_to_tgt_indices: dict[str, list[int]] = {}
    for src_loc_n in loc_to_src_indices:
        if src_loc_n:
            matched: list[int] = []
            if rf_process is not None and rf_fuzz is not None:
                hits = rf_process.extract(
                    src_loc_n,
                    unique_tgt_locs,
                    scorer=rf_fuzz.ratio,
                    processor=None,
                    score_cutoff=location_threshold,
                    limit=None,
                )
                for _, _, hit_pos in hits:
                    matched.extend(tgt_loc_to_indices[unique_tgt_locs[int(hit_pos)]])
            else:
                matched = [
                    j for j, tgt_loc_n in enumerate(right_locs_norm)
                    if tgt_loc_n and fuzzy_score(src_loc_n, tgt_loc_n) >= location_threshold
                ]
            loc_to_tgt_indices[src_loc_n] = matched if matched else all_right_indices
        else:
            loc_to_tgt_indices[src_loc_n] = all_right_indices

    # Run name matching per location group then reassemble in original source order
    result_rows: list[dict] = [{}] * len(left_list)
    for src_loc_n, src_indices in loc_to_src_indices.items():
        tgt_indices = loc_to_tgt_indices[src_loc_n]
        group_src = [left_list[i] for i in src_indices]
        group_tgt = [right_list[j] for j in tgt_indices]
        sub_df = match_names(
            group_src,
            group_tgt,
            method=method_value,
            fuzzy_threshold=fuzzy_threshold,
            lev_max_distance=levenshtein_max_distance,
            lev_engine=levenshtein_engine,
            feedback=feedback,
        )
        for row_pos, src_idx in enumerate(src_indices):
            result_rows[src_idx] = sub_df.iloc[row_pos].to_dict()

    return pd.DataFrame(result_rows)


# Sidebar menu is rendered by name_matchingUI.py before delegating to aviation.
if "sidebar_menu" not in st.session_state:
    st.session_state["sidebar_menu"] = "AirlineMatching"
sidebar_menu = st.session_state.get("sidebar_menu", "AirlineMatching")

if sidebar_menu == "SLM":
    runpy.run_path(os.path.join(BASE_DIR, "slm_ui.py"), run_name="__main__")
    st.stop()

if sidebar_menu == "Bulk Name Matching":
    with st.sidebar:
        st.divider()
        st.header("Matching Settings")
        st.caption("Configure matching and provide data.")

        slm_health = _slm_health_status()
        slm_available, slm_unavailable_reason = _slm_matching_available()

        with st.expander("Matching settings", expanded=True):
            _bulk_method_opts = [
                "ENCCLT Match",
                "FNCCLT Match",
                "SNCCLT Match",
                "JNCCLT Match",
                "LNCCLT Match",
                "AINCCLT Match",
            ]
            if slm_available:
                _bulk_method_opts.append("SLM Match")

            _bulk_method_sel = st.selectbox(
                "Method",
                _bulk_method_opts,
                index=1,
                key="bulk_method",
            )
            if not slm_available and slm_unavailable_reason:
                st.caption(slm_unavailable_reason)

            if _bulk_method_sel in {"FNCCLT Match", "JNCCLT Match", "AINCCLT Match", "SLM Match", "Vector Similarity (SLM)", "SLM Adaptive Match"}:
                st.slider("Fuzzy threshold", 0, 100, 75, 1, key="bulk_threshold")
            if _bulk_method_sel == "LNCCLT Match":
                st.slider("Levenshtein max distance", 0, 10, 2, 1, key="bulk_lev_distance")
                st.selectbox(
                    "Levenshtein engine",
                    ["Auto", "RapidFuzz", "Python"],
                    key="bulk_lev_engine",
                    help="Auto uses RapidFuzz when available, otherwise Python fallback.",
                )

        with st.expander("Advanced", expanded=False):
            st.caption(f"Loaded: `{_clean_display_path(__file__)}`")
            st.caption(f"mtime: `{_file_mtime_iso(__file__)}`")

    runpy.run_path(os.path.join(BASE_DIR, "bulknamematchingUI.py"), run_name="__main__")
    st.stop()

with st.sidebar:
    st.divider()

    st.header("Matching Settings")
    st.caption("Configure matching and provide data.")

    use_demo_files = st.toggle("Use built-in demo files", value=True)
    slm_health = _slm_health_status()
    slm_available, slm_unavailable_reason = _slm_matching_available()

    with st.expander("Matching settings", expanded=True):
        method_options = [
            "ENCCLT Match",
            "FNCCLT Match",
            "SNCCLT Match",
            "JNCCLT Match",
            "LNCCLT Match",
            "AINCCLT Match",
        ]
        if slm_available:
            method_options.append("SLM Match")

        method = st.selectbox(
            "Method",
            method_options,
        )
        if not slm_available and slm_unavailable_reason:
            st.caption(slm_unavailable_reason)

        threshold = 75
        lev_max_distance = 2
        lev_engine = "auto"
        if method in {"FNCCLT Match", "JNCCLT Match", "AINCCLT Match", "SLM Match", "Vector Similarity (SLM)", "SLM Adaptive Match"}:
            threshold = st.slider("Fuzzy threshold", 0, 100, 75, 1)
        if method == "LNCCLT Match":
            lev_max_distance = st.slider("Levenshtein max distance", 0, 10, 2, 1)
            lev_engine = st.selectbox(
                "Levenshtein engine",
                ["Auto", "RapidFuzz", "Python"],
                help="Auto uses RapidFuzz when available, otherwise Python fallback.",
            ).lower()

        top_n = st.slider("Top matches to show", 1, 25, 10, 1)

    with st.expander("Advanced", expanded=False):
        show_previews = st.checkbox(
            "Show data previews",
            value=True,
            disabled=not _is_control_enabled("show_data_previews_checkbox"),
        )
        show_only_matches = st.checkbox(
            "Show only matched rows",
            value=False,
            disabled=not _is_control_enabled("show_only_matches_checkbox"),
        )
        show_unmatched_rows = st.checkbox(
            "Show unmatched rows",
            value=False,
        )
        max_rows_to_render = st.slider("Rows to render in UI tables", 100, 5000, 1000, 100)

    with st.expander("Debug", expanded=False):
        st.caption(f"Loaded: `{_clean_display_path(__file__)}`")
        st.caption(f"mtime: `{_file_mtime_iso(__file__)}`")

method_key = {
    "ENCCLT Match": "exact",
    "FNCCLT Match": "fuzzy",
    "SNCCLT Match": "soundex",
    "JNCCLT Match": "jaro_winkler",
    "LNCCLT Match": "levenshtein",
    "AINCCLT Match": "ai_advanced",
    "SLM Match": "slm",
    "Vector Similarity (SLM)": "vector_similarity",
    "SLM Adaptive Match": "slm_adaptive",
}[method]

if "slm_bulk_warmed" not in st.session_state:
    st.session_state["slm_bulk_warmed"] = False

if method_key in {"slm", "vector_similarity", "slm_adaptive"} and not st.session_state["slm_bulk_warmed"]:
    with st.spinner("Preparing SLM model for faster matching..."):
        try:
            from Source import name_matchingaviation as nm

            warmup_fn = getattr(nm, "warmup_slm_runtime", None)
            if callable(warmup_fn):
                warmup_fn()
            else:
                # Compatibility path for deployments with older namematching module exports.
                runtime_loader = getattr(nm, "_load_slm_runtime", None)
                if not callable(runtime_loader):
                    raise AttributeError(
                        "warmup_slm_runtime is unavailable and _load_slm_runtime fallback is not present"
                    )
                runtime_loader()
            st.session_state["slm_bulk_warmed"] = True
        except Exception as exc:
            if isinstance(exc, ModuleNotFoundError):
                st.warning(
                    "SLM warm-up could not complete because required dependencies are missing "
                    f"({exc}). Install/update requirements and redeploy."
                )
            else:
                st.warning(f"SLM warm-up could not complete: {exc}")

if sidebar_menu == "Data Upload":
    st.subheader("Data Upload")
    source_upload_df = None
    mapping_df = pd.DataFrame(columns=["Source Column", "Destination Column"])
    preview_clicked = False
    uploaded_source_file = st.file_uploader(
        "Source file selector",
        type=["csv", "xlsx"],
        key="data_upload_source_file",
    )
    if uploaded_source_file is not None:
        source_upload_df = read_table(uploaded_source_file)
        if source_upload_df is None:
            st.warning("Could not read the selected file.")
        else:
            file_col, preview_col = st.columns([4, 1], gap="small")
            with file_col:
                st.success(f"Selected: `{uploaded_source_file.name}`")
            with preview_col:
                preview_clicked = st.button(
                    "Data Preview",
                    use_container_width=True,
                    disabled=not _is_control_enabled("data_preview_button"),
                )

            if preview_clicked:
                with st.expander("Uploaded Data Preview", expanded=True):
                    st.dataframe(source_upload_df.head(100), use_container_width=True, height=320)

            st.markdown("### Source and Destination Column Mapping")
            st.caption("Map each source column to a destination column using dropdowns.")

            source_columns = [str(col) for col in source_upload_df.columns.tolist()]
            header_col1, header_col2 = st.columns(2, gap="small")
            with header_col1:
                st.markdown("**Source Columns**")
            with header_col2:
                st.markdown("**Destination Columns**")

            mapped_rows: list[dict[str, str]] = []
            for idx, default_source in enumerate(source_columns):
                row_col1, row_col2 = st.columns(2, gap="small")
                with row_col1:
                    selected_source = st.selectbox(
                        f"Source Column {idx + 1}",
                        options=source_columns,
                        index=idx,
                        key=f"data_upload_source_col_{idx}",
                        label_visibility="collapsed",
                    )
                with row_col2:
                    default_dest_index = (
                        source_columns.index(default_source)
                        if default_source in source_columns
                        else 0
                    )
                    selected_destination = st.selectbox(
                        f"Destination Column {idx + 1}",
                        options=source_columns,
                        index=default_dest_index,
                        key=f"data_upload_dest_col_{idx}",
                        label_visibility="collapsed",
                    )
                mapped_rows.append(
                    {
                        "Source Column": selected_source,
                        "Destination Column": selected_destination,
                    }
                )

            mapping_df = pd.DataFrame(mapped_rows)
            st.session_state["data_upload_column_mapping"] = mapping_df
    else:
        st.info("Choose a CSV/XLSX file.")

    upload_button_clicked = st.button(
        "Data Upload",
        type="primary",
        use_container_width=True,
        disabled=(
            uploaded_source_file is None
            or source_upload_df is None
            or not _is_control_enabled("data_upload_button")
        ),
    )
    if upload_button_clicked and uploaded_source_file is not None and source_upload_df is not None:
        with st.spinner("Saving uploaded data to DB..."):
            upload_id, saved_row_count = _save_data_upload_to_db(
                source_upload_df,
                mapping_df,
                uploaded_source_file.name,
            )
        st.success(
            f"Data uploaded to DB successfully. Upload ID: `{upload_id}`. "
            f"Saved rows: {saved_row_count}. DB: `{DATA_UPLOAD_DB_PATH}`"
        )

    st.markdown("Switch to **Name Matching** from the left menu to run matching.")
    st.stop()

if sidebar_menu == "Tower Matching":
    st.subheader("Tower Matching")

    tower_template_path = os.path.join(BASE_DIR, "demo_data", "Tower_Matching_Template.xlsx")
    if os.path.exists(tower_template_path):
        with open(tower_template_path, "rb") as template_file:
            template_bytes = template_file.read()
        b64 = base64.b64encode(template_bytes).decode("ascii")
        href = (
            f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;'
            f'base64,{b64}" download="Tower_Matching_Template.xlsx"'
            ' style="text-decoration: underline;">'
            "Tower Matching Template</a>"
        )
        st.markdown(
            f"""
            <div style="display:flex; align-items:baseline; gap:0.5rem; flex-wrap:wrap;">
              <span>Upload a tower match file (CSV/XLSX). Use previews to sanity check the data.</span>
              {href}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption("Upload a tower match file (CSV/XLSX). Use previews to sanity check the data.")

    tower_source_file = st.file_uploader(
        "**Tower Source File**",
        type=["csv", "xlsx"],
        key="tower_source_file",
    )

    tower_source_df = read_table(tower_source_file)

    if tower_source_file is not None and tower_source_df is None:
        st.warning("Could not read the tower source file.")

    def _render_tower_mapping(label: str, df: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
        st.markdown(f"### {label} Column Mapping")
        st.caption("Map each source column to a destination column using dropdowns.")

        tower_columns = [str(col) for col in df.columns.tolist()]
        header_col1, header_col2 = st.columns(2, gap="small")
        with header_col1:
            st.markdown("**Source Columns**")
        with header_col2:
            st.markdown("**Destination Columns**")

        mapped_rows: list[dict[str, str]] = []
        for idx, default_source in enumerate(tower_columns):
            row_col1, row_col2 = st.columns(2, gap="small")
            with row_col1:
                selected_source = st.selectbox(
                    f"{label} Source Column {idx + 1}",
                    options=tower_columns,
                    index=idx,
                    key=f"{key_prefix}_source_col_{idx}",
                    label_visibility="collapsed",
                )
            with row_col2:
                default_dest_index = (
                    tower_columns.index(default_source)
                    if default_source in tower_columns
                    else 0
                )
                selected_destination = st.selectbox(
                    f"{label} Destination Column {idx + 1}",
                    options=tower_columns,
                    index=default_dest_index,
                    key=f"{key_prefix}_dest_col_{idx}",
                    label_visibility="collapsed",
                )
            mapped_rows.append(
                {
                    "Source Column": selected_source,
                    "Destination Column": selected_destination,
                }
            )

        mapping_df = pd.DataFrame(mapped_rows)
        st.session_state[f"{key_prefix}_column_mapping"] = mapping_df
        return mapping_df

    if tower_source_df is not None:
        st.markdown("**Tower Source Preview**")
        st.dataframe(tower_source_df.head(100), use_container_width=True, height=320)

    def _ensure_min_columns(df: pd.DataFrame, min_cols: int) -> pd.DataFrame:
        if df.shape[1] >= min_cols:
            return df
        extra_needed = min_cols - df.shape[1]
        extra_cols = []
        base_idx = 1
        while len(extra_cols) < extra_needed:
            name = f"_col_{df.shape[1] + base_idx}"
            if name not in df.columns:
                extra_cols.append(name)
            base_idx += 1
        for col_name in extra_cols:
            df[col_name] = ""
        return df

    def TM_Formula(source_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Port of the VBA TM_Formula logic using positional columns (A=0 ... O=14).
        Returns: (working_df, working_next_df, final_result_df)
        """
        df = _ensure_min_columns(source_df.copy(), 15)
        columns = list(df.columns)
        rows = df.to_numpy(copy=True).tolist()

        working_next_rows: list[list] = []
        final_rows: list[list] = []

        max_cycles = 1000
        max_rows = 30000

        # Column positions (0-based)
        col_c = 2
        col_d = 3
        col_e = 4
        col_f = 5
        col_h = 7
        col_j = 9
        col_k = 10
        col_l = 11
        col_m = 12
        col_n = 13
        col_o = 14

        for j in range(max_cycles + 1):
            ws_lr = len(rows)
            if ws_lr <= 1 or ws_lr == 1048576:
                break

            counts: dict[object, int] = {}
            i = 1  # 0-based index for Excel row 2
            while i < min(ws_lr, max_rows):
                row = rows[i]
                prev_row = rows[i - 1]

                current_c = row[col_c]
                k_val = counts.get(current_c, 0)
                row[col_k] = k_val
                counts[current_c] = k_val + 1

                row[col_l] = "primary" if row[col_f] == 0 else "non-primary"

                if row[col_k] == 0:
                    row[col_m] = 0
                else:
                    if (
                        row[col_f] == 0
                        and row[col_c] == prev_row[col_c]
                        and row[col_d] == prev_row[col_d]
                        and row[col_e] == prev_row[col_e]
                        and row[col_f] == prev_row[col_f]
                        and row[col_h] == prev_row[col_h]
                        and row[col_j] != prev_row[col_j]
                    ):
                        row[col_m] = 0
                    else:
                        row[col_m] = "next cycle"

                if row[col_k] == 0:
                    row[col_n] = 0
                else:
                    if row[col_f] >= (prev_row[col_e] + prev_row[col_f]):
                        row[col_n] = 0
                    else:
                        if row[col_e] == prev_row[col_e] and row[col_f] == prev_row[col_f]:
                            row[col_n] = 0
                        else:
                            row[col_n] = "next cycle"

                row[col_o] = row[col_m] if row[col_l] == "primary" else row[col_n]

                if row[col_k] == -1:
                    if i > 1:
                        for idx in range(1, i):
                            rows[idx][col_m:col_o + 1] = [j, j, j]
                        final_rows.extend(rows[1:i])
                    rows = rows[:1] + rows[i + 1 :]
                    if working_next_rows:
                        rows = working_next_rows + rows
                        working_next_rows = []
                    break

                if row[col_o] == "next cycle":
                    working_next_rows.append(row.copy())
                    rows.pop(i)
                    counts[current_c] = counts.get(current_c, 1) - 1
                    ws_lr = len(rows)
                    continue

                i += 1

        working_df = pd.DataFrame(rows, columns=columns)
        working_next_df = pd.DataFrame(working_next_rows, columns=columns)
        final_result_df = pd.DataFrame(final_rows, columns=columns)
        return working_df, working_next_df, final_result_df

    if tower_source_df is None:
        st.info("Upload the tower source file to get started.")
        st.stop()

    if st.button("Tower Match", type="primary", use_container_width=True):
        with st.spinner("Running Tower Match formula..."):
            working_df, working_next_df, final_result_df = TM_Formula(tower_source_df)

        st.success("Tower Match complete.")
        st.markdown("### Working Sheet (Processed)")
        st.dataframe(working_df.head(200), use_container_width=True, height=360)

        if not working_next_df.empty:
            st.markdown("### Working Sheet Next")
            st.dataframe(working_next_df.head(200), use_container_width=True, height=360)

        if not final_result_df.empty:
            st.markdown("### Final Result")
            st.dataframe(final_result_df.head(200), use_container_width=True, height=360)

    st.stop()

if sidebar_menu == "Admin":
    st.subheader("Admin")
    st.caption("Enable or disable app buttons and checkboxes, then save to XML.")

    button_controls = [c for c in CONTROL_REGISTRY if c["type"] == "button"]
    checkbox_controls = [c for c in CONTROL_REGISTRY if c["type"] == "checkbox"]
    updated_settings = dict(control_settings)

    st.markdown("### Buttons")
    for control in button_controls:
        updated_settings[control["id"]] = st.checkbox(
            control["label"],
            value=bool(control_settings.get(control["id"], True)),
            key=f"admin_control_{control['id']}",
        )

    st.markdown("### Checkboxes")
    for control in checkbox_controls:
        updated_settings[control["id"]] = st.checkbox(
            control["label"],
            value=bool(control_settings.get(control["id"], True)),
            key=f"admin_control_{control['id']}",
        )

    save_admin_controls = st.button("Save Admin Settings", type="primary", use_container_width=True)
    if save_admin_controls:
        _save_control_settings(updated_settings)
        st.success(f"Settings saved to `{CONTROL_SETTINGS_XML_PATH}`")
        st.rerun()

    st.stop()

st.markdown(
    """
    <div style="display:flex; align-items:center; gap:1rem; flex-wrap:wrap;">
      <h3 style="margin:0;">Provide data</h3>
      <div class="nm-muted" style="margin:0;">
        Upload two files (CSV/XLSX) or use the built-in demo files from the sidebar.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

up_col1, up_col2 = st.columns(2, gap="large")
with up_col1:
    st.markdown("<strong><b>Source File</b></strong>", unsafe_allow_html=True)
    left_file = st.file_uploader("", type=["csv", "xlsx"], key="source_file")
with up_col2:
    st.markdown("<strong>Reference File</strong>", unsafe_allow_html=True)
    right_file = st.file_uploader("", type=["csv", "xlsx"], key="reference_file")

if use_demo_files:
    left_df = (
        _read_demo_csv(DEMO_SOURCE_PATH, os.path.getmtime(DEMO_SOURCE_PATH))
        if os.path.exists(DEMO_SOURCE_PATH)
        else None
    )
    right_df = (
        _read_demo_csv(DEMO_TARGET_PATH, os.path.getmtime(DEMO_TARGET_PATH))
        if os.path.exists(DEMO_TARGET_PATH)
        else None
    )
    st.success(f"Using demo files: `{DEMO_SOURCE_PATH}` and `{DEMO_TARGET_PATH}`")
else:
    left_df = read_table(left_file)
    right_df = read_table(right_file)

if left_df is None or right_df is None:
    st.info("Upload both files to start matching, or enable demo files in the sidebar.")
    st.stop()

if show_previews:
    with st.container(border=True):
        st.markdown("**Data Previews**")
        prev_col1, prev_col2 = st.columns(2, gap="large")
        with prev_col1:
            with st.expander("Preview: Source", expanded=False):
                st.dataframe(left_df.head(25), use_container_width=True, height=280)
        with prev_col2:
            with st.expander("Preview: Target", expanded=False):
                st.dataframe(right_df.head(25), use_container_width=True, height=280)

choose_col_header, include_loc_col, include_ind_col = st.columns([3, 1.4, 1.4], gap="small")
with choose_col_header:
    st.subheader("Choose Columns")
with include_loc_col:
    include_location = st.checkbox(
        "Include Schedule",
        value=False,
        help="Append the schedule column to the primary name before matching when available.",
        disabled=not _is_control_enabled("include_location_checkbox"),
    )
with include_ind_col:
    include_industry = st.checkbox(
        "Include Airline Code",
        value=False,
        help="Append the airline code column to the primary name before matching when available.",
        disabled=not _is_control_enabled("include_industry_checkbox"),
    )

col_sel_left, col_sel_right = st.columns(2, gap="large")
with col_sel_left:
    left_default = left_df.columns.tolist().index("full_name") if "full_name" in left_df.columns else 0
    left_name_col = st.selectbox("Source name column", options=left_df.columns.tolist(), index=left_default)
with col_sel_right:
    right_default = right_df.columns.tolist().index("name_in_system") if "name_in_system" in right_df.columns else 0
    right_name_col = st.selectbox("Target name column", options=right_df.columns.tolist(), index=right_default)

left_location_col: str | None = None
right_location_col: str | None = None
left_industry_col: str | None = None
right_industry_col: str | None = None

if include_location:
    location_left, location_right = st.columns(2, gap="large")
    with location_left:
        left_location_options = [c for c in left_df.columns.tolist() if c != left_name_col]
        if left_location_options:
            left_location_default = (
                left_location_options.index("location") if "location" in left_location_options else 0
            )
            left_location_col = st.selectbox(
                "Source schedule column",
                options=left_location_options,
                index=left_location_default,
            )
        else:
            st.caption("No source columns available for schedule selection.")
    with location_right:
        right_location_options = [c for c in right_df.columns.tolist() if c != right_name_col]
        if right_location_options:
            right_location_default = (
                right_location_options.index("location") if "location" in right_location_options else 0
            )
            right_location_col = st.selectbox(
                "Target schedule column",
                options=right_location_options,
                index=right_location_default,
            )
        else:
            st.caption("No target columns available for schedule selection.")

if include_industry:
    industry_left, industry_right = st.columns(2, gap="large")
    with industry_left:
        left_industry_options = [c for c in left_df.columns.tolist() if c != left_name_col]
        if left_industry_options:
            left_industry_default = (
                left_industry_options.index("industry") if "industry" in left_industry_options else 0
            )
            left_industry_col = st.selectbox(
                "Source airline code column",
                options=left_industry_options,
                index=left_industry_default,
            )
        else:
            st.caption("No source columns available for airline code selection.")
    with industry_right:
        right_industry_options = [c for c in right_df.columns.tolist() if c != right_name_col]
        if right_industry_options:
            right_industry_default = (
                right_industry_options.index("industry") if "industry" in right_industry_options else 0
            )
            right_industry_col = st.selectbox(
                "Target airline code column",
                options=right_industry_options,
                index=right_industry_default,
            )
        else:
            st.caption("No target columns available for airline code selection.")

left_extra_cols: list[str] = []
right_extra_cols: list[str] = []
# Location is handled separately via staged matching; only append industry here.
if include_industry and left_industry_col and left_industry_col != left_name_col:
    left_extra_cols.append(left_industry_col)
if include_industry and right_industry_col and right_industry_col != right_name_col:
    right_extra_cols.append(right_industry_col)

left_selected_cols = [left_name_col]
right_selected_cols = [right_name_col]
if include_location and left_location_col:
    left_selected_cols.append(left_location_col)
if include_location and right_location_col:
    right_selected_cols.append(right_location_col)
left_selected_cols.extend(left_extra_cols)
right_selected_cols.extend(right_extra_cols)

left_df, left_header_rows_dropped = _drop_header_like_rows(left_df, left_selected_cols)
right_df, right_header_rows_dropped = _drop_header_like_rows(right_df, right_selected_cols)
if left_header_rows_dropped or right_header_rows_dropped:
    st.caption(
        "Ignored header-like rows in uploaded data "
        f"(source: {left_header_rows_dropped}, target: {right_header_rows_dropped})."
    )

left_names = _compose_match_values(left_df, left_name_col, left_extra_cols)
right_names = _compose_match_values(right_df, right_name_col, right_extra_cols)

if "slm_prime_signature" not in st.session_state:
    st.session_state["slm_prime_signature"] = ""

run_header_col, run_button_col = st.columns(2, gap="small")
with run_header_col:
    back_to_landing = st.button(
        "Back to Landing",
        type="primary",
        use_container_width=True,
        key="name_matching_back_to_landing",
    )
with run_button_col:
    run_now = st.button(
        "Run Airline Matching",
        type="primary",
        use_container_width=True,
        disabled=not _is_control_enabled("run_name_matching_button"),
    )

if back_to_landing:
    st.query_params["page"] = "landing"
    st.rerun()

has_results = "result_df" in st.session_state
if run_now:
    if method_key in {"slm", "vector_similarity", "slm_adaptive"}:
        left_sig = _fast_series_signature(left_names)
        right_sig = _fast_series_signature(right_names)
        slm_prime_signature = f"{left_sig}:{right_sig}"
        if st.session_state["slm_prime_signature"] != slm_prime_signature:
            with st.spinner("Priming SLM cache for this dataset..."):
                try:
                    from Source import name_matchingaviation as nm

                    prime_fn = getattr(nm, "prime_slm_match_runtime", None)
                    if callable(prime_fn):
                        prime_target_cap = min(len(right_names), 8000)
                        prime_source_cap = min(len(left_names), 128)
                        prime_fn(
                            target_names=right_names.tolist(),
                            source_names=left_names.tolist(),
                            max_target_to_embed=prime_target_cap,
                            max_source_to_embed=prime_source_cap,
                        )
                    else:
                        warmup_fn = getattr(nm, "warmup_slm_runtime", None)
                        if callable(warmup_fn):
                            warmup_fn()
                    st.session_state["slm_prime_signature"] = slm_prime_signature
                except Exception as exc:
                    st.caption(f"SLM pre-prime skipped: {exc}")

    with st.spinner("Matching names..."):
        feedback_token = _feedback_cache_token(FEEDBACK_DB_PATH)
        _use_staged = (
            include_location
            and left_location_col is not None
            and right_location_col is not None
        )
        if _use_staged:
            _left_locs = left_df[left_location_col].fillna("").astype(str)
            _right_locs = right_df[right_location_col].fillna("").astype(str)
            st.session_state["result_df"] = run_matching_staged(
                tuple(left_names.tolist()),
                tuple(_left_locs.tolist()),
                tuple(right_names.tolist()),
                tuple(_right_locs.tolist()),
                method_key,
                int(threshold),
                int(lev_max_distance),
                lev_engine,
                feedback_token,
            )
        else:
            st.session_state["result_df"] = run_matching(
                tuple(left_names.tolist()),
                tuple(right_names.tolist()),
                method_key,
                int(threshold),
                int(lev_max_distance),
                lev_engine,
                feedback_token,
            )
    st.session_state["scroll_to_top_matches"] = True
    has_results = True

if not has_results:
    st.info("Click **Run name matching** to generate results.")
    st.stop()

full_result_df = st.session_state.get("result_df")
if full_result_df is None:
    st.info("No results available yet. Run matching again.")
    st.stop()

# Apply self-learning feedback overrides
try:
    from Source.name_matchingaviation import load_match_feedback, apply_match_feedback
    _fb = load_match_feedback(FEEDBACK_DB_PATH)
    if _fb["approved"] or _fb["rejected"]:
        full_result_df = apply_match_feedback(full_result_df, _fb)
        st.session_state["result_df"] = full_result_df
except Exception:
    pass

result_df = full_result_df
if show_only_matches and "is_match" in full_result_df.columns:
    result_df = full_result_df[full_result_df["is_match"]].copy()
elif show_unmatched_rows and "is_match" in full_result_df.columns:
    result_df = full_result_df[~full_result_df["is_match"]].copy()

result_df_view = result_df.head(int(max_rows_to_render))
if len(result_df) > len(result_df_view):
    st.caption(f"Showing first {len(result_df_view):,} of {len(result_df):,} rows for faster rendering.")


def _style_matched_rows(df: pd.DataFrame):
    match_col = "is_match" if "is_match" in df.columns else ("Is Match" if "Is Match" in df.columns else None)
    if match_col is None:
        return df

    def _highlight_row(row: pd.Series) -> list[str]:
        if bool(row.get(match_col, False)):
            return ["background-color: #e8f5e9"] * len(row)
        return [""] * len(row)

    return df.style.apply(_highlight_row, axis=1)


def _to_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=lambda col: str(col).replace("_", " ").title())


def _prepare_result_for_display(
    df: pd.DataFrame,
    *,
    include_location: bool = False,
    left_df: "pd.DataFrame | None" = None,
    right_df: "pd.DataFrame | None" = None,
    left_location_col: "str | None" = None,
    right_name_col: "str | None" = None,
    right_location_col: "str | None" = None,
) -> pd.DataFrame:
    """Reorder columns and optionally enrich with location data for display."""
    display = df.copy()
    if include_location:
        if left_location_col and left_df is not None and left_location_col in left_df.columns:
            display["source_location"] = left_df[left_location_col].reindex(display.index).values
        if (
            right_location_col
            and right_df is not None
            and right_name_col is not None
            and right_name_col in right_df.columns
            and right_location_col in right_df.columns
        ):
            right_loc_map = (
                right_df.drop_duplicates(subset=[right_name_col])
                .set_index(right_name_col)[right_location_col]
                .to_dict()
            )
            display["matched_location"] = display["matched_name"].map(right_loc_map).fillna("")
    priority = ["source_name", "matched_name"]
    if include_location:
        if "source_location" in display.columns:
            priority.append("source_location")
        if "matched_location" in display.columns:
            priority.append("matched_location")
    existing_priority = [c for c in priority if c in display.columns]
    remaining = [c for c in display.columns if c not in priority]
    return display[existing_priority + remaining]


@st.cache_data(show_spinner=False)
def _top_relink_candidates(source_value: str, target_values: tuple[str, ...], top_k: int = 10) -> list[str]:
    from Source.name_matchingaviation import fuzzy_score, normalize_name, token_set_score

    source_text = str(source_value or "")
    source_norm = normalize_name(source_text)

    unique_targets: list[str] = []
    seen: set[str] = set()
    for value in target_values:
        target = str(value or "").strip()
        if not target or target in seen:
            continue
        seen.add(target)
        unique_targets.append(target)

    if not unique_targets:
        return []

    if not source_norm:
        return unique_targets[:top_k]

    scored: list[tuple[tuple[int, int, int], str]] = []
    source_tokens = set(source_norm.split())
    
    for target in unique_targets:
        target_norm = normalize_name(target)
        target_tokens = set(target_norm.split())
        
        # Hybrid scoring: prefix match + token overlap + character similarity
        prefix_bonus = 50 if source_norm.startswith(target_norm) else 0  # Exact prefix match
        token_match = 40 if target_tokens.issubset(source_tokens) else 0  # All target tokens in source
        fuzzy = fuzzy_score(source_norm, target_norm)
        
        # Use prefix_bonus as primary sort key, then token_match, then fuzzy
        composite_score = (prefix_bonus + token_match + fuzzy // 2, token_match, fuzzy)
        scored.append((composite_score, target))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [name for _, name in scored[:top_k]]


def _relink_score(source_value: str, target_value: str) -> int:
    from Source.name_matchingaviation import fuzzy_score, normalize_name

    if not str(target_value or "").strip():
        return 0
    return int(fuzzy_score(normalize_name(str(source_value or "")), normalize_name(str(target_value or ""))))


result_display_df = _to_display_columns(
    _prepare_result_for_display(
        result_df_view,
        include_location=include_location,
        left_df=left_df,
        right_df=right_df,
        left_location_col=left_location_col,
        right_name_col=right_name_col,
        right_location_col=right_location_col,
    )
)

st.dataframe(
    _style_matched_rows(result_display_df),
    use_container_width=True,
    height=420,
    key="results_table",
)

metric_col1, metric_col2, metric_col3 = st.columns(3)
with metric_col1:
    st.metric("Source rows", len(full_result_df))
with metric_col2:
    matched_count = int(full_result_df["is_match"].sum()) if "is_match" in full_result_df.columns else 0
    st.metric("Matched rows", matched_count)
with metric_col3:
    if "is_match" in full_result_df.columns and len(full_result_df) > 0:
        match_rate = 100 * float(full_result_df["is_match"].mean())
    else:
        match_rate = 0.0
    st.metric("Match rate", f"{match_rate:.1f}%")

st.markdown('<div id="top-matches-section"></div>', unsafe_allow_html=True)
st.subheader("Top potential matches")
if "score" in result_df.columns:
    top_df = result_df.sort_values("score", ascending=False).head(int(top_n))
else:
    top_df = result_df.head(int(top_n))
st.dataframe(
    _style_matched_rows(_to_display_columns(_prepare_result_for_display(
        top_df,
        include_location=include_location,
        left_df=left_df,
        right_df=right_df,
        left_location_col=left_location_col,
        right_name_col=right_name_col,
        right_location_col=right_location_col,
    ))),
    use_container_width=True,
    height=320,
)

if st.session_state.pop("scroll_to_top_matches", False):
    html(
        """
        <script>
          const scrollToMatches = () => {
            const el = window.parent.document.getElementById("top-matches-section");
            if (el && el.scrollIntoView) {
              el.scrollIntoView({behavior: "smooth", block: "start"});
            }
          };
          setTimeout(scrollToMatches, 120);
        </script>
        """,
        height=0,
    )

st.link_button(
    "Download Match Results",
    "https://www.linkedin.com/in/surabhi-singh-368042167/",
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Row-level enrichment dialog helpers
# ---------------------------------------------------------------------------

def _detect_country_col(columns: tuple[str, ...]) -> str | None:
    """Return the best country/location column found in columns, or None."""
    priority = [
        "country", "nation", "location", "city", "region",
        "state", "territory", "geography", "locale",
    ]
    cols_lower = {str(c).lower(): c for c in columns}
    for kw in priority:
        if kw in cols_lower:
            return cols_lower[kw]
    return None


@st.cache_data(show_spinner=False)
def _top_country_candidates(
    source_value: str, target_values: tuple[str, ...], top_k: int = 10
) -> list[str]:
    """Top-k unique location/country values from reference scored against source_value."""
    from Source.name_matchingaviation import fuzzy_score, normalize_name

    unique_vals: list[str] = list(
        dict.fromkeys(str(v).strip() for v in target_values if str(v).strip())
    )
    if not unique_vals:
        return []
    if not str(source_value or "").strip():
        return unique_vals[:top_k]
    src_n = normalize_name(str(source_value))
    scored = [(fuzzy_score(src_n, normalize_name(v)), v) for v in unique_vals]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [v for _, v in scored[:top_k]]


@st.dialog("Enrich Unmatched Record", width="small")
def _row_enrich_dialog(
    source_name: str,
    source_country_value: str,
    name_candidates: list[str],
    country_candidates: list[str],
    country_col_label: str,
    right_df_cols: list[str],
    use_demo_files: bool,
    right_name_col: str,
    country_col: str | None,
    row_original_index: int,
) -> None:
    """Modal dialog: RLHF trains the SLM; Enrichment adds to the reference file."""
    st.markdown(f"**Unmatched source:** `{source_name}`")
    st.caption(
        "**RLHF** � confirms this pair as a match, updates the SLM feedback store and refreshes results.  \n"
        "**Enrichment** � appends the chosen name + location as a new row in the reference data."
    )

    name_col_ui, country_col_ui = st.columns(2)
    with name_col_ui:
        chosen_name = st.selectbox(
            "Top 10 name candidates",
            options=name_candidates if name_candidates else [""],
            key="erd_name",
        )
    with country_col_ui:
        chosen_country = st.selectbox(
            "Top 10 schedule candidates",
            options=[""] + [c for c in country_candidates if c][:10],
            key="erd_country",
        )

    st.markdown("---")
    act_c1, act_c2 = st.columns(2)
    with act_c1:
        if st.button("RLHF", type="primary", use_container_width=True, key="erd_rlhf"):
            if chosen_name:
                try:
                    from Source.name_matchingaviation import save_match_feedback as _smf
                    _smf(
                        [{"source_name": source_name, "matched_name": chosen_name, "is_correct": True}],
                        FEEDBACK_DB_PATH,
                    )
                    _upd_df = st.session_state.get("result_df")
                    if isinstance(_upd_df, pd.DataFrame) and row_original_index in _upd_df.index:
                        _upd_df = _upd_df.copy()
                        _upd_df.at[row_original_index, "matched_name"] = chosen_name
                        _upd_df.at[row_original_index, "score"] = _relink_score(source_name, chosen_name)
                        _upd_df.at[row_original_index, "is_match"] = True
                        if "feedback_override" in _upd_df.columns:
                            _upd_df.at[row_original_index, "feedback_override"] = "rlhf_confirmed"
                        st.session_state["result_df"] = _upd_df
                    st.success(f"RLHF saved: '{source_name}' ? '{chosen_name}'. Refreshing�")
                    st.rerun()
                except Exception as _exc_rlhf:
                    st.error(f"RLHF error: {_exc_rlhf}")
            else:
                st.warning("Select a name candidate first.")
    with act_c2:
        if st.button("Enrichment", type="secondary", use_container_width=True, key="erd_enrichment"):
            _effective_name = str(chosen_name or "").strip() or str(source_name or "").strip()
            _effective_country = str(chosen_country or "").strip() or str(source_country_value or "").strip()
            if not _effective_name:
                st.warning("Could not enrich because source name is blank.")
            else:
                _new_ref_row: dict[str, object] = {col: "" for col in right_df_cols}
                _new_ref_row[right_name_col] = _effective_name
                if country_col and country_col in _new_ref_row:
                    _new_ref_row[country_col] = _effective_country
                _enr_list = list(st.session_state.get("_enrichment_rows", []))
                _enr_list.append(_new_ref_row)
                st.session_state["_enrichment_rows"] = _enr_list
                if use_demo_files:
                    try:
                        _demo_ref = pd.read_csv(DEMO_TARGET_PATH)
                        _demo_ref = pd.concat(
                            [_demo_ref, pd.DataFrame([_new_ref_row])], ignore_index=True
                        )
                        _demo_ref.to_csv(DEMO_TARGET_PATH, index=False)
                        st.success(f"Reference file updated with '{_effective_name}'.")
                    except Exception as _exc_enr:
                        st.error(f"Could not write reference file: {_exc_enr}")
                else:
                    st.success(f"'{_effective_name}' queued � download the enriched rows below the feedback panel.")
                st.rerun()


# ---------------------------------------------------------------------------
# Self-learning feedback section
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("Confirm Matches � Self-Learning Feedback", expanded=False):
    st.caption(
        "Mark each result as correct or incorrect. "
        "Saved decisions are applied automatically on every future run."
    )
    _left_country_col = left_location_col
    if not _left_country_col and left_df is not None:
        _left_country_col = _detect_country_col(tuple(left_df.columns.tolist()))

    _right_country_col = right_location_col
    if not _right_country_col and right_df is not None:
        _right_country_col = _detect_country_col(tuple(right_df.columns.tolist()))

    _feedback_columns = [
        "source_name",
        "source_location",
        "source_country",
        "matched_name",
        "matched_location",
        "matched_country",
        "score",
        "is_match",
    ]
    _fb_view = result_df_view[[c for c in _feedback_columns if c in result_df_view.columns]].copy()

    if "source_location" not in _fb_view.columns and _left_country_col and _left_country_col in left_df.columns:
        _fb_view["source_location"] = left_df[_left_country_col].reindex(_fb_view.index).fillna("").astype(str)

    if "matched_location" not in _fb_view.columns and _right_country_col and _right_country_col in right_df.columns:
        _right_country_map = (
            right_df.drop_duplicates(subset=[right_name_col])
            .set_index(right_name_col)[_right_country_col]
            .to_dict()
        )
        _fb_view["matched_location"] = _fb_view["matched_name"].map(_right_country_map).fillna("")

    _fb_view["is_correct"] = _fb_view.get("is_match", False)

    # -- Row-click enrichment dialog (active only when "Show unmatched rows" is on) --
    if show_unmatched_rows:
        st.markdown(
            "**Click any row** to open the RLHF / Enrichment dialog for that record.",
            help="RLHF trains the SLM; Enrichment appends the record to the reference data.",
        )
        _fb_sel_event = st.dataframe(
            _fb_view[[c for c in _feedback_columns if c in _fb_view.columns]],
            use_container_width=True,
            height=300,
            key="feedback_unmatched_selector",
            on_select="rerun",
            selection_mode="single-row",
        )
        _sel_rows = getattr(getattr(_fb_sel_event, "selection", None), "rows", [])
        if _sel_rows:
            _sel_pos = int(_sel_rows[0])
            _fb_sel_row = _fb_view.iloc[_sel_pos]
            _sel_source_name = str(_fb_sel_row.get("source_name", ""))
            _sel_orig_idx = int(_fb_view.index[_sel_pos])
            _sel_source_country = str(
                _fb_sel_row.get("source_location", "")
                or _fb_sel_row.get("source_country", "")
                or ""
            ).strip()
            if (
                not _sel_source_country
                and _left_country_col is not None
                and _left_country_col in left_df.columns
                and _sel_orig_idx in left_df.index
            ):
                _sel_source_country = str(left_df.at[_sel_orig_idx, _left_country_col] or "").strip()
            _name_cands = _top_relink_candidates(
                _sel_source_name, tuple(right_names.tolist()), top_k=10
            )
            _country_col = right_location_col if right_location_col in right_df.columns else _detect_country_col(tuple(right_df.columns.tolist()))
            if _country_col:
                _country_vals = tuple(
                    right_df[_country_col].dropna().astype(str).unique().tolist()
                )
                _country_query = _sel_source_country or _sel_source_name
                _country_cands = _top_country_candidates(_country_query, _country_vals, top_k=10)
            else:
                _country_cands = []
            _row_enrich_dialog(
                source_name=_sel_source_name,
                source_country_value=_sel_source_country,
                name_candidates=_name_cands,
                country_candidates=_country_cands,
                country_col_label=_country_col or "Country",
                right_df_cols=right_df.columns.tolist(),
                use_demo_files=use_demo_files,
                right_name_col=right_name_col,
                country_col=_country_col,
                row_original_index=_sel_orig_idx,
            )
        st.divider()

# -- Enrichment download for uploaded (non-demo) reference files ---------------
_pending_enr = st.session_state.get("_enrichment_rows", [])
if _pending_enr and not use_demo_files:
    _enr_df = pd.DataFrame(_pending_enr)
    st.download_button(
        "? Download Enriched Reference Rows",
        data=_enr_df.to_csv(index=False).encode("utf-8"),
        file_name="enriched_reference_rows.csv",
        mime="text/csv",
        use_container_width=True,
        key="download_enriched_reference",
    )

st.markdown('<div class="nm-chat-shell">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="nm-chat-head">
      <h3>Chat Assistant</h3>
      <span class="nm-chat-badge">AI Guidance</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="nm-muted">Ask about matching methods, thresholds, or troubleshooting. All analysis uses your local SLM model.</div>',
    unsafe_allow_html=True,
)

settings_col, clear_col = st.columns([4, 1], gap="small")
with settings_col:
    with st.expander("Assistant settings", expanded=False):
        include_app_context = st.checkbox(
            "Include current app context",
            value=True,
            disabled=not _is_control_enabled("include_app_context_checkbox"),
        )
with clear_col:
    clear_chat = st.button(
        "Clear chat",
        use_container_width=True,
        disabled=not _is_control_enabled("clear_chat_button"),
    )

if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = [
        {
            "role": "assistant",
            "content": "Hi! Ask me which matching method to use, how to pick thresholds, or why a row did not match.",
        }
    ]

if clear_chat:
    st.session_state["chat_messages"] = [
        {"role": "assistant", "content": "Chat cleared. Ask a new question when you're ready."}
    ]
    st.rerun()

st.markdown('<div class="nm-chat-quick">Quick prompts</div>', unsafe_allow_html=True)
prompt_col1, prompt_col2, prompt_col3 = st.columns(3, gap="small")
if prompt_col1.button(
    "Best method?",
    use_container_width=True,
    disabled=not _is_control_enabled("best_method_button"),
):
    st.session_state["quick_prompt"] = "Which method is best for messy customer names?"
if prompt_col2.button(
    "Tune threshold",
    use_container_width=True,
    disabled=not _is_control_enabled("tune_threshold_button"),
):
    st.session_state["quick_prompt"] = "How should I tune the threshold to reduce false positives?"
if prompt_col3.button(
    "Explain mismatch",
    use_container_width=True,
    disabled=not _is_control_enabled("explain_mismatch_button"),
):
    st.session_state["quick_prompt"] = "Why might two similar names fail to match?"

for msg in st.session_state["chat_messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_prompt = st.chat_input("Ask the assistant...")
if not user_prompt and "quick_prompt" in st.session_state:
    user_prompt = st.session_state.pop("quick_prompt")

if user_prompt:
    st.session_state["chat_messages"].append({"role": "user", "content": user_prompt})

    context_lines: list[str] = []
    if include_app_context:
        context_lines = [
            f"Selected method: {method}",
            f"Method key: {method_key}",
            f"Fuzzy threshold: {int(threshold)}",
            f"Levenshtein max distance: {int(lev_max_distance)}",
            f"Levenshtein engine: {lev_engine}",
            f"Top matches: {int(top_n)}",
            f"Optional source columns: {', '.join(left_extra_cols) if left_extra_cols else 'None'}",
            f"Optional target columns: {', '.join(right_extra_cols) if right_extra_cols else 'None'}",
            f"Show only matches: {bool(show_only_matches)}",
            f"Rows in result: {len(result_df)}",
        ]

    app_context_str = "\n".join(context_lines) if context_lines else ""

    with st.chat_message("assistant"):
        # Generate SLM-based explanation locally (no external API calls)
        try:
            answer = _generate_slm_explanation(user_prompt, app_context_str)
        except Exception as error:
            answer = f"An error occurred while generating the explanation: {type(error).__name__}"

        st.markdown(answer)
        st.session_state["chat_messages"].append({"role": "assistant", "content": answer})

st.markdown("</div>", unsafe_allow_html=True)
st.markdown(
    '<div class="nm-footer">&copy; 2026 braincal.com. All rights reserved</div>',
    unsafe_allow_html=True,
)


