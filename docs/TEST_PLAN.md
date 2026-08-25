# Test Plan — Engineering Intelligence Hub QA Suite

**Author:** Jerin Anan Proma · **Version:** 1.0 · **Type:** Master test plan (IEEE-829-inspired, lightweight)

## 1. Objective
Validate the functional correctness, API contract, performance under load, and
**AI/RAG output quality** of the Engineering Intelligence Hub — a hybrid-retrieval
RAG service exposing a FastAPI API, a Streamlit UI, and a CLI.

## 2. Scope
**In scope:** `/healthz`, `/ingest`, `/ask` API contract & negative cases; the
Streamlit ask→answer→citations flow; load behaviour of `/ask`; groundedness,
relevance, correctness, retrieval quality, and answer consistency of generated
answers.
**Out of scope:** model training/fine-tuning; the ingestion internals of
third-party libraries (Qdrant, sentence-transformers); vision-captioning accuracy.

## 3. Test items & approach
| Layer | Technique | Tool | Location |
|---|---|---|---|
| API contract | Positive, negative, schema validation | pytest + requests; Postman/Newman | `api/` |
| UI E2E | Black-box, exploratory-to-scripted | Playwright (Python) | `ui/` |
| Performance | Load / stress (ramped concurrency) | k6 (JMeter-portable) | `perf/` |
| AI/RAG quality | Metric-based eval, tolerance validation | DeepEval + custom | `ai_eval/` |

## 4. Entry / exit criteria
- **Entry:** SUT reachable (`/healthz` = 200); sample corpus ingested.
- **Exit:** all contract tests pass; retrieval hit-rate ≥ 0.75; answer-consistency
  ≥ 0.75 tolerance; faithfulness/relevancy ≥ 0.7; all open defects triaged with a
  severity and a tracking issue.

## 5. Test design techniques used
Equivalence partitioning & boundary analysis (valid/invalid `question`,
`source_types`), negative testing (missing/malformed fields), and
**tolerance-based validation** for non-deterministic LLM output (semantic
similarity thresholds instead of exact match).

## 6. Environment
Python 3.11; SUT run with the `echo` provider (no LLM key) for deterministic CI,
or Groq/Ollama for full generation locally. k6 and Newman installed for perf/API.

## 7. Risks
- **Non-determinism:** LLM output varies run-to-run → mitigated by tolerance
  thresholds, not exact-match assertions.
- **Live demo cold-start:** the hosted Streamlit demo sleeps → UI tests wake it
  and use generous timeouts.
- **Cost/rate limits** on any hosted judge model → DeepEval pointed at a free model.

## 8. Deliverables
Automated suites (this repo), a defect log (`docs/BUG_REPORTS.md`), CI workflow
(`.github/workflows/qa-suite.yml`), and this plan.
