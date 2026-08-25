# Performance testing — `/ask` under load (k6)

## Why k6 (and where JMeter fits)
The JD lists **k6/JMeter**; either satisfies it. I use **k6** here because the
script is plain JavaScript — it lives in Git, diffs cleanly, and runs in CI in one
line, which matches the JD's "integrate into CI/CD" requirement better than
JMeter's GUI/XML `.jmx` files. If a team standardises on JMeter, the same plan
ports directly: a Thread Group ramping 3→5→10 users, an HTTP Request sampler to
`POST /ask`, a JSON Extractor + Response Assertion on `answer`/`citations`, and a
Summary/Aggregate report. Keep both in your vocabulary; lead with k6 in the repo.

## What this test does
Ramps virtual users 3 → 5 → 10 against `POST /ask`, recording latency and error
rate, with pass/fail **thresholds** (`p95 < 15s`, `errors < 5%`).

## How to read the result
- **`ask_latency_ms` p95 climbing steeply as VUs rise** → the pipeline is
  concurrency-bound. The usual culprit in this architecture is the
  **cross-encoder rerank + LLM generation** stage (CPU-bound, not I/O-bound),
  so more concurrent requests queue on the same compute.
- **`ask_errors` rising before latency** → capacity/timeout ceiling hit.
- **Bottleneck write-up (do this):** run once at 1 VU to get the baseline
  single-request latency, then at 10 VU. If p95 at 10 VU ≫ 10× the baseline, the
  system does not scale linearly — name the rerank/LLM stage as the suspect and
  recommend batching or a smaller reranker. That sentence is the "identify
  bottlenecks" deliverable.
