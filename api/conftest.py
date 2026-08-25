import os, requests, pytest

BASE = os.getenv("BASE_URL", "http://localhost:8000")

@pytest.fixture(scope="session", autouse=True)
def ensure_corpus_ingested():
    """The API does not ingest at startup; load the sample corpus once before any /ask test."""
    try:
        requests.post(f"{BASE}/ingest", json={"path": "data/sample"}, timeout=300)
    except Exception as e:
        pytest.skip(f"Could not reach API at {BASE} to ingest: {e}")
