"""
LLM / RAG output-quality evaluation as pytest tests.

This is the piece most junior QA candidates cannot show. It evaluates the SUT's
generated answers the way the Cloudly JD describes -- faithfulness/groundedness,
answer relevancy, factual correctness, retrieval quality, and CONSISTENCY under
non-determinism -- using an eval set and TOLERANCE thresholds, not exact match.

Two layers:
  A) LLM-judged metrics via DeepEval (faithfulness, answer relevancy, correctness).
  B) A dependency-light consistency test (same question x N, semantic agreement),
     which needs no judge LLM and directly demonstrates tolerance-based validation
     of non-deterministic output.

Setup:
  pip install deepeval sentence-transformers requests
  # DeepEval uses an LLM judge. Point it at a free model to avoid OpenAI cost, e.g.
  # export it per DeepEval's current docs (Ollama / Groq / a local model).
  BASE_URL=http://localhost:8000 pytest ai_eval/ -v

NOTE: DeepEval's metric API evolves quickly -- confirm class/param names against
the version you install. The consistency test (layer B) has no such dependency.
"""
import os
import json
from pathlib import Path

import pytest
import requests

BASE = os.getenv("BASE_URL", "http://localhost:8000")
GOLD = json.loads((Path(__file__).parent / "goldset_eval.json").read_text())
TIMEOUT = 120


def _ask(question, source_types=None):
    payload = {"question": question}
    if source_types:
        payload["source_types"] = source_types
    r = requests.post(f"{BASE}/ask", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# ============================================================
# Layer A — LLM-judged metrics (DeepEval)
# ============================================================
deepeval = pytest.importorskip("deepeval", reason="pip install deepeval to run LLM-judged metrics")
from deepeval import assert_test  # noqa: E402
from deepeval.test_case import LLMTestCase  # noqa: E402
from deepeval.metrics import (  # noqa: E402
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    GEval,
)
from deepeval.test_case import LLMTestCaseParams  # noqa: E402


def _to_testcase(item):
    resp = _ask(item["question"])
    retrieval_context = [c.get("preview", "") for c in resp["citations"]]
    return LLMTestCase(
        input=item["question"],
        actual_output=resp["answer"],
        expected_output=item["ground_truth"],
        retrieval_context=retrieval_context,
    )


@pytest.mark.parametrize("item", GOLD, ids=[g["question"] for g in GOLD])
def test_answer_is_faithful_to_retrieved_context(item):
    """Groundedness / hallucination guard: every claim must be supported by context."""
    tc = _to_testcase(item)
    assert_test(tc, [FaithfulnessMetric(threshold=0.7)])


@pytest.mark.parametrize("item", GOLD, ids=[g["question"] for g in GOLD])
def test_answer_is_relevant(item):
    tc = _to_testcase(item)
    assert_test(tc, [AnswerRelevancyMetric(threshold=0.7)])


@pytest.mark.parametrize("item", GOLD, ids=[g["question"] for g in GOLD])
def test_answer_is_factually_correct(item):
    correctness = GEval(
        name="Correctness",
        criteria="Is the actual output factually consistent with the expected answer? "
                 "Penalise contradictions and unsupported specifics.",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=0.6,
    )
    assert_test(_to_testcase(item), [correctness])


# ============================================================
# Layer B — retrieval quality + consistency (no judge LLM)
# ============================================================
def test_retrieval_hits_expected_source():
    """Retrieval quality: expected source doc must appear in citations (hit@k)."""
    misses = []
    for item in GOLD:
        resp = _ask(item["question"])
        got = {c["doc_id"] for c in resp["citations"]}
        if not (set(item["expected_source_ids"]) & got):
            misses.append((item["question"], sorted(got)))
    hit_rate = 1 - len(misses) / len(GOLD)
    assert hit_rate >= 0.75, f"retrieval hit-rate {hit_rate:.2f} below tolerance; misses={misses}"


def test_answer_consistency_under_nondeterminism():
    """
    Tolerance-based validation of non-deterministic output: ask the SAME question
    N times and require the answers to be semantically consistent (mean pairwise
    cosine >= tolerance). This is the 'non-deterministic outputs / tolerance-based
    validation' item in the JD, made concrete.
    """
    st = pytest.importorskip("sentence_transformers")
    from itertools import combinations
    import numpy as np

    model = st.SentenceTransformer("all-MiniLM-L6-v2")
    N, TOLERANCE = 3, 0.75
    question = "How are JWTs validated?"

    answers = [_ask(question)["answer"] for _ in range(N)]
    embs = model.encode(answers, normalize_embeddings=True)
    sims = [float(np.dot(embs[i], embs[j])) for i, j in combinations(range(N), 2)]
    mean_sim = sum(sims) / len(sims)
    assert mean_sim >= TOLERANCE, (
        f"answers drift across runs: mean pairwise similarity {mean_sim:.2f} < {TOLERANCE}. "
        f"sims={[round(s,2) for s in sims]}"
    )
