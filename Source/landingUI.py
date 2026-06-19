import base64
import os

import streamlit as st


ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
FAVICON_PATH = os.path.join(ASSETS_DIR, "favicon.png.jpeg")
LANDING_CSS_PATH = os.path.join(ASSETS_DIR, "landing.css")


def _safe_set_page_config(**kwargs) -> None:
    try:
        st.set_page_config(**kwargs)
    except Exception:
        pass


def _to_data_uri(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("utf-8")
    ext = os.path.splitext(path)[1].lower().replace(".", "")
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


def _load_css(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


_safe_set_page_config(
    page_title="ReMatch | Landing",
    page_icon=FAVICON_PATH,
    layout="wide",
    initial_sidebar_state="collapsed",
)

logo_data_uri = _to_data_uri(LOGO_PATH)
landing_css = _load_css(LANDING_CSS_PATH)

if landing_css:
    st.markdown(f"<style>{landing_css}</style>", unsafe_allow_html=True)

_dialog_decorator = None
if hasattr(st, "dialog"):
    _dialog_decorator = st.dialog
elif hasattr(st, "experimental_dialog"):
    _dialog_decorator = st.experimental_dialog


def _demo_dialog_body() -> None:
    st.markdown(
        """
In order to book a demo of the tool or for download options of your matched data, please get in touch with the BrainCal Tech on
`braincaldemo@gmail.com` or `surabhi.singh@braincal.com`.

Thanks for your interest!!
""".strip()
    )


if _dialog_decorator is not None:

    @_dialog_decorator("Book a Demo", width="small")
    def _show_demo_dialog() -> None:
        _demo_dialog_body()
        if st.button("Close"):
            st.rerun()

else:

    def _show_demo_dialog() -> None:
        _demo_dialog_body()


_open_demo_dialog = str(st.query_params.get("demo", "")).strip() == "1"
if _open_demo_dialog:
    try:
        del st.query_params["demo"]
    except KeyError:
        pass

# 🔥 HTML MUST START AT COLUMN 0 — NO INDENTATION AT ALL
st.markdown(
f"""
        <title>AI Name Matching for Reinsurance | RematchingAI</title>
        <meta name="description" content="RematchingAI delivers award-winning AI name matching and entity resolution for reinsurers, brokers, and insurers. Improve data quality, reduce duplication, and automate bordereaux and compliance workflows.">
        <meta name="keywords" content="AI name matching, entity resolution, reinsurance automation, insurance data quality, bordereaux automation, KYC AML screening, fuzzy matching, insured name matching">
        <meta name="robots" content="index, follow">
        <link rel="canonical" href="https://rematchingai.com/">
<section class="landing-shell">
<nav class="landing-nav">
<div class="brand-wrap">
<img class="brand-logo" src="{logo_data_uri}" alt="ReMatch" />
<span class="brand-dot">•</span>
<span class="brand-tagline">AI-Powered Insured Name Matching for Reinsurance</span>
</div>
<div class="nav-cta">
<a class="cta-btn" href="?page=landing&demo=1" target="_self">Get in Touch</a>
<a class="cta-btn" href="https://cal.com/rematchingai/30mins?overlayCalendar=true" target="_blank">Book a Demo</a>
<a class="cta-btn" href="?page=matcher" target="_self">Tool Play</a>
</div>
</nav>

<main class="hero">
<div class="hero-inner">
<div class="hero-chip">✧ AI-Powered</div>

<h1>Your exposure is only as good<br>as your data</h1>

<p>
ReMatch cleans and matches messy reinsurance bdx data using AI techniques and six intelligent
matching methods, so the numbers you rely on are the numbers you can trust.
</p>

<div class="hero-cta">
<a class="cta-btn" href="?page=whymatch" target="_self">Why Match</a>
<a class="cta-btn" href="?page=rematchpricing" target="_self">Price Model</a>
<a class="cta-btn" href="?page=howmatchworks" target="_self">How it Works</a>
</div>

</div>
</main>
</section>
""",
    unsafe_allow_html=True,
)

if _open_demo_dialog:
    _show_demo_dialog()