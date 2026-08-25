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
