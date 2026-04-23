import os
import runpy
import streamlit as st


BASE_DIR = os.path.dirname(__file__)

runpy.run_path(os.path.join(BASE_DIR, "Source", "name_matchingUI.py"), run_name="__main__")
