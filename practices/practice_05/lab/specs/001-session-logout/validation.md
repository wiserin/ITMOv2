# Session Logout — implementation evidence

## Environment and architectural gate (T001)

- Python 3.14.7; uv 0.11.28; host Node 26.9.0/npm 11.19.1.
- Node 22.23.4 available through `npm exec --package=node@22`.
- Docker Desktop available. PostgreSQL 18 disposable container
  `animemap-logout-test-db`, isolated port 55432; existing volumes untouched.
- `uv sync --group migrations --group service --group tests`: PASS.
- Existing Alembic head `43b8dfef97c1` applied to disposable database;
  `alembic check`: PASS, no drift. Test POSTGRES_* from quickstart.
- Constitution I–VI, naming/codestyle and approved ADR-01–ADR-11 reviewed.
  Domain ports, ordinary function-scope DI/factory commit, no Logout renewal,
  user→session locks, same-origin,15/20s and accepted cookie race preserved.
- Requirements checklist:21/21 checked, read-only.
- Runtime dependencies unchanged. Existing backend/frontend dockerignore and
  frontend gitignore reviewed; private npm package needs no publishing ignore.

## Progress

Implementation in progress. Unexecuted, skipped or blocked checks are not PASS.

### Phase 1 — setup

- T002: pinned dev-only Vitest3.2.4/jsdom26.1.0/Testing Library16.3.0/
  user-event14.6.1; `npm run test:unit -- --passWithNoTests` loads config
  successfully (tooling smoke only, not functional coverage). Node22 build PASS.
- T003: real PostgreSQL seed→independent snapshot→cleanup smoke PASS with
  production SessionController, NullPool only for cross-loop test isolation.
- T004: real HTTPS `/health` request PASS with certificate validation and
  NODE_EXTRA_CA_CERTS. Generated two-day localhost certificate/key outside Git
  in approved temporary directory. Browser config optionally pins TLS_SPKI;
  it does not disable all certificate validation.
- API fixture register/login/cleanup smoke: first run failed because test
  idle-timeout DI was not overridden; fixed test-only DI, rerun PASS.
  Production Auth dependency remains a separate transaction in the harness.
- npm install reported3 advisories (1 moderate,2 critical); no automatic
  force upgrade performed. Runtime versions remain unchanged.

### Phase 2 — foundation

- T005/T006: `npm run test:unit -- tests/unit/sessionState.test.ts`:
  RED (module absent), then5 tests PASS; `npm run typecheck`: PASS.
- T007/T008: Node raw HTTP contract test RED (404 instead of405), then
  `npm test`:9 tests PASS, including existing login/register/search/static.
- T009/T010: `pytest tests/api/test_repository_di.py
  tests/integration/database/test_logout_commit.py -q` with real test DB:
  RED (2 unsafe-log assertions), then5 tests PASS. ASGI start follows
  function finalization. Actual Logout commit-order test is still T061.
- `uvx ruff check app/infrastructure/database/session.py
  tests/integration/database/logout_support.py
  tests/integration/database/test_logout_commit.py
  tests/api/test_repository_di.py`: PASS after line/import formatting fix.
