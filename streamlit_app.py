import os
import runpy
import streamlit as st

BASE_DIR = os.path.dirname(__file__)
DEPLOY_REV = "2026-04-30-payg-pricing"

def _safe_set_page_config(**kwargs):
    try:
        st.set_page_config(**kwargs)
    except Exception:
        pass

_safe_set_page_config(
    page_title="ReMatch",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ⭐ REAL FIX: Remove Streamlit's root padding + centre all pages
st.markdown("""
<style>

/* Remove Streamlit's global padding */
div[data-testid="stAppViewContainer"] {
    padding: 0 !important;
    margin: 0 !important;
}

/* Remove padding inside main block */
div[data-testid="stAppViewContainer"] > div {
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}

/* Force the entire content area to be centred */
div[data-testid="stAppViewContainer"] > div:nth-child(1) {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
}

/* Ensure the child page expands full width */
div[data-testid="stAppViewContainer"] > div:nth-child(1) > div {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 auto !important;
}

</style>
""", unsafe_allow_html=True)

# --- PAGE ROUTING ---
page = st.query_params.get("page", "landing")

if page == "matcher":
    runpy.run_path(os.path.join(BASE_DIR, "Source", "name_matchingUI.py"), run_name="__main__")
elif page == "whymatch":
    runpy.run_path(os.path.join(BASE_DIR, "Source", "whymatchUI.py"), run_name="__main__")
elif page in ("rematchpricing", "pricing"):
    runpy.run_path(os.path.join(BASE_DIR, "Source", "matchpricingUI.py"), run_name="__main__")
elif page == "howmatchworks":
    runpy.run_path(os.path.join(BASE_DIR, "Source", "howmatchworksUI.py"), run_name="__main__")
else:
    runpy.run_path(os.path.join(BASE_DIR, "Source", "landingUI.py"), run_name="__main__")
