import os
import streamlit as st

FAVICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "favicon.png")

def _safe_set_page_config(**kwargs):
    try:
        st.set_page_config(**kwargs)
    except Exception:
        pass

_safe_set_page_config(
    page_title="Why Match | ReMatch",
    page_icon=FAVICON_PATH,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CLEAN CSS ---
st.markdown("""
<style>

html, body, .stApp {
    margin: 0;
    padding: 0;
    font-family: "Plus Jakarta Sans", sans-serif;
}

/* Hide Streamlit chrome */
div[data-testid="stHeader"],
div[data-testid="stToolbar"],
#MainMenu,
footer {
    display: none !important;
}

/* Remove Streamlit padding */
.block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}

/* Background (NO radial circle anymore) */
.stApp {
    background: #f3f4f6;
}

/* --- PAGE LAYOUT --- */
.wm-shell {
    width: min(76rem, 92%);
    margin: 0 auto;
    padding: 3rem 0 3rem;
    text-align: center;
    position: relative;
}

/* --- TYPOGRAPHY --- */
.wm-title {
    font-size: clamp(2.4rem, 4.5vw, 4rem);
    font-weight: 800;
    margin: 0;
    color: #12131a;
}

.wm-title-em {
    color: #0f62ff;
}

.wm-subtitle {
    margin: 1rem auto 0;
    max-width: 52rem;
    font-size: clamp(1.1rem, 1.5vw, 1.55rem);
    color: #343741;
    font-weight: 500;
    line-height: 1.32;
    text-align: center;
    width: 100%;
}

/* --- GRID --- */
.wm-grid {
    margin-top: 2rem;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.4rem;
    justify-items: center;
}

/* Equal-height cards */
.wm-card {
    background: white;
    border: 1px solid rgba(18, 19, 26, 0.08);
    border-radius: 0.9rem;
    padding: 1.6rem 1.8rem;
    width: 100%;
    max-width: 34rem;
    text-align: left;

    min-height: 14rem;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}

.wm-card h2 {
    margin: 0 0 0.6rem;
    font-size: 2.3rem;
    font-weight: 700;
}

.wm-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.wm-list li {
    font-size: 1.18rem;
    margin-bottom: 0.45rem;
    color: #343741;
    font-weight: 500;
}

/* --- BUTTON --- */
.wm-actions {
    margin-top: 1.8rem;
}

/* --- MOBILE --- */
@media (max-width: 900px) {
    .wm-grid {
        grid-template-columns: 1fr;
    }
}

</style>
""", unsafe_allow_html=True)

st.markdown(
        """
            <head>
        <title>Why AI Name Matching Matters in Reinsurance | RematchingAI</title>
        <meta name="description" content="Discover why accurate AI name matching is essential for reinsurers, brokers, and insurers. Improve data quality, reduce duplication, strengthen compliance, and automate bordereaux workflows with RematchingAI.">
        <meta name="keywords" content="AI name matching, reinsurance data quality, entity resolution, bordereaux automation, insurance data cleansing, KYC AML screening, fuzzy matching, insured name matching">
        <meta name="robots" content="index, follow">
        <link rel="canonical" href="https://rematchingai.com/whymatch">
    </head>
        <style>
            div[data-testid="stButton"] button[kind="primary"][data-testid="stBaseButton-primary"] {
                min-height: 2.9rem;
                padding: 0.3rem 1.15rem;
                border-radius: 0.65rem;
                border: 1px solid rgba(0, 0, 0, 0.04);
                background: linear-gradient(180deg, #0f62ff, #084dce);
                color: #ffffff;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: 0.96rem;
                font-weight: 700;
                box-shadow: 0 8px 16px rgba(15, 98, 255, 0.22);
            }
        </style>
        """,
        unsafe_allow_html=True,
)

# --- PAGE CONTENT ---
st.markdown("""
<section class="wm-shell">

<h1 class="wm-title">
  Why Re<span class="wm-title-em">Match</span> is different
</h1>

<p class="wm-subtitle">
  Generic Insured Name Matching tools fail on reinsurance data.
  We built a specialised engine that understands the context of your industry.
</p>

<div class="wm-grid">

  <article class="wm-card">
    <h2>Now</h2>
    <ul class="wm-list">
      <li>Multi-Method Matching (6 Methods)</li>
      <li>Self-Learning AI</li>
      <li>Built Specifically For Reinsurance</li>
    </ul>
  </article>

  <article class="wm-card">
    <h2>Soon</h2>
    <ul class="wm-list">
      <li>Batch Processing</li>
      <li>Exposure Calculation</li>
      <li>RCR &amp; RDS Reporting</li>
      <li style="opacity:0;">placeholder</li>
    </ul>
  </article>

</div>

</section>
""", unsafe_allow_html=True)

left_spacer, button_col, right_spacer = st.columns([4, 2, 4])
with button_col:
        if st.button("Back to Landing", type="primary", use_container_width=True, key="why_match_back_to_landing"):
                st.query_params["page"] = "landing"
                st.rerun()
