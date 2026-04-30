import os
import runpy
import streamlit as st


BASE_DIR = os.path.dirname(__file__)
DEPLOY_REV = "2026-04-30-payg-pricing"

page = st.query_params.get("page", "landing")

if page == "matcher":
	runpy.run_path(os.path.join(BASE_DIR, "Source", "name_matchingUI.py"), run_name="__main__")
elif page == "whymatch":
	runpy.run_path(os.path.join(BASE_DIR, "Source", "whymatchUI.py"), run_name="__main__")
elif page == "pricing":
	runpy.run_path(os.path.join(BASE_DIR, "Source", "matchpricingUI.py"), run_name="__main__")
elif page == "howmatchworks":
	runpy.run_path(os.path.join(BASE_DIR, "Source", "howmatchworksUI.py"), run_name="__main__")
else:
	runpy.run_path(os.path.join(BASE_DIR, "Source", "landingUI.py"), run_name="__main__")
