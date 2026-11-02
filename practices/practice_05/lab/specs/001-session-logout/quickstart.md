# Session Logout: Quickstart Validation Guide

**Date**: 2026-11-02. Это руководство **для будущей реализации** после её отдельного разрешения.
Ни одна команда приложения/тестов ниже при планировании не выполнялась.
Сейчас Logout и часть тестового tooling отсутствуют; исполнение существующей baseline suite
само по себе не подтверждает C-01–C-27.

Связанные артефакты: [plan](plan.md), [test strategy](test-strategy.md),
[HTTP contract](contracts/logout-http.md), [UI contract](contracts/logout-ui.md),
[data model](data-model.md).
Все cwd ниже относительно `practices/practice_05/lab/`.

## 1. Prerequisites

- Python3.14+, uv, Docker; Node22.12+ и npm.
- Изолированная PostgreSQL18 test DB; existing Alembic head применён, schema не меняется.
- Для HTTPS: TLS_CERT/TLS_KEY к тестовым сертификату/ключу, TLS_CA к доверенному CA-файлу.
  Ключи предоставляются окружением, не коммитятся. Browser test profile должен доверять CA.
- Для full-stack: валидный base64 PEM Ed25519 JWT_PRIVATE_KEY и PostgreSQL/Redis окружение
  из existing backend README/.env.example. Пустой test key ниже не подходит запуску run.py.
- Playwright Chromium установлен. Два HTTPS-режима: fixture upstream для transport tests
  и настоящий API для сохранения сессии; последний не использует page.route API interception.

## 2. Backend: disposable database and test environment

Команда создания **отдельной** ephemeral БД использует существующий PostgreSQL image;
это валидационная инфраструктура, не новая версия project Compose. Порт55432 и имя
animemap-logout-test-db должны быть свободны. Cwd для Docker-команд произвольный.

```bash
docker run --rm -d \
  --name animemap-logout-test-db \
  --publish 127.0.0.1:55432:5432 \
  --tmpfs /var/lib/postgresql \
  --env POSTGRES_USER=animemap_test \
  --env POSTGRES_PASSWORD=animemap_test_only \
  --env POSTGRES_DB=animemap_logout_test \
  postgres:18-alpine

docker exec animemap-logout-test-db \
  pg_isready -U animemap_test -d animemap_logout_test
```

Перейти дальше только после успешной readiness-проверки. Для следующих команд cwd `backend/`.
В отдельном test shell экспортировать все обязательные AppConfig поля **до Python imports**:

```bash
export POSTGRES_USER=animemap_test
export POSTGRES_PASSWORD=animemap_test_only
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT=55432
export POSTGRES_DB=animemap_logout_test
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export REDIS_DB=0
export REDIS_PASSWORD=unused_for_database_tests
export JWT_PRIVATE_KEY=
export SESSION_IDLE_TIMEOUT_MINUTES=30
export TEST_DATABASE_URL='postgresql+asyncpg://animemap_test:animemap_test_only@127.0.0.1:55432/animemap_logout_test'

uv sync --group migrations --group service --group tests
uv run --group migrations alembic upgrade head
uv run --group migrations alembic check
uv run --group tests pytest tests/unit
uv run --group tests pytest tests/api
uv run --group tests pytest tests/integration/database
uvx ruff check app tests migrations run.py
```

Это существующие команды/группы зависимостей. Alembic использует POSTGRES_*, pytest integration
использует process TEST_DATABASE_URL: они должны указывать на одну disposable БД.
Настоящий Redis для этих DB tests не нужен; его поля удовлетворяют shared AppConfig.
Fixtures используют генерируемый test JWT key. Новые production-factory tests также обязаны
внедрять test security providers и test controller, не production lifespan с пустым key.

Ожидается: schema check без drift; все будущие D/A/H/P Logout suites и baseline tests PASS,
не skipped. Отсутствие TEST_DATABASE_URL даёт skip и не доказывает real-PG гарантии.
Integration fixtures с commit требуют явного cleanup; не запускать их против рабочей БД.

### Focused commands после создания запланированных тестов

Эти пути **пока не существуют**; команды предназначены для будущей проверки:

```bash
uv run --group tests pytest \
  tests/unit/domain/test_session_close.py \
  tests/unit/application/test_logout.py \
  tests/api/test_logout.py

uv run --group tests pytest \
  tests/integration/database/test_logout.py \
  tests/integration/database/test_logout_concurrency.py \
  tests/integration/database/test_logout_commit.py -vv
```

Результат должен включать PG-1–PG-7 из test-strategy, независимые observer reads,
production SessionController и отсутствие ASGI response.start до commit.
Для fault model unknown acknowledgement observer может видеть committed close,
но HTTP остаётся ошибкой без deletion и без обещания rollback.

## 3. Frontend baseline, unit и proxy tests

Cwd `frontend/`. Существующие команды:

```bash
npm ci
npm run build
npm test
npx playwright install chromium
npm run test:e2e -- tests/browser/app.spec.ts --workers=1
```

Build обязателен до Node static/browser tests: server раздаёт dist, не Vite dev sources.
`dev` — Node watch, не HMR. npm test уже запускает node:test server tests;
расширенный файл проверит Logout proxy и сохранит регистрацию303→201.

После добавления dev-only Vitest/Testing Library, `test:unit` и новых suites:

```bash
npm run test:unit
npm run test:e2e -- tests/browser/logout.spec.ts --workers=1
```

`test:unit` **отсутствует сейчас**. Ожидается PASS transport/state/components,
exact19999/20000ms tests, deferred event orders UI-1–UI-3, отсутствие duplicate send/autoqueue,
старые callbacks не меняют новые данные/slot. Browser mocked UI suite не доказывает cookie/commit.

## 4. Full stack and actual HTTPS boundary

Запуск API — в отдельном runtime shell, **не с пустым JWT_PRIVATE_KEY test shell**.
Подготовить существующий `backend/.env` по backend README с валидным Ed25519 key.
Cwd `lab/` (root Compose включает backend):

```bash
docker compose --env-file backend/.env up --build --wait
docker compose --env-file backend/.env ps --all
```

Ожидается: healthy database/cache, migration service completed, API доступен на8080
при default BACKEND_PORT. Сам API endpoint HTTP не заменяет browser→proxy HTTPS проверку.
Для ручного HTTPS frontend cwd `frontend/`, TLS_* уже экспортированы окружением:

```bash
PUBLIC_ORIGIN=https://localhost:3443 \
TLS_CERT="$TLS_CERT" TLS_KEY="$TLS_KEY" \
API_ORIGIN=http://127.0.0.1:8080 PORT=3443 npm start
```

TLS startup поддержан сейчас; PUBLIC_ORIGIN будет добавлен реализацией плана.
Нельзя использовать arbitrary client X-Forwarded-Proto как доверенную публичную схему.
Для test runs порт3443 освобождается, поскольку HTTPS config запускает собственный server.

### Автоматическая HTTPS-приёмка после реализации

Планируемый `playwright.https.config.ts` использует environment TLS_CERT/TLS_KEY,
PUBLIC_ORIGIN и LOGOUT_E2E_MODE:

- `fixture`: config/harness запускает локальный управляемый upstream и настоящий Node proxy;
  HTTP delays/redirect/status/cookie задаются fixture, а не browser API interception.
- `api`: тот же HTTPS proxy обращается к API_ORIGIN, работающему с реальной PostgreSQL.
  Harness создаёт и убирает отдельные test users/sessions через baseline/test fixtures.

```bash
LOGOUT_E2E_MODE=fixture PUBLIC_ORIGIN=https://localhost:3443 \
  npm run test:e2e -- --config=playwright.https.config.ts --workers=1

LOGOUT_E2E_MODE=api PUBLIC_ORIGIN=https://localhost:3443 \
API_ORIGIN=http://127.0.0.1:8080 \
  npm run test:e2e -- --config=playwright.https.config.ts --workers=1
```

Этот config/режимы — **будущие**, не существующие scripts, не выполненные проверки.
Ожидается: реальная cookie с Secure/HttpOnly/host-only/Path=/;204/401 её удаляют,
прочие ошибки не отправляют session mutation. В api-mode после204 сохранённый тестовым
harness credential даёт401, независимая сессия остаётся пригодной. App JS не получает JWT.

### Ручные публичные негативные сценарии

Через работающий HTTPS proxy, cwd произвольный, TLS_CA указывает на CA-файл:

```bash
export LOGOUT_URL=https://localhost:3443/v1/auth/logout

curl --silent --show-error --include --cacert "$TLS_CA" \
  --request GET "$LOGOUT_URL"

curl --silent --show-error --include --cacert "$TLS_CA" \
  --request POST --data-binary '{}' "$LOGOUT_URL"

curl --silent --show-error --include --cacert "$TLS_CA" \
  --request POST --header 'X-AnimeMap-Logout: 1' \
  --data-binary '{}' "$LOGOUT_URL"

curl --silent --show-error --include --cacert "$TLS_CA" \
  --request POST --header 'X-AnimeMap-Logout: 1' "$LOGOUT_URL"
```

Последовательно ожидаются405/Allow: POST,403/CSRF,400/форма,401/missing_session_cookie.
Все контролируемые ответы no-store/envelope, где body разрешён; только последний содержит
удаление session_token. Нет Origin не отменяет CSRF. Эти запросы не выполняют auth записи.

### Ручной пользовательский путь

Войти тестовым аккаунтом на HTTPS frontend, открыть Account/Admin по доступной роли и нажать
«Выйти». Проверить pending с «Выходим…» вне меню, после204 — login с точным success notice,
focus heading и отсутствие личных данных по Back/Forward/hash. Повторить с недействительной
сессией:401 даёт нейтральное сообщение. Proxy/API failure сохраняет только актуальный экран,
показывает persistent error и manual retry. Другую вкладку проверить next protected401/reload.

## 5. Cleanup and evidence

После test DB suites, cwd произвольный:

```bash
docker stop animemap-logout-test-db
```

--rm/tmpfs удаляют только созданную выше disposable БД; существующие Compose volumes
не затрагиваются этим cleanup. Остановку full-stack выполнять штатно без удаления рабочих данных.
В отчёте будущей реализации сохранить команды, версии, результаты по всем27 C и ограничения:
mocked UI, real proxy HTTPS и PostgreSQL — разные доказательства. Raw tokens/cookies/keys
не включать в прикладные логи или публикуемые отчёты. Наличие plan не является таким отчётом.
