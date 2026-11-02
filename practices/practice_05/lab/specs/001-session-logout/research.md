# Phase 0 Research: Session Logout

**Date**: 2026-11-02 · **Status**: завершено для планирования.
Исследованы исходники, lockfiles, установленный backend framework и существующие тесты.
Приложения, тесты, установка зависимостей и сборки не запускались.
Все пути ниже относительно `practices/practice_05/lab/`; номера строк — снимок исследования.

Нормативные основания: [CONTRACT](../../docs/sdd/logout/CONTRACT.md),
[UI V2](../../docs/sdd/logout/UI_SPEC_V2.md),
[Backend V2](../../docs/sdd/logout/BACKEND_SPEC_V2.md),
[spec](spec.md), [Constitution](../../.specify/memory/constitution.md).
Начальный Constitution Check пройден: решения сохраняют слои, DI, существующую фабрику,
согласованный контракт и соответствующие слоям проверки. Повторная проверка — в plan.md.

## R-01. Существующая предметная модель и репозитории

**Evidence**:

- `backend/app/domain/entities/session.py:14–51`: frozen/slotted/keyword-only SessionEntity,
  `ensure_usable()` и immutable `use()`, но нет close; хранится только secret_hash.
- `backend/app/domain/repositories/{session,user}.py:9–37`: уже есть
  `get_by_id(..., for_update=True)`; SessionRepository имеет update.
- `backend/app/infrastructure/database/repositories/session.py:23–49,67–80`:
  чтение с `populate_existing=True`, опциональный FOR UPDATE, immutable-field guards,
  update и flush. `.../repositories/user.py:28–76,97–122` использует аналогичные locks/refresh.
- `backend/app/infrastructure/database/models/session.py:20–65`: closed_at уже существует,
  timestamps timezone-aware, constraint closed_at >= last_used_at, owner delete CASCADE.

**Decision**: добавить только доменную команду close и прикладной сценарий; использовать
существующие интерфейсы/адаптеры. Схема и миграции не меняются.

**Rationale**: CONTRACT §3, C-13 требуют сохранить историю и изменить только closed_at.
`SELECT FOR UPDATE` без refresh недостаточен при уже загруженной ORM-записи;
нужный `populate_existing=True` уже реализован, его необходимо сохранить и проверить.

**Alternatives considered**: delete записи нарушает историю; SQL в UseCase нарушает слои;
новый репозиторий/Unit of Work/миграция не дают требуемой дополнительной возможности.

## R-02. Отдельный LogoutUseCase и повторная проверка

**Evidence**:

- `backend/app/application/usecases/auth.py:39–70`: offloaded JWT decode, verify,
  locks user→session, проверка активности, `use()`, явный auth commit, UserDTO.
- `.../usecases/login.py:41–95`: проверка секрета до owner lock, создание hash-only сессии.
- `backend/app/infrastructure/security/jwt.py:37–81`: EdDSA/Ed25519, точные claims
  jti/secret/iat, UUIDv4, строковый secret, integer iat, invalid_token.
- `.../security/secret.py:20–63`: Argon2id hash/verify через to_thread;
  несовпадение → invalid_secret, повреждённый hash → DataFormatException.

**Decision**: LogoutUseCase(BaseUseCase).logout(token) получает UserRepository,
SessionRepository, JwtProviderPort, SecretManagerPort через конструктор.
После preliminary read и verify — user lock, refreshed session lock, повторная проверка
владения/проверенного hash/закрытия/срока по свежему aware UTC, close, update.
is_active не является отказом. UseCase не вызывает обычный Auth, use или commit.

**Rationale**: существующий Auth продлевает срок и не подходит неактивному владельцу.
Копирование Auth без дополнительной сверки owner/hash тоже недостаточно (CONTRACT §3).
При нарушении сверки — отказ через существующие общие ошибки, без нового публичного
error-кода и без успеха на основании старого verify. Нет дополнительной гарантии порядка
нескольких credential-дефектов сверх CONTRACT §4.

**Alternatives considered**: AuthUseCaseDI, общий auth middleware, проверка роли администратора,
выдача UserDTO или новая JWT-схема противоречат ADR-07/11 и baseline.

## R-03. Доказательство границы commit → HTTP

**Evidence приложения**:

- `backend/app/infrastructure/database/session.py:35–96`: expire_on_commit=False,
  autoflush=False; фабрика yield→commit, при исключениях rollback/перевод в доменные ошибки.
- `backend/app/presentation/api/di/clients/postgres.py:10–20`: function-scope yield dependency.
  `di/repositories/{user,session}.py:15–22` используют одну кэшированную PostgresSessionDI.
- `di/clients/auth_postgres.py:13–33`: отдельная AuthPostgresSessionDI/AuthCommitDI;
  это утверждённое исключение для продления, а не механизм Logout.
- `backend/tests/api/test_repository_di.py:31–91`: есть проверка завершения dependency
  и замены подготовленного успеха ошибкой finalization, но нет полной Logout-cookie проверки.

**Evidence версий и установленного framework**:

- `backend/pyproject.toml:6,17–33`, `backend/uv.lock`: Python >=3.14,
  FastAPI 0.162.0, Starlette 1.10.0, SQLAlchemy 2.1.6; локальная .venv — Python 3.14.7.
- В `backend/.venv/lib/python3.14/site-packages/fastapi/dependencies/utils.py:717–729`
  function-scope генератор регистрируется на function exit stack.
- В установленном `fastapi/routing.py:145–166` результат handler сначала создаётся внутри
  function stack; выход из stack предшествует `await response(scope, receive, send)`.
- В `starlette/responses.py:168–172` только вызов Response отправляет http.response.start.
- `starlette/_exception_handler.py:31–63`: исключение до response start может быть
  обработано mapper с отправкой другого ответа.

**Decision**: сохранить фабрику и function-scope DI. Handler может **создать** Response(204)
с cookie до commit; он не должен **отправлять** его до выхода dependency. Успешный commit
завершает stack, после чего Response отправляется. Ошибка commit прерывает этот путь:
подготовленный Response отбрасывается, mapper создаёт ошибку без session Set-Cookie.

**Rationale**: это фактический механизм текущей версии, а не предположение, что любой yield
в любом FastAPI выполняет commit до ответа. Фиксируем его ASGI-тестом с gated commit
и перехватом send; пересмотр зависимости/версии требует повторения этого regression gate.
Не вводим streaming response/background commit для Logout.

**Alternatives considered**: request-scope finalizer может быть поздним;
commit в репозитории нарушает архитектуру; callback auth commit здесь не требуется;
отдельный transaction middleware или переписывание SessionController избыточны.

## R-04. Фактические ошибки, cookie и безопасное логирование

**Evidence**:

- `backend/app/presentation/setup_exceptions.py:22–76` обрабатывает доменные ошибки
  и validation, но не добавляет Logout no-store/cookie и не нормализует routing/неожиданный 500.
- `backend/run.py:18–35`: mapper/router подключены; своих middleware нет.
- `.../routes/auth/login.py:35–44`: host-only cookie Path=/, Secure, HttpOnly, SameSite=Lax.
- Установленный `starlette/responses.py:137–157`: delete_cookie по умолчанию имеет
  secure=False/httponly=False; эти атрибуты необходимо задавать явно.
- FastAPI middleware stack включает внешний ServerErrorMiddleware; обычный внутренний
  postprocessing middleware не гарантирует обработку созданного им неожиданного 500.
- `SessionController:78–95` пишет «rolled back» для DBAPI errors и logger.exception
  для неожиданных ошибок. Формулировка не доказывает rollback при потере commit acknowledgement.

**Decision**: общий Presentation helper для политики фактического Logout-ответа вызывается
из success handler и exception handlers. Logout-контекст credential-проверки отмечается
после CSRF/формы и до cookie; только AuthenticationException этого контекста удаляет cookie
на 401. Расширить текущую настройку HTTPException/неожиданных ошибок без изменения baseline
других ручек. Для HEAD подавить тело; сохранить Allow у 405. На storage/commit error
не переносить headers подготовленного успеха.

**Decision logging**: в существующем session boundary заменить небезопасное application
логирование безопасной категорией/стадией/известностью результата без raw exceptions/SQL,
credential или утверждения rollback при unknown commit. Существующий SQLSTATE/retryable
маппинг сохраняется; retry не добавляется.

**Alternatives considered**: headers только на injected Response теряются при mapper;
удаление на любом 401 смешивает credential и инфраструктуру; только user middleware
не покрывает внешний 500. Новый сервис логов/аудита для Logout не нужен.

## R-05. Состояние React и транспорт Logout

**Evidence**:

- `frontend/src/App.tsx:10–75`: account/loading/error, простой onExpired без generation;
  account-based conditional render уже скрывает защищённый subtree.
- `components/Header.tsx:6–76`: dropdown/focus ref/Escape; Logout — заглушка с notice.
- `pages/AuthPage.tsx:9–45,70–88`: local busy; login + me; нет общей auth-operation ownership.
- `pages/AccountPage.tsx:5–20`, `pages/AdminPage.tsx:7–38,55–109`: local effects,
  debounce/abort, поиск/пагинация/карточка; onExpired не имеет поколения.
- `api/client.ts:26–64`: принимает любой response.ok, JSON failure→{}, generic/search-specific
  сообщения; непосредственное переиспользование для Logout даст ложный успех/неверный текст.

**Decision**: маленький App-owned hook/coordinator с синхронным ref-захватом auth slot,
react state для отображения, отдельными generation, operation ID и logout attempt ID.
Login держит slot до завершения me. Protected requests несут generation/request identity;
все callbacks, включая error/401/finally, проверяют владельца. Account clear/remount subtree
удаляет локальные данные; pending запрещает новые запросы даже после hash navigation.
Старый finalizer освобождает только собственную операцию. Logout state живёт выше Header.

**Decision transport**: отдельный logout helper сохраняет статус, не отправляет JSON body,
использует same-origin/no-store и явный CSRF; принимает только 204, независимо от error JSON
обрабатывает 401, имеет конечное 20-секундное ожидание включая чтение ответа.
Никаких JS-cookie/JWT операций или persistence. Точные тексты — spec/CONTRACT §6.1.

**Alternatives considered**: одного busy state недостаточно до React render;
generation нельзя использовать как владельца auth slot; abort не доказывает отмену сервера;
Redux/router migration/query library или BroadcastChannel не нужны.

## R-06. Proxy, Origin и strict input

**Evidence**:

- `frontend/server/proxy.mjs:1–43`: allowlist без Logout, fallback404, Origin сравнивает
  только host, общий 16 KiB buffer возвращает413.
- `proxy.mjs:44–92`: CSRF не forwarded; manual redirect и 15-секундный AbortSignal уже есть;
  регистрация303→201, buffer response до отправки, ошибки только с message; Allow не передаётся.
- `server/app.mjs:16–38`, `server/index.mjs:6–20`: API_ORIGIN, HTTP/HTTPS startup,
  TLS_CERT/TLS_KEY; requestTimeout30s не является upstream15s или DB deadline.

**Decision**: распознавать Logout до generic allowlist/buffer; метод→Origin→CSRF→форма.
Для Logout локально отклонять invalid CSRF и любой query/первый байт body без накопления
всего тела; не превращать непустой вход в пустой upstream. Допустимый нулевой вход передавать
с исходными Cookie/CSRF; backend независимо повторяет проверки. Duplicate ambiguity
проверять по исходным заголовкам, не выбирать удобное значение из объединённого списка.
Этот route-specific путь исключает случайный413 общего буфера при обязательном400.

**Decision origin**: добавить доверенную настройку PUBLIC_ORIGIN, передаваемую из index
в createApp/proxy и явно задаваемую для runtime и тестов; нормализовать URL origin
в scheme/hostname/effective-port. Это техническая настройка разрешённой контрактом
топологии, не дополнительная клиентская проверка. Не доверять Host/X-Forwarded-Proto
для определения публичного origin. Для присутствующего malformed/null Origin —403;
отсутствие не отменяет CSRF. Сохранить регистрационную семантику.

**Decision response**: сохранить manual redirect, полный buffer response внутри15s,
передавать status/Set-Cookie/Cache-Control/Allow; no body для204/HEAD.
Abort signal state учитывается и при чтении body: timeout→504, иная upstream failure→502;
redirect→502 без его cookie. Local errors получают envelope/no-store, но не Set-Cookie.

**Alternatives considered**: сравнение одного host, произвольный forwarded proto,
синтез CSRF, silently dropped body, generic413 и retry противоречат CONTRACT §2/7.

## R-07. Проверки, tooling и воспроизводимость

**Evidence**:

- Backend: `tests/unit/domain/test_session_use.py`, `unit/application/test_auth.py`,
  `test_security_threads.py`, `unit/test_security.py`, `api/test_repository_di.py`,
  `integration/database/test_auth_flow.py` и `test_repositories.py` дают повторно используемые
  fixtures/паттерны, но Logout/race coverage отсутствует.
- Integration пропускается без TEST_DATABASE_URL; нужны мигрированная БД и committed fixtures
  для нескольких соединений. Auth-flow fixture подменяет фабрику на session.begin(),
  поэтому не доказывает production SessionController error/commit boundary.
- `frontend/tests/server.test.mjs:7–125`: node:test с реальным HTTP server и stub upstream.
  `tests/browser/app.spec.ts:12–133`: семь UI tests с API interception и Logout placeholder.
- `frontend/package.json`/lock: React19.3.1, TS5.9.3, Vite7.3.7, Playwright1.64.1.
  Vite lock требует Node22.12+ в выбранной Node22 линии. Unit runner/Testing Library отсутствуют.
- Playwright config использует HTTP3100; API interception обходит proxy.
  Native TLS поддержан, но готового HTTPS acceptance config/Compose override нет.

**Decision**: сохранить pytest/node:test/Playwright. Для frontend unit/component добавить
Vitest 3.2.x, jsdom26.x, Testing Library React16.x и user-event14.x
как dev-only зависимости; точные patch версии закрепить lockfile при будущей установке
и подтвердить npm peer/Node compatibility. Новых runtime библиотек не требуется.
Отдельный HTTPS Playwright config и тестовые сертификаты окружения, без ключей в репозитории.

Проверен [npm metadata Vitest3.2.4](https://registry.npmjs.org/vitest/3.2.4):
dependency Vite `^5.0.0 || ^6.0.0 || ^7.0.0-0`, Node `>=22` поддержан,
jsdom26.1.0 используется собственным dev окружением пакета. Это обоснование совместимой
линии, не установка зависимостей или замена project lockfile в задаче планирования.

**Decision races**: реальные PostgreSQL sessions/соединения, committed setup, events/barriers
на read/verify/lock/commit, ограниченные ожидания и observer transaction. Никаких sleep-only
доказательств или mock-repository замен для locks/commit. Сохранить сильную ORM-reference
в refresh regression. UI/proxy timeouts — управляемые часы с реальными HTTP-проверками.

**Alternatives considered**: SQLite, только AsyncMock, только browser route interception
не доказывают требуемые уровни; новый frontend runtime/framework не нужен.

## Итог Phase 0

Существенных неразрешённых вопросов или конфликтов с ADR-01–ADR-11 нет.
Численные SLA сверх15/20s, межвкладочный lock и гарантированная отмена сервера не вводятся.
Все исследовательские вопросы для Phase1 разрешены; это не утверждение успешного выполнения
будущих тестов. Проверяемые решения и критерии — [test-strategy.md](test-strategy.md).
