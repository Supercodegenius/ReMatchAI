import os
import runpy


APP_PATH = os.path.join(os.path.dirname(__file__), "..", "Source", "name_matchingUI.py")
runpy.run_path(APP_PATH, run_name="__main__")
