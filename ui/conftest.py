import os
import pytest

# Point at the live Streamlit Community Cloud demo by default; override for local:
#   BASE_UI_URL=http://localhost:8501 pytest ui/
DEFAULT_UI = "https://engineering-intelligence-app-ojzakhcjhz6depgb7ppehz.streamlit.app/"


@pytest.fixture(scope="session")
def ui_url():
    return os.getenv("BASE_UI_URL", DEFAULT_UI)
