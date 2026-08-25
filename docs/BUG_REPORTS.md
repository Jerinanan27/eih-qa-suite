# Defect Log

> Format mirrors a Jira/GitHub-Issue defect: ID, severity, environment, steps,
> expected vs. actual, evidence, status. File each of these as a **GitHub Issue**
> on the SUT repo and link it here — that closes the defect lifecycle loop the JD asks for.

---

## BUG-001 — Invalid `source_types` value returns HTTP 500 instead of 422
- **Severity:** Medium · **Priority:** Medium · **Type:** Input validation / error handling
- **Component:** `POST /ask` (FastAPI, `src/eih/api.py`)
- **Environment:** local, echo provider, main branch

**Steps to reproduce**
1. Start the API: `uvicorn eih.api:app`
2. `POST /ask` with body:
   ```json
   {"question": "How are JWTs validated?", "source_types": ["banana"]}
   ```

**Expected:** `422 Unprocessable Entity` with a clear message that `source_types`
must be one of the valid `SourceType` values (client error).

**Actual:** `500 Internal Server Error`. Root cause: `api.py` does
`SourceType(t)` on each value; an unknown value raises an unhandled `ValueError`,
which FastAPI surfaces as a 500 — a server error for what is really bad client input.

**Suggested fix:** validate against the enum and return a 422 (e.g. accept
`source_types: list[SourceType]` in the Pydantic model, or catch `ValueError` and
raise `HTTPException(422, ...)`).

**Evidence:** covered by `api/test_api_contract.py::test_ask_invalid_source_type_should_be_422_not_500`
(marked `xfail` until fixed) and the Newman test "Ask - negative: invalid source_type (BUG-001)".

**Status:** OPEN

---

## BUG-TEMPLATE — copy for new defects
- **Severity:** … · **Priority:** … · **Type:** …
- **Component:** …
- **Environment:** …
- **Steps to reproduce:** …
- **Expected:** …
- **Actual:** …
- **Evidence:** (screenshot / failing test / response body)
- **Status:** OPEN / IN PROGRESS / FIXED / VERIFIED / CLOSED


## BUG-002 — `/ask` returns HTTP 500 when the LLM provider call fails, instead of degrading gracefully

- **Severity:** High · **Priority:** High · **Type:** Error handling / resilience
- **Component:** `POST /ask` — `src/eih/generation.py` (`_groq`, line ~84) via `pipeline.py` → `api.py`
- **Environment:** local, `provider: auto` with `GROQ_API_KEY` set, `groq_model: openai/gpt-oss-120b`, main branch
- **Found by:** automated API contract and performance testing (k6 load run + `/docs` manual verification)

### Steps to reproduce
1. Start the API with an **invalid or expired** `GROQ_API_KEY` set in the environment:
   ```
   $env:GROQ_API_KEY="gsk_invalid_key"
   python -m uvicorn eih.api:app --host 127.0.0.1 --port 8000
   ```
2. Ingest the sample corpus: `POST /ingest` with `{"path": "data/sample"}` → 200 OK (5 documents, 14 chunks).
3. Call `POST /ask` with `{"question": "How are JWTs validated?"}`.

### Expected
Retrieval succeeds independently of generation, so the service should either:
- return **200** with the retrieved citations and a clear notice that generation is unavailable
  (the same graceful degradation the `echo` provider already implements), or
- return a **502 / 503** with an explanatory message indicating an upstream LLM provider failure.

Either way the client should be able to distinguish "the LLM provider is unavailable"
from "this service is broken."

### Actual
**HTTP 500 Internal Server Error** with an empty, non-JSON body (`Internal Server Error`,
`content-type: text/plain`). The response gives the client no indication of the cause, and
the successfully-retrieved citations are discarded.

Server traceback (abridged):
```
File "src/eih/generation.py", line 84, in _groq
    r.raise_for_status()
requests.exceptions.HTTPError: 401 Client Error: Unauthorized for url:
https://api.groq.com/openai/v1/chat/completions
```

### Root cause
`_groq()` calls `r.raise_for_status()` with no surrounding exception handling. Any non-2xx
response from the provider — `401` (bad key), `404` (deprecated/renamed model), `429`
(rate limit) — raises `requests.exceptions.HTTPError`, which propagates unhandled through
`pipeline.ask()` and the FastAPI route, and FastAPI converts it into a generic 500.

This makes an **upstream dependency failure** indistinguishable from an internal defect, and
throws away the retrieval work that already succeeded.

### Impact
- The entire `/ask` endpoint fails whenever the LLM provider is unavailable, even though
  retrieval — the core RAG capability — is healthy and returning correct sources.
- Rate limiting (`429`) on a free provider tier will cause intermittent 500s in production.
- Provider model deprecation silently breaks the service: a `404` on a renamed model ID
  produces the same opaque 500 (observed with the now-deprecated `llama-3.3-70b-versatile`).
- Monitoring and alerting cannot distinguish provider outages from application bugs.

### Suggested fix
Wrap the provider call and fall back to the retrieval-only response path:

```python
try:
    r = requests.post(..., timeout=self.cfg.timeout)
    r.raise_for_status()
except requests.exceptions.RequestException as exc:
    logger.warning("LLM provider unavailable, degrading to retrieval-only: %s", exc)
    return _retrieval_only_notice()   # same output shape the echo provider returns
```

Optionally surface the degraded state to the client (e.g. a `generation_available: false`
field in the response) so callers can render appropriately.

### Evidence
- Server traceback above (`401 Client Error`, `generation.py:84`).
- k6 load run: `status is 200` and `has an answer` passed on the echo provider, while the
  same requests returned 500 with a failing provider — confirming retrieval is unaffected.
- `POST /ingest` returned 200 with 14 chunks immediately before the failing `/ask` call,
  proving the index was populated and retrieval was healthy.

### Regression test
Once fixed, assert that `/ask` returns a non-5xx status and preserves citations when the
provider is unreachable (simulate with an invalid key or a mocked provider error).

**Status:** OPEN


**Tracking issue:** https://github.com/Jerinanan27/engineering-intelligence-hub/issues/1
**Tracking issue:** https://github.com/Jerinanan27/engineering-intelligence-hub/issues/2
