"""
API contract & negative tests for the Engineering Intelligence Hub FastAPI service.

SUT endpoints (from src/eih/api.py):
  GET  /healthz  -> {"status": "ok"}
  POST /ingest   {"path": "data/sample"} -> ingestion stats
  POST /ask      {"question": str, "source_types": [str]|null}
                 -> {"question", "answer", "citations": [{index, doc_id,
                     source_type, path, score, preview}]}

Run:  BASE_URL=http://localhost:8000 pytest api/ -v
Start the SUT first:  uvicorn eih.api:app   (echo provider needs no LLM key)
"""
import os
import requests
import pytest

BASE = os.getenv("BASE_URL", "http://localhost:8000")
TIMEOUT = 120  # RAG /ask is slow: embed + hybrid retrieve + rerank + generate


# ---------- liveness ----------
def test_healthz_returns_ok():
    r = requests.get(f"{BASE}/healthz", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------- happy path: /ask ----------
@pytest.fixture(scope="module")
def ask_response():
    r = requests.post(f"{BASE}/ask", json={"question": "How are JWTs validated?"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


def test_ask_response_schema(ask_response):
    body = ask_response
    assert {"question", "answer", "citations"}.issubset(body)
    assert isinstance(body["answer"], str) and body["answer"].strip()
    assert isinstance(body["citations"], list) and len(body["citations"]) >= 1


def test_ask_citation_schema(ask_response):
    c = ask_response["citations"][0]
    for field in ("index", "doc_id", "source_type", "score", "preview"):
        assert field in c, f"missing citation field: {field}"
    assert isinstance(c["score"], (int, float))


def test_ask_answer_is_grounded_in_a_returned_source(ask_response):
    """Cheap groundedness proxy: a JWT question should retrieve the auth sources."""
    doc_ids = {c["doc_id"] for c in ask_response["citations"]}
    assert any("auth" in d for d in doc_ids), f"expected an auth source, got {doc_ids}"


# ---------- negative / validation ----------
def test_ask_missing_question_is_422():
    r = requests.post(f"{BASE}/ask", json={}, timeout=TIMEOUT)
    assert r.status_code == 422  # FastAPI/pydantic validation


def test_ask_wrong_type_question_is_422():
    r = requests.post(f"{BASE}/ask", json={"question": 12345}, timeout=TIMEOUT)
    assert r.status_code == 422


@pytest.mark.xfail(
    reason="BUG-001: invalid source_types crashes with 500 (unhandled ValueError "
           "from SourceType(t)) instead of a clean 422. See docs/BUG_REPORTS.md.",
    strict=False,
)
def test_ask_invalid_source_type_should_be_422_not_500():
    r = requests.post(
        f"{BASE}/ask",
        json={"question": "How are JWTs validated?", "source_types": ["banana"]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 422  # desired contract: reject bad enum as client error
