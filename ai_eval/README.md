# AI/ML output evaluation — the differentiator

The Cloudly JD's hardest requirement is testing **LLM/RAG outputs** for
*accuracy, relevance, consistency, hallucinations, groundedness* using
*evaluation sets, non-deterministic outputs, and tolerance-based validation*.
This folder does exactly that against your own RAG service.

| JD phrase | Test here |
|---|---|
| Groundedness / hallucinations | `test_answer_is_faithful_to_retrieved_context` (DeepEval FaithfulnessMetric) |
| Relevance | `test_answer_is_relevant` (AnswerRelevancyMetric) |
| Factual correctness vs. ground truth | `test_answer_is_factually_correct` (GEval rubric) |
| Retrieval quality | `test_retrieval_hits_expected_source` (hit@k vs. expected sources) |
| Non-determinism / tolerance-based validation | `test_answer_consistency_under_nondeterminism` |

**Eval set:** `goldset_eval.json` — question / ground-truth-answer / expected-source
triples. Writing these *is* test-case design applied to a non-deterministic system;
grow it and the coverage grows with it. It extends the `eval/goldset.json` your Hub
already ships with (which computes hit@k, MRR, citation-rate).

**Interview line:** "The consistency test asks the same question three times and
fails if the answers disagree beyond a semantic-similarity tolerance — that's how
you regression-test a system that never returns the same string twice."
