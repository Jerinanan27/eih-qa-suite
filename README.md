# Engineering Intelligence Hub — QA & AI-Evaluation Suite

A complete quality-assurance suite for a hybrid-retrieval **RAG** system
([Engineering Intelligence Hub](https://github.com/Jerinanan27/engineering-intelligence-hub)),
covering API contract testing, UI automation, load testing, and **LLM/RAG output
evaluation** — groundedness, relevance, factual correctness, retrieval quality, and
answer consistency under non-determinism.

Testing an AI system requires more than asserting on status codes. The same question
never returns the same string twice, so correctness has to be measured against an
evaluation set with tolerance thresholds rather than exact-match assertions. This suite
combines conventional QA layers with that kind of probabilistic validation against a
single system under test.

## What's covered

| Layer | Approach | Tooling |
|---|---|---|
| Test strategy & documentation | Master test plan, defect log, severity/priority triage | Markdown, GitHub Issues |
| API | Contract, schema, and negative testing | PyTest + requests, Postman, Newman |
| UI | End-to-end browser automation | Playwright (Python) |
| Performance | Ramped-concurrency load testing with SLO thresholds | k6 |
| AI output quality | Evaluation-set scoring and tolerance-based validation | DeepEval, sentence-transformers |
| Continuous integration | Provisions the SUT and runs tests on every commit | GitHub Actions |

## System under test

The Engineering Intelligence Hub is a retrieval-augmented question-answering service over
engineering documentation, source code, incident reports, and architecture diagrams. It
exposes a FastAPI service (`/healthz`, `/ingest`, `/ask`) and a Streamlit UI, and returns
citation-backed answers assembled from dense retrieval, BM25, reciprocal-rank fusion,
cross-encoder reranking, and LLM generation.

Its `/ask` endpoint is the primary target: it exercises the full pipeline, returns a
structured citation schema that can be asserted against, and is the slowest and most
failure-prone path in the system.

## Results

All layers executed against a live instance.

| Layer | Result |
|---|---|
| API contract + negative tests | 6 passed, 1 xfailed (BUG-001, tracked) |
| Postman / Newman collection | all assertions passed |
| UI automation (Playwright) | 3 passed |
| Performance (k6) | p95 **90 ms**, **0% errors**, both thresholds met at 10 VUs |
| RAG output evaluation | 2 passed — retrieval hit-rate and answer consistency |

![API contract tests](docs/screenshots/01-api-contract-tests-passing.jpg)
![Newman collection run](docs/screenshots/05-newman-postman-collection-run.png)
![Playwright UI tests](docs/screenshots/02-playwright-ui-tests-passing.png)
![k6 load test](docs/screenshots/03-k6-load-test-thresholds-passed.png)
![RAG evaluation](docs/screenshots/04-rag-evaluation-retrieval-consistency.jpg)

### Performance analysis

Ramping 3 to 10 concurrent users against `POST /ask`, the retrieval path sustained a p95
latency of 90 ms (median 47 ms, max 125 ms) with a 0% error rate across 607 requests.
Latency stayed flat as concurrency tripled, indicating the pipeline scales linearly at
this load with no bottleneck at 10 VUs.

An earlier run surfaced a content defect rather than a performance one: every request
returned 200 with a valid answer, but the citation assertion failed at 100%. Isolating
that to configuration rather than capacity — and separating availability and latency
from response content — is recorded in `perf/README.md`.

## Evaluating non-deterministic output

Three techniques carry most of the weight in `ai_eval/`:

**Evaluation set.** `goldset_eval.json` holds ten question / ground-truth /
expected-source triples drawn from the indexed corpus. Authoring these is test-case
design applied to a system with no single correct output string.

**Retrieval quality, measured separately from generation.** Retrieval either surfaced the
expected source document or it did not, independent of how the answer was phrased. This
isolates the retrieval stage so a generation regression can't mask a retrieval one.

**Consistency under tolerance.** The same question is asked N times and the answers are
compared by semantic similarity, failing if the mean pairwise score drops below
threshold. Exact-match assertions are meaningless against a model sampling at
temperature > 0; a tolerance band is not.

LLM-judged metrics — faithfulness (groundedness), answer relevancy, and factual
correctness via a G-Eval rubric — are implemented with DeepEval and skipped when no judge
model is configured, so the suite runs green without an API key.

## Defects found

Two defects were identified, documented with reproduction steps and root-cause analysis,
and filed as tracked issues:

- **BUG-001** *(Medium)* — `POST /ask` returns 500 for an invalid `source_types` enum
  value instead of a 422 client error. An unhandled `ValueError` reaches FastAPI as a
  server fault. Pinned with an `xfail` test so the suite stays green while the defect
  stays visible.
- **BUG-002** *(High)* — `POST /ask` returns an opaque 500 when the upstream LLM provider
  call fails (invalid key, deprecated model, or rate limit), discarding successfully
  retrieved citations instead of degrading to retrieval-only output. Makes provider
  outages indistinguishable from application faults in monitoring.

Full write-ups in [`docs/BUG_REPORTS.md`](docs/BUG_REPORTS.md).

## Notes from building it

**Locator ambiguity, not flakiness.** The Playwright citation test failed intermittently
on a strict-mode violation: `name="Sources"` matched both the results heading and a
sidebar "Filter sources" control. Exact matching resolved it. Worth distinguishing a
genuinely ambiguous selector from a timing problem before reaching for a wait.

**Test against a controlled instance.** Initial UI runs targeted a hosted demo that sleeps
when idle, producing three-minute cold starts and a wake-up screen mid-test. Running
against a local instance removed a source of failure that had nothing to do with the
application.

**State is a precondition, not an assumption.** The API keeps its index in memory, so
`/ask` returns empty results until `/ingest` runs. The API suite handles this in a
session fixture; it's a manual step for the load and evaluation layers, documented in the
quickstart below.

## Quickstart

Start the system under test:

```bash
# from the Hub repo
uvicorn eih.api:app                          # API on :8000
curl -X POST localhost:8000/ingest \
     -H 'Content-Type: application/json' \
     -d '{"path":"data/sample"}'             # required: index is in-memory
streamlit run src/eih/ui.py                  # UI on :8501
```

Install and run the suite:

```bash
pip install -r requirements.txt
playwright install chromium
npm i -g newman

BASE_URL=http://localhost:8000 pytest api/ -v        # contract + negative
bash api/run_newman.sh                               # Postman collection
BASE_UI_URL=http://localhost:8501 pytest ui/ -v      # Playwright
k6 run perf/ask_load_test.js                         # load test
BASE_URL=http://localhost:8000 pytest ai_eval/ -v    # RAG evaluation
```

## Layout

```
qa-suite/
├── docs/        TEST_PLAN.md, BUG_REPORTS.md, screenshots/
├── api/         contract tests, Postman collection, Newman runner
├── ui/          Playwright end-to-end tests
├── perf/        k6 load test and performance analysis
├── ai_eval/     evaluation set, retrieval and consistency tests, DeepEval metrics
└── .github/workflows/qa-suite.yml
```
