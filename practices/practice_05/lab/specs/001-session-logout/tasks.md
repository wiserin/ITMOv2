---
description: "Обязательные задачи реализации и проверки AnimeMap Session Logout"
---

# Tasks: AnimeMap Session Logout

**Input**: `specs/001-session-logout/spec.md`, `plan.md`, `research.md`, `data-model.md`, `test-strategy.md`, `contracts/logout-http.md`, `contracts/logout-ui.md`, `quickstart.md`; `.specify/memory/constitution.md` v1.0.0.

**Authority**: `docs/sdd/logout/CONTRACT.md` v1.0 и утверждённые ADR-01–ADR-11 из `docs/sdd/logout/REVIEW.md` §6–10. Исторические предложения §1–5 не применяются.

**Status**: план будущей реализации после отдельного разрешения. Создание этого файла не означает выполнения задач или прохождения тестов.

**Tests**: обязательны во всех историях. Семь уровней: D — domain unit, A — application unit, H — API, P — реальный PostgreSQL, F — frontend unit/component, X — реальный Node HTTP proxy, B — browser. Моки F/H/A не заменяют P/X/HTTPS B. Написать тесты перед соответствующим поведением, подтвердить релевантное падение, затем довести до PASS; если часть поведения уже реализована предыдущей задачей, сохранить тест как regression и подтвердить PASS.

## Format и пути

Каждая исполняемая задача имеет вид `- [ ] Tnnn [P?] [USn?] действие, пути, результат`. Все пути относительно `practices/practice_05/lab/`. Новые файлы названы явно; существующие файлы переиспользуются по `plan.md`. `Зависит` перечисляет дополнительные непосредственные prerequisites; транзитивные зависимости и барьеры фаз обязательны. Одна задача может затрагивать несколько тесно связанных файлов.

`[P]` означает безопасный запуск **только в указанной ниже волне**, после её prerequisites, на разных файлах. Это не разрешение одновременно редактировать один файл в разных фазах. Без `[P]` используется последовательный порядок ID. Задачи проверки также обязательны; их результат фиксируется в будущем `specs/001-session-logout/validation.md`, без credential/ключей/сырого SQL.

## Архитектурные инварианты для всех задач

- Domain/Application не зависят от HTTP/ORM; порты и интерфейсы Repository остаются в Domain. `LogoutUseCase(BaseUseCase).logout(token)` получает ровно четыре существующие зависимости через constructor DI. Не создавать DTO/Request/JSON Response для пустого запроса/204.
- Существующие EdDSA/Ed25519 JWT `jti/secret/iat`, UUIDv4 и Argon2id сохраняются; decode/verify не блокируют event loop. Только `secret_hash` хранится в сущности/БД. Logout не использует обычный Auth, `use()`, отдельный Auth commit или проверку роли/активности как запрет собственного close.
- Одна cached `PostgresSessionDI(scope="function")`, locks user→session, refreshed read с `populate_existing=True`, повторная сверка owner/hash/closed/expiry по свежему UTC. Репозитории flush, фабрика commit/rollback. Успех и его cookie отправляются только после подтверждённого commit.
- Новых таблиц, миграций, индексов, Redis-структур, refresh/blacklist и runtime-framework нет. Существующее исключение Auth с отдельным commit и renewal даже при бизнес-403 сохраняется.
- Только Browser→same-origin Node proxy→FastAPI; доверенный `PUBLIC_ORIGIN`, не клиентский `X-Forwarded-Proto`. JWT не читается/не хранится JS, не передаётся в Authorization/JSON/storage; JS не удаляет HttpOnly cookie.
- Auth generation отличается от operation ownership. Clear auth не освобождает pending Logout slot. Нет autoqueue/autoretry/broadcast/polling/intertab lock. Поздний Set-Cookie может удалить новую cookie, но не закрывает новую независимую серверную запись. Abort/timeout/502/504 не доказывают rollback; 15/20 секунд не являются deadline БД.
- Python, включая тесты: 70 символов, Ruff E501 без обходов, hanging indent и naming из `agent-rules/naming.md` и `agent-rules/codestyle.md`. Контракты, ADR и исходные спецификации при реализации не переписываются.

## Phase 1: Setup — общая проверочная инфраструктура

**Цель**: подготовить воспроизводимые D/A/H/P/F/X/B проверки без изменения runtime-архитектуры. T001 открывает параллельную волну T002–T004; Phase 2 начинается после всей Phase 1.

- [X] T001 Сверить `agent-rules/AGENTS.md`, `agent-rules/naming.md`, `agent-rules/codestyle.md`, `.specify/memory/constitution.md`, `docs/sdd/logout/REVIEW.md` §6–10 и входные артефакты; проверить Python 3.14+, Node 22.12+, existing Alembic head и окружение из `specs/001-session-logout/quickstart.md`, зафиксировать версии/команды/gates в `specs/001-session-logout/validation.md`; результат: baseline и ограничения ADR-01–ADR-11 явно подтверждены, новые противоречия вынесены на согласование до реализации.
- [X] T002 [P] Добавить dev-only Vitest 3.2.x, jsdom 26.x, Testing Library React 16.x/user-event 14.x в `frontend/package.json` и `frontend/package-lock.json`, создать `frontend/vitest.config.ts` и `frontend/tests/unit/setup.ts`, script `test:unit`; результат: совместимые patch закреплены lockfile, доступны jsdom, cleanup, deferred promises/fake clocks, существующие `npm test` и Playwright scripts сохранены. Зависит: T001.
- [X] T003 [P] Создать `backend/tests/integration/database/logout_support.py` с test app production router/handlers, настоящим `SessionController`, test security providers, committed users/sessions, отдельными connections/observer и stage gates/fault wrappers; результат: existing миграции на PostgreSQL 18, один `asyncio.run(...)` на конкурентный сценарий, bounded waits и finally-cleanup/dispose, bootstrap root не меняется; отсутствие `TEST_DATABASE_URL` явно не считается PASS. Зависит: T001.
- [X] T004 [P] Создать `frontend/playwright.https.config.ts`, `frontend/tests/browser/support/logoutHttps.mjs` и `frontend/tests/browser/support/logoutFixtures.ts`, исключить HTTPS suite из обычного HTTP project в `frontend/playwright.config.ts`; результат: режимы `LOGOUT_E2E_MODE=fixture|api`, настоящий HTTPS Node proxy, управляемый HTTP upstream без `page.route` в HTTPS, TLS_CERT/TLS_KEY из окружения без ключей в Git, API-mode создаёт/удаляет изолированные аккаунты через baseline/test harness, а не новые production endpoints; конфигурация совместима с будущим PUBLIC_ORIGIN. Зависит: T001.

**Checkpoint**: все три harness готовы; исходные контракты остаются входом, не генерируются заново.

## Phase 2: Foundational — блокирующие архитектурные предпосылки

**Цель**: минимальные общие механизмы ownership, публичной границы и безопасной finalization. Все задачи этой фазы — prerequisite любой US.

- [X] T005 Написать pure-state tests в `frontend/tests/unit/sessionState.test.ts` для локальных моделей из `data-model.md`: `AuthContext` — «Generation меняется при clear/replacement; старые события не применяются»; `AuthOperation` — «Синхронный ref-owned slot; максимум один; clear auth не снимает slot»; `LogoutAttempt` — «Deadline20s; завершённый ID не оживает; release только своего slot»; результат: проверены acquire/clear/replace/terminalize/release, login/logout kind и независимость поколения от владельца операции. Покрывает C-19, C-21, C-22.
- [X] T006 Реализовать типизированные memory-only модели и pure transitions в `frontend/src/auth/sessionState.ts`; сохранить поля generation/account|null, unique operationId/kind/busy, attemptId/operationId/capturedGeneration/startedAt/deadline/terminal, LogoutUI «idle/pending/failed; safe reason», LoginOutcome «success/session-invalid notice», ProtectedRequestContext «generation, request identity»; результат: T005 PASS, stale no-op, terminalize перед owner-only release, без JWT/persistence. Зависит: T005.
- [X] T007 Написать базовые HTTP contract tests публичного Logout в `frontend/tests/server.test.mjs`: метод→Origin→CSRF→форма, duplicate raw CSRF, отсутствие синтеза заголовка, body/query до cookie, >16 KiB даёт 400, HEAD без тела, OPTIONS без auth/CORS, forwarding Cookie/CSRF и response status/Set-Cookie/no-store/Allow; результат: реальные Node server/upstream и счётчики вызовов, failures не подменяются generic 404/413/201. Покрывает C-06–C-10, C-17.
- [X] T008 Реализовать базовую route-specific Logout границу в `frontend/server/proxy.mjs`, передать trusted `PUBLIC_ORIGIN` через `frontend/server/app.mjs` и `frontend/server/index.mjs`; результат: точный `/v1/auth/logout` обрабатывается до allowlist/buffer, методы 405/Allow: POST, POST Origin по scheme/hostname/effective port, CSRF по raw headers, query/первый body byte отклоняются без накопления payload, валидный нулевой запрос передаёт исходные Cookie/CSRF, local ошибки имеют JSON envelope/no-store и не меняют cookie; T007 PASS, baseline registration 303→201 сохранён. Зависит: T007.
- [X] T009 Расширить `backend/tests/api/test_repository_di.py` проверками одной cached function-scope PostgreSQL dependency для двух репозиториев и отсутствия `http.response.start` до finalization; добавить regression безопасности session-boundary логов в `backend/tests/integration/database/test_logout_commit.py` на harness T003; результат: factory/DI regression ловит поздний commit, raw SQL/exception/secret и ложное «rolled back» при неизвестном acknowledgement. Покрывает C-16, C-17.
- [X] T010 Исправить только безопасное failure logging в `backend/app/infrastructure/database/session.py`: категория/стадия/известность исхода вместо raw exception/SQL и без обещания rollback при unknown commit; результат: T009 PASS, существующий domain error mapping с SQLSTATE/retryable, ownership commit/rollback, cached function-scope DI и baseline Auth exception сохранены; `backend/app/presentation/api/di/clients/postgres.py` переиспользуется без смены scope. Зависит: T009.

**Checkpoint**: T001–T010 завершены. Это общая foundation, а не доказательство Logout commit/cookie/races: отдельные интеграционные gates находятся в US1 и US5.

## Phase 3: US1 — Подтверждённый выход из текущей сессии (P1), MVP-срез

**Цель**: user/moderator/admin и неактивный владелец закрывают только предъявленную пригодную сессию; UI очищается после подтверждения.

**Independent Test**: для каждой роли POST→204 после commit, body=0/no-store/no Location, другой credential работает; старый JWT на `/account/me`→401, inactive→204 без активации/renewal, реактивация не оживляет JWT. В UI login с «Вы вышли из аккаунта.» без дополнительного me; HTTPS cookie действительно удалена.

### Обязательные тесты — независимая волна T011–T018

- [ ] T011 [P] [US1] Написать D tests в `backend/tests/unit/domain/test_session_close.py`: before/equal/after last_used_at, default aware UTC, повтор close с другим now, исходный frozen объект и остальные поля неизменны; отдельно ensure_usable при now==expires_at/now>expires_at и closed, без вызова use; процитированные ограничения модели: `closed_at` — «nullable timezone-aware timestamp», «Для нового close max(now,last_used_at); при повторе исходное значение»; результат: C-13 и domain eligibility C-05 проверены независимо от HTTP.
- [ ] T012 [P] [US1] Написать A tests в `backend/tests/unit/application/test_logout.py`: четыре constructor dependencies, decode через to_thread и async verify до locks, preliminary ensure_usable, user→refreshed session, повторная сверка owner/hash/expiry/closed, update получает результат close; результат: все роли/inactive допустимы, нет Auth/authenticate/use/explicit commit/UserDTO/global config, verify offload не блокирует event loop. Покрывает C-01, C-02, C-13–C-15.
- [ ] T013 [P] [US1] Написать H contract tests в `backend/tests/api/test_logout.py` с production router/handlers и HTTPS TestClient: POST body=0 с/без Content-Type, 204 ноль байт/no Location/no-store, cookie deletion, CSRF/input order, method 405/Allow/HEAD/OPTIONS, OpenAPI auth_logout/tag auth/cookie security/required CSRF/no requestBody/no content204; результат: assertions наблюдаемого `contracts/logout-http.md`, не только handler return. Покрывает C-01, C-06–C-08, C-11, C-17.
- [ ] T014 [P] [US1] Написать P happy-path tests в `backend/tests/integration/database/test_logout.py` на T003: все три роли, inactive owner, reactivation, copied old JWT→account/me401, независимая сессия пригодна; observer сравнивает id/user_id/secret_hash/created_at/last_used_at/expires_at и retained запись; результат: только closed_at изменён, close сохранён настоящей factory. Покрывает C-01, C-02, C-12, C-13.
- [ ] T015 [P] [US1] Написать transport contract tests в `frontend/tests/unit/logoutTransport.test.ts`: относительный POST `/v1/auth/logout`, без body/query/Authorization, единственный `X-AnimeMap-Logout: 1`, `credentials: 'same-origin'`, `cache: 'no-store'`, closed только на 204; результат: transport не читает JWT/cookie/storage и не меняет маршрут/account. Покрывает C-01, C-18, C-27.
- [ ] T016 [P] [US1] Написать coordinator tests в `frontend/tests/unit/useAuthSession.test.tsx` с deferred transport: capture generation/attempt/operation, синхронное acquire до render, один pending request, current204 clear+generation++, owner-only release; результат: результат не применяется до ответа, menu/hash не владеют попыткой. Покрывает C-19, C-20, C-22.
- [ ] T017 [P] [US1] Написать App/Header/AuthPage integration tests в `frontend/tests/unit/logoutUI.test.tsx`: запуск с главной/аккаунта/Admin, «Выходим…» вне меню, после204 одновременная очистка account/search/page/card/errors, скрытие Header/protected subtree и `#/login` с точным итогом без me; результат: отсутствует кадр личных данных на login и JWT в JS/storage. Покрывает C-20, C-27.
- [ ] T018 [P] [US1] Создать отдельные HTTPS integration tests cookie в `frontend/tests/browser/logout.https.spec.ts` на T004: реальные Node proxy/upstream Set-Cookie и browser jar, login scope и удаление на204/каждом Logout401, отсутствие session mutation header на400/403/405/500/502/503/504; результат: проверены пустое значение, host-only без Domain, Path=/, Max-Age=0, прошлый Expires, Secure/HttpOnly/SameSite=Lax, отсутствие чтения cookie в app JS, cookie меняет backend-команда, не proxy/JS. Покрывает C-10, C-11, C-27; fixture mode не выдаётся за доказательство PostgreSQL.

### Реализация и интеграция

- [ ] T019 [US1] Добавить immutable `close(now=None)` через dataclasses.replace в `backend/app/domain/entities/session.py`; сохранить `frozen`, `slots=True`, `kw_only=True` и ограничения `data-model.md` дословно: `id` «UUIDv4», «Не меняется; определяется jti предъявленного JWT»; `user_id` «UUID владельца», «Не меняется; владелец должен существовать и совпадать при refreshed read»; `secret_hash` «Argon2id hash», «Не меняется; сверка актуального hash с проверенным обязательна»; `created_at` «timezone-aware timestamp», «Не меняется»; `last_used_at` «timezone-aware timestamp», «Не меняется этим Logout, сохраняется более свежее конкурентное продление»; `expires_at` «timezone-aware timestamp», «Не меняется этим Logout; пригодность now < expires_at»; `closed_at` «nullable timezone-aware timestamp», «Для нового close max(now,last_used_at); при повторе исходное значение»; результат: меняется только closed_at=max(now,last_used_at), повтор сохраняет исходное время, default now aware UTC, eligibility/owner/hash checks остаются обязанностью сценария, T011 PASS. Зависит: T011.
- [ ] T020 [US1] Создать `backend/app/application/usecases/logout.py` с `LogoutUseCase(BaseUseCase).logout(token)` и UserRepository/SessionRepository/JwtProviderPort/SecretManagerPort в конструкторе; результат: decode offload→pre-read/ensure_usable→verify→user lock→refreshed session lock→owner/hash/closed/expiry recheck со свежим UTC→close/update, is_active игнорируется только для собственного Logout, поля/схема/JWT неизменны, T012 PASS. Использовать существующие `backend/app/infrastructure/database/repositories/user.py` и `backend/app/infrastructure/database/repositories/session.py` с populate_existing/FOR UPDATE, без SQL в UseCase. Зависит: T012, T019.
- [ ] T021 [US1] Создать `backend/app/presentation/api/di/logout.py` с `get_logout_usecase` и `LogoutUseCaseDI`, используя существующие repo/port алиасы; результат: DI только собирает экземпляр, оба репозитория получают одну ordinary cached function-scope PostgresSessionDI, без AuthUseCaseDI/AuthPostgresSessionDI/AuthCommitDI или business I/O в provider. Зависит: T020.
- [ ] T022 [US1] Создать `backend/app/presentation/logout_response.py` с политикой фактического Logout response и credential-check контекста: no-store всегда, на204/Logout AuthenticationException401 deletion только session_token с полным host-only scope/атрибутами из T018, остальные ошибки без session Set-Cookie, HEAD без body; результат: один helper для success и mapper, без HTTP-политики в Domain/Application. Зависит: T013.
- [ ] T023 [US1] Создать `backend/app/presentation/api/routes/auth/logout.py`, зарегистрировать в `backend/app/presentation/api/routes/auth/__init__.py`; результат: raw headers CSRF→raw query/body→credential context/cookie→именованный logout, нет JSON parser/422/ordinary Auth, auth_logout/tag auth/OpenAPI как T013, создаётся пустой 204 без отправки до function finalization. Зависит: T021, T022.
- [ ] T024 [US1] Подключить helper T022 в `backend/app/presentation/setup_exceptions.py` для реальных domain/validation/HTTPException405/unexpected500 ответов Logout, включая внешний ServerErrorMiddleware handler; результат: error/message:string и details:object/no-store на фактических ошибках, Allow сохранён, prepared success cookies не копируются при finalization failure, не-Logout baseline mapper сохранён; T013 и backend DI regression PASS. Зависит: T023.
- [ ] T025 [US1] Создать `frontend/src/api/logout.ts` с типизированным closed204/invalid401/safe-failure результатом и Abort/deadline context; результат: запрос точно как T015, только204 success, достоверный HTTP status не зависит от optional JSON, JWT/account/hash не принадлежат transport, автоповторов нет, T015 PASS. Зависит: T015.
- [ ] T026 [US1] Создать App-owned `frontend/src/auth/useAuthSession.ts` поверх T006/T025: identity refs обновляются синхронно, React state отражает slot, live attempt и generation проверяются отдельно от release owner; результат: start→pending, current204→clear/generation++/signed-out, terminalize→release только своего slot, T016 PASS. Зависит: T016, T025.
- [ ] T027 [US1] Интегрировать coordinator в `frontend/src/App.tsx`: account-based render boundary и generation-keyed protected subtree, централизованная очистка search/pagination/card/errors через unmount, переход login без дополнительного me после204; результат: state не принадлежит Header/page, protected данные не видны ни в одном login render, happy-path T017 PASS для App. Зависит: T026.
- [ ] T028 [US1] Заменить Logout-заглушку в `frontend/src/components/Header.tsx` на callback/busy/status coordinator, убрать «Скоро», закрыть dropdown при старте и вернуть focus на фокусируемый guarded trigger; результат: доступный запуск на всех защищённых страницах, «Выходим…»/role=status вне dropdown и отсутствие действий pending, без локальной auth-попытки. Зависит: T027.
- [ ] T029 [US1] Подключить shared auth busy/login action/outcome/dismiss к `frontend/src/pages/AuthPage.tsx` и `frontend/src/App.tsx`; результат: login держит один slot через `/account/me`, guarded submit, после Logout заголовок получает focus, success «Вы вышли из аккаунта.» с role=status закрывается вручную/сбрасывается новым login; T017 PASS. Зависит: T028.
- [ ] T030 [US1] Прогнать D/A/H/P/F и HTTPS fixture+api happy path для `backend/tests/integration/database/test_logout.py` и `frontend/tests/browser/logout.https.spec.ts`, добавить api-mode assertions copied JWT rejection/independent session и заменить placeholder ожидание в `frontend/tests/browser/app.spec.ts`; результат: T011–T018 PASS на соответствующих уровнях, C-01/C-02/C-11/C-12/C-13/C-20 имеют evidence в `specs/001-session-logout/validation.md`, без объявлений, что моки доказывают commit/HTTPS. Зависит: T014, T018, T024, T029.

**Checkpoint**: независимо проверяемый основной путь US1. Это MVP-срез для демонстрации; полный выпуск требует все P1, US6 и final gates.

## Phase 4: US2 — Завершение локального входа при недействительной сессии (P1)

**Цель**: различать отказ credential и подтверждённый close; каждый Logout401 завершает локальную авторизацию с нейтральным итогом.

**Independent Test**: по одному дефекту cookie/JWT/secret/session/owner, closed и expired; соответствующий401/deletion без записи close/renewal. Malformed JSON401 всё равно очищает UI, без повторного POST.

### Обязательные тесты

- [ ] T031 [P] [US2] Расширить `backend/tests/unit/application/test_logout.py` проверками token/state orchestration и отдельно сохранить полную HTTP-матрицу в `backend/tests/api/test_logout.py`: missing/empty cookie/Bearer-only, подпись/фиксированный алгоритм/claims jti-secret-iat/UUIDv4/типы, invalid secret, missing session/owner, closed, expired; result reasons строго missing_session_cookie/invalid_token/invalid_secret/session_not_found/session_closed/session_expired, hash corruption остаётся400, не401; результат: bad credential не вызывает close/update, каждый фактический401 удаляет cookie; cookie/Bearer проверяются на API-границе, а unit/API не заменяют PostgreSQL evidence T032. Покрывает C-03–C-05, C-17.
- [ ] T032 [P] [US2] Добавить параметризованные HTTP+PostgreSQL cases в `backend/tests/integration/database/test_logout.py` на harness T003: реальные SessionController, репозитории и существующие JWT EdDSA/Ed25519/Argon2id-адаптеры из `backend/app/infrastructure/security/jwt.py` и `backend/app/infrastructure/security/secret.py` с тестовым ключом, без моков repositories/security/commit. Для C-03 проверить одиночные JWT-дефекты подписи/алгоритма/claims jti-secret-iat/UUIDv4/типов из T031→401/invalid_token, корректно подписанный JWT с неверным secret существующей открытой сессии→401/invalid_secret, корректный JWT отсутствующей сессии→401/session_not_found, JWT владельца, удалённого с baseline CASCADE до запроса→401/session_not_found. Независимый observer сравнивает committed snapshots до/после Logout: все поля fixture user/session и независимой контрольной сессии неизменны, closed_at не появляется, last_used_at/expires_at не продлены, отсутствующие строки не создаются; снимок для удалённого owner снимается после fixture delete, CASCADE не считается эффектом Logout, FK не обходятся. На каждом отказе проверить фактический401/reason/no-store и deletion cookie по T018. Сохранить C-04/C-05 cases: closed_at при повторе неизменен, повтор без cookie→missing_session_cookie, now==expires_at/now>expires_at и expiry при controlled verify без close/renewal. Не дублировать missing/empty/Bearer-only матрицу T031 сверх повтора C-04, полную атрибутную cookie-матрицу T018, concurrent owner-delete T059 и expiry lock-wait T058; результат: C-03 имеет реальные security+PG/persisted-state доказательства, C-04/C-05 regression сохранены. Покрывает C-03–C-05.
- [ ] T033 [P] [US2] Расширить `frontend/tests/unit/logoutTransport.test.ts` и `frontend/tests/unit/logoutUI.test.tsx`:401 с JSON/malformed/non-JSON/empty body, актуальная clear и точный нейтральный итог; результат: статус не теряется из-за parse error, нет нового Logout/me или утверждения нового close. Покрывает C-18, C-20.

### Реализация и проверка

- [ ] T034 [US2] Довести отказные ветки в `backend/app/application/usecases/logout.py`: NotFound→AuthenticationException/session_not_found, сохранение существующих JWT/secret/expired/closed reasons и DataFormatException; результат: T031/T032 PASS, не вводится полный приоритет нескольких внутренних credential-дефектов и inactive_user только из is_active=false. Зависит: T031, T032.
- [ ] T035 [US2] Довести cookie extraction/credential context в `backend/app/presentation/api/routes/auth/logout.py` и mapper policy в `backend/app/presentation/setup_exceptions.py`; результат: после CSRF/формы missing/empty/Bearer-only→401/missing_session_cookie с deletion, все Logout401 имеют нужный scope, прочие ошибки не превращаются в401 и не удаляют cookie; API T031 PASS. Зависит: T034.
- [ ] T036 [US2] Довести status-preserving invalid401 обработку в `frontend/src/api/logout.ts`; результат: достоверный401 переживает ошибку optional JSON, transport возвращает invalid без сырых message/details и без повторного запроса, T033 transport PASS. Зависит: T033.
- [ ] T037 [US2] Подключить invalid outcome в `frontend/src/auth/useAuthSession.ts` и `frontend/src/pages/AuthPage.tsx`, прогнать T031–T033 и HTTPS401 cases в `frontend/tests/browser/logout.https.spec.ts`; результат: clear/generation++, unauthenticated, «Сессия недействительна. Войдите снова», без ложного close/autoretry, owned finalization и C-03–C-05/C-18/C-20 подтверждены в `specs/001-session-logout/validation.md`. Зависит: T035, T036.

## Phase 5: US3 — Восстановление после неподтверждённого выхода (P1)

**Цель**: безопасные persistent ошибки, конечное ожидание, явный повтор; потеря ответа не превращается в успех или обещание rollback.

**Independent Test**: неожиданные200/201/202, non-401 errors, network/status0, proxy502/504 и body stalls; UI не объявляет успех, до19999ms нет timeout, на20000ms invalidates ID/releases own slot. Persisted close с потерянным ответом и явный retry401 проверяются отдельно.

### Обязательные тесты

- [ ] T038 [P] [US3] Расширить `frontend/tests/unit/logoutTransport.test.ts`: не2042xx/3xx/400/403/405/500/502/503/504, malformed/non-JSON, fetch/network/status0, deferred body, fake19999/20000ms от dispatch; результат: known status не заменяется parse error, timeout охватывает чтение, early response завершает ожидание раньше20s, no autoretry даже retryable. Покрывает C-18, C-23.
- [ ] T039 [P] [US3] Расширить `frontend/tests/unit/logoutUI.test.tsx` и `frontend/tests/unit/useAuthSession.test.tsx` cases failure/dismiss/retry и protected401-before-failure: экран/account сохраняются только пока auth актуальна, alert не auto-dismiss, dismiss не восстанавливает snapshot, retry создаёт новый ID; результат: точные безопасные тексты из таблицы ниже и owner-only timeout finalization. Покрывает C-18, C-21, C-23, C-24.
- [ ] T040 [P] [US3] Добавить X deadline/failure tests в `frontend/tests/server.test.mjs`: настоящие HTTP upstream stalls до headers и в body, injectable scheduler 14999/15000ms при production default15000, redirects302/303 с Set-Cookie, connection failure; результат: status/cookie не уходят до полного чтения, timeout504/upstream_timeout, другие failures/3xx502/upstream_failure без redirect cookie/follow/повтора, no-store/envelope. Покрывает C-10, C-11, C-17, C-23.
- [ ] T041 [P] [US3] Создать LOSS-1 integration case в `backend/tests/integration/database/test_logout_commit.py` на реальной factory: observer доказывает successful commit, test delivery boundary теряет ответ, повтор сохранённым JWT→401/session_closed с прежним closed_at; результат: commit-loss и unknown commit acknowledgement — разные fault models, серверный close доказан независимо от доставки. Покрывает C-16, C-24.

### Реализация и проверка

- [ ] T042 [US3] Довести failures/deadline в `frontend/src/api/logout.ts`: единый budget20000ms от отправки до чтения, safe reason по статусу, только204 успех, без автоматического повторения и утечек сырого error; результат: T038 PASS, network/status0 отличается от достоверного HTTP, abort не называется rollback. Зависит: T038.
- [ ] T043 [US3] Реализовать failure/timeout/retry/dismiss в `frontend/src/auth/useAuthSession.ts`: invalidate/terminalize ID перед release, failed только при текущей auth, иначе сохранить очищенную unauthenticated, новый retry ID; результат: T039 coordinator PASS и поздний Promise не завершает новую попытку. Зависит: T039, T042.
- [ ] T044 [US3] Подключить persistent role=alert, «Повторить выход» и «Закрыть уведомление» в `frontend/src/App.tsx` и `frontend/src/components/Header.tsx`; результат: явные keyboard-доступные действия без timer-dismiss, точные тексты ошибок, нет текста поиска/сырых details и обещания активности сессии, T039 UI PASS. Зависит: T043.
- [ ] T045 [US3] Довести manual redirect, полное response buffering и deadline scheduler в `frontend/server/proxy.mjs`; результат: production15000ms включает body read, до completion нет success/status/deletion downstream, timeout504 при доступном browser connection, иной upstream сбой/3xx502 без чужой cookie, original headers сохраняются, no retry и baseline registration303→201 не меняется, T040 PASS. Зависит: T040.
- [ ] T046 [US3] Добавить сквозной lost-reply/manual-retry browser case в `frontend/tests/browser/logout.https.spec.ts` и delivery gate в `frontend/tests/browser/support/logoutHttps.mjs`: API-mode commit проверяется независимым observer через test harness, ответ не доставляется, UI не сообщает success, явный retry401 очищает UI; результат: LOSS-1 связан с реальным proxy/API/PostgreSQL, исходное closed_at неизменно, не используется page.route вместо integration. Зависит: T041, T044, T045.
- [ ] T047 [US3] Прогнать T038–T041/T046 и добавить представительский real-time15/20s browser scenario в `frontend/tests/browser/logout.https.spec.ts` с timeout теста >20s: отдельно доставленный proxy504 до UI20s и недоставленный результат с UI20s; результат: ранних timeout/autoretry нет, late result после timeout не даёт success новой попытке, C-18/C-23/C-24 evidence записаны в `specs/001-session-logout/validation.md`. Зависит: T046.

### Нормативные строки для T039/T042/T044

| Reason | Точный текст |
| --- | --- |
| network/status0 | Не удалось подтвердить выход: нет соединения. Попробуйте ещё раз. |
| UI timeout/504 | Не удалось подтвердить выход: сервер не ответил вовремя. Попробуйте ещё раз. |
| 502/503 | Не удалось подтвердить выход: сервис временно недоступен. Попробуйте позже. |
| прочее/неожиданный ответ | Не удалось подтвердить выход. Попробуйте ещё раз. |

## Phase 6: US4 — Защита от повторных действий и устаревших событий (P1)

**Цель**: двусторонняя локальная сериализация login/logout и generation/request/attempt guards всех событий, включая finally/таймеры.

**Independent Test**: до React render два действия дают один POST; login держит slot через me. Protected401 при pending очищает UI, но не открывает login submit до собственного completion/timeout Logout. Оба порядка protected401/204 и старые account/search/results/error/finally/timers после retry/login не меняют новые данные/маршрут/notice/busy.

### Обязательные тесты

- [ ] T048 [P] [US4] Расширить `frontend/tests/unit/sessionState.test.ts` schedules UI-1/UI-2/UI-3: protected401 first и Logout first, generation сменился при busy, terminal attempt, timeout→retry/login→старые timer/finalizer; результат: старый completion освобождает только собственную операцию и не меняет текущий notice/route/attempt. Покрывает C-19, C-21, C-22.
- [ ] T049 [P] [US4] Расширить `frontend/tests/unit/useAuthSession.test.tsx`: два синхронных вызова до render, login→me удерживает slot, logout во время login и login во время pending не отправляются/не ставятся в очередь, current protected401 в idle/failed/pending и поздние204/error/timeout; результат: очищенная auth не восстанавливается, shared busy снимается только владельцем по окончании собственного ожидания. Покрывает C-19, C-21, C-22.
- [ ] T050 [P] [US4] Создать `frontend/tests/unit/protectedRequests.test.tsx` для startup/account/admin search с deferred results: старые success/error/401/finally после generation replacement и stale request в том же search, hash change при pending; результат: никаких новых protected effects во время pending, ни account/search/card/error/route/busy не получают устаревшее значение. Покрывает C-19, C-21, C-22.
- [ ] T051 [P] [US4] Создать `frontend/tests/browser/logout.spec.ts` с controlled response ordering для double click/Enter, меню/hash и смены попытки/login; результат: ровно один POST, protected401 открывает login с disabled submit до завершения Logout, поздние callback/data/таймеры игнорируются, без требования блокировать browser Set-Cookie поколениями. Покрывает C-19, C-21, C-22, C-24.

### Реализация и проверка

- [ ] T052 [US4] Довести stale transitions в `frontend/src/auth/sessionState.ts`: сравнивать generation и live attempt для UI отдельно от operationId для release; результат: clear/replacement меняют generation, clear не снимает slot, terminal IDs не оживают, все T048 PASS. Зависит: T048.
- [ ] T053 [US4] Довести синхронные refs/ownership/timer cleanup в `frontend/src/auth/useAuthSession.ts`: guard до любого await/send, захват login до fetch через me, protected401 clear без release Logout, поздние own finalizers могут снять только свой slot; результат: T049 PASS, нет snapshot restore/autoqueue. Зависит: T049, T052.
- [ ] T054 [US4] Довести обе стороны shared gate в `frontend/src/pages/AuthPage.tsx` и presentation pending guards в `frontend/src/components/Header.tsx`; результат: disabled/aria-busy отражают синхронный guard, повторный submit/Enter/Space/меню не отправляет запрос, login остаётся заблокирован после protected401 до Logout completion, тесты T049/T051 проходят для auth actions. Зависит: T053.
- [ ] T055 [US4] Проставить generation/request identity на startup/account/search success/error/401/finally в `frontend/src/App.tsx`, `frontend/src/pages/AccountPage.tsx` и `frontend/src/pages/AdminPage.tsx`; результат: проверяется актуальность всех callbacks, search freshness дополнительно к generation, pending не запускает route/debounce/page/card protected requests после hash navigation, T050 PASS. Зависит: T050, T054.
- [ ] T056 [US4] Прогнать UI-1/UI-2/UI-3 в `frontend/tests/unit/sessionState.test.ts`, `frontend/tests/unit/useAuthSession.test.tsx`, `frontend/tests/unit/protectedRequests.test.tsx` и `frontend/tests/browser/logout.spec.ts`; результат: все порядки late204/error/401/data/timer/finally PASS, C-19/C-21/C-22/C-24 evidence сохранены в `specs/001-session-logout/validation.md`. Зависит: T051, T055.

## Phase 7: US5 — Безопасное серверное закрытие при конкуренции (P1)

**Цель**: доказать атомарность и актуальность состояния на настоящем PostgreSQL, commit-before-response и фактические error/cookie guarantees публичной цепочки.

**Independent Test**: PG-1–PG-7 и fault matrix на отдельных real connections, observer после завершения. Два Logout→204+401/одно closed_at; оба порядка Auth/Logout; expiry при verify/lock wait; deactivation/delete; ранее аутентифицированный бизнес-запрос может закончиться. До подтверждения production commit нет ASGI start; failures не дают204/deletion.

### Обязательные тесты — последовательные расширения общих файлов

- [ ] T057 [US5] Создать PG-1/PG-2/PG-3 в `backend/tests/integration/database/test_logout_concurrency.py` на T003: оба Logout preliminary-read/verify open, A lock/save/commit затем B reread; Logout stale pre-read→Auth use/commit→Logout locks; Auth verified→Logout commit→Auth locks; результат: отдельные sessions/connections, один204+один401/session_closed/одно closed_at, Auth-first свежие last_used_at/expires_at сохранены, Logout-first Auth401 без resurrection. Покрывает C-14.
- [ ] T058 [US5] Добавить PG-4 в `backend/tests/integration/database/test_logout_concurrency.py`: pause verify и отдельно удерживать user row lock другим соединением, подтвердить реальное ожидание через gate/pg_blocking_pids, сдвинуть controlled UTC финальной проверки к ==/>expires_at после locks; результат:401/session_expired без close/use/renewal, без sleep-only доказательств, все gates bounded. Покрывает C-05.
- [ ] T059 [US5] Добавить PG-5 в `backend/tests/integration/database/test_logout_concurrency.py`: между verify и финальной проверкой отдельный actor commits deactivation/delete owner; отдельно gate бизнес-операции после её обычного Auth до Logout commit; результат: inactive204 без активации, deleted401/session_not_found (CASCADE не close), ранее authenticated операция может завершиться после Logout, другие сессии не закрыты. Покрывает C-02, C-15.
- [ ] T060 [US5] Добавить PG-7 identity-map regression в `backend/tests/integration/database/test_logout_concurrency.py`: удержать strong reference ранее загруженного SessionORM, другой actor commits renewal/close, затем FOR UPDATE+populate_existing read; результат: реально обновлённый snapshot используется Logout и ordinary Auth, свежие времена не теряются, closed не resurrect; existing adapters `backend/app/infrastructure/database/repositories/user.py` и `backend/app/infrastructure/database/repositories/session.py` остаются источником SQL. Покрывает C-14.
- [ ] T061 [US5] Написать отдельный PG-6 commit-before-response integration test в `backend/tests/integration/database/test_logout_commit.py`: production SessionController + function-scope DI + настоящая транзакция, gate commit и collector ASGI send; результат: после handler/flush до release commit нет `http.response.start` или cookies downstream, после successful commit observer видит close и только затем204/deletion, при commit failure mapper заменяет подготовленный успех. Покрывает C-01, C-11, C-16; не подменять factory на `session.begin()` fixture.
- [ ] T062 [US5] Добавить read/update/flush/commit faults в `backend/tests/integration/database/test_logout_commit.py` через controllable wrappers реальных соединений/factory: known pre-commit failure с rollback→observer open; unknown acknowledgement — реально commit, затем wrapper теряет подтверждение→error/no session cookie, observer может видеть closed; результат: нет204 при faults, error JSON/log не содержат raw SQL/exception/credential и не обещают rollback неизвестного исхода. Покрывает C-11, C-16, C-17.
- [ ] T063 [US5] Довести backend negative/actual-response matrix в `backend/tests/api/test_logout.py` и production-factory variants в `backend/tests/integration/database/test_logout_commit.py`: duplicate/missing/wrong CSRF с плохими cookie/body/query без auth repository reads; {},null,space,damaged JSON/любой query до cookie;405/HEAD/OPTIONS; corrupt hash400, unavailable503, unexpected500 с raise_server_exceptions=False; результат: no-store/envelope на реальном mapper/routing/finalization output, отсутствие session mutation на всех non401 errors. Покрывает C-06–C-08, C-11, C-16, C-17.
- [ ] T064 [US5] Расширить публичную X matrix в `frontend/tests/server.test.mjs`: нормализованные Origin/effective port и null/malformed/scheme/hostname/port mismatch, absence+CSRF, forged X-Forwarded-Proto, missing/duplicate CSRF, invalid body >16KiB/query, Cookie/CSRF exact forwarding, status/Set-Cookie/Allow/no-store, GET/HEAD/OPTIONS, 3xx/no cookie/no registration conversion; результат: реальные Node HTTP requests/upstream counters доказывают приоритет до auth и семантику headers, baseline login/register tests сохранены. Покрывает C-06–C-11, C-17.

### Интеграционное укрепление и проверка

- [ ] T065 [US5] Довести production атомарную orchestration в `backend/app/application/usecases/logout.py` и сборку `backend/app/presentation/api/di/logout.py` по выявленным T057–T061 failures; результат: ровно user→session FOR UPDATE, проверенные owner/hash совпадают с refreshed entity, свежий now после locks, close/update в одной ordinary factory transaction, no commit/Auth/use в Logout, PG-1–PG-7 PASS без новых repo methods/SQL обходов/миграций; существующий Auth independent renewal on403 остаётся PASS. Зависит: T057–T064.
- [ ] T066 [US5] Довести actual-response/fault policy в `backend/app/presentation/setup_exceptions.py`, `backend/app/presentation/logout_response.py`, `backend/app/infrastructure/database/session.py` и публичную policy в `frontend/server/proxy.mjs` по T062–T064; результат: commit/500/405/proxy ошибки безопасны/no-store/envelope, подготовленная deletion не утекает, unknown outcome не называется rollback, T062–T064 PASS без изменения контрактных статусов/приоритетов и без retries. Зависит: T065.
- [ ] T067 [US5] Выполнить real-PG suites `backend/tests/integration/database/test_logout.py`, `backend/tests/integration/database/test_logout_concurrency.py`, `backend/tests/integration/database/test_logout_commit.py`, backend API и `frontend/tests/server.test.mjs`; результат: все PG-1–PG-7/fault cases и C-01–C-17 соответствующих уровней PASS, skips не принимаются, committed fixtures очищены, evidence расписаний/observer/ASGI order записаны в `specs/001-session-logout/validation.md`. Зависит: T066.

**Требования к расписаниям T057–T062**: barriers/events вокруг реальных adapters, разные connections для actors и observer, один event loop внутри `asyncio.run`, все ожидания bounded/finally-unblock/cleanup. Не ставить rendezvous, которого оба actor должны достигнуть уже удерживая один exclusive lock; no random sleep как доказательство порядка. Unit mock не является PG schedule.

## Phase 8: US6 — Доступный интерфейс, навигация и другая вкладка (P2)

**Цель**: завершить доступный путь выхода, baseline navigation/reload и принятую межвкладочную границу. P2 не делает accessibility/security тесты опциональными.

**Independent Test**: pointer/touch/Enter/Space, screen-reader semantics/focus/manual announcements и узкий экран; Back/Forward/hash не показывают очищенные данные, reload401→login/unavailable→baseline retry, новый login только новый account. Две страницы общей cookie очищаются на next current401/reload; late deletion допускается, новая серверная сессия остаётся open и old callback не меняет новый UI.

### Обязательные тесты

- [ ] T068 [P] [US6] Расширить `frontend/tests/unit/logoutUI.test.tsx` и `frontend/tests/unit/protectedRequests.test.tsx`: focus trigger при start, progress вне dropdown/role=status/aria-busy/aria-disabled, persistent alert/retry/dismiss, login heading/status, modal-unmount cleanup, baseline startup401/unavailable/retry и нового аккаунта; результат: callback guards не возвращают старые данные/ошибки и focus не уходит в исчезнувшую карточку. Покрывает C-25, C-27.
- [ ] T069 [P] [US6] Расширить `frontend/tests/browser/logout.spec.ts`: mouse/touch/Enter/Space, keyboard repeat/dismiss, narrow viewport без обрезки, accessible roles/names/status/alert, Back/Forward/protected hash/reload401 и me-unavailable/retry, новый login; результат: только актуальный account без старого search/card/notice, никакого protected frame на login. Покрывает C-25, C-27.
- [ ] T070 [P] [US6] Добавить two-page shared-context HTTPS api-mode cases в `frontend/tests/browser/logout.https.spec.ts` и gates/observer в `frontend/tests/browser/support/logoutHttps.mjs`: другая вкладка next protected401/reload, поздний old Logout response после нового login другой вкладки и той же после timeout; результат: old callback не меняет новый UI, новая независимая запись реально open/usable при credential harness, возможная потеря новой cookie принимается и не скрывается browser interception. Покрывает C-22, C-26.

### Реализация и проверка

- [ ] T071 [US6] Довести accessibility в `frontend/src/components/Header.tsx`, `frontend/src/pages/AuthPage.tsx` и `frontend/src/components/AccountModal.tsx` (guard focus cleanup при unmount), объявление busy/disabled/status/alert и заголовка login; результат: focusable trigger не запускает pending actions, keyboard/touch действия доступны, modal не перехватывает heading focus, T068/T069 accessibility assertions PASS. Зависит: T068–T070.
- [ ] T072 [US6] Добавить адаптивное оформление progress/notices/alert/retry/dismiss в `frontend/src/styles/global.css`; результат: текст и действия не обрезаются на narrow viewport, есть различимый focus/disabled state, T069 responsive cases PASS без смены UI framework. Зависит: T071.
- [ ] T073 [US6] Довести account-based navigation и baseline startup/retry в `frontend/src/App.tsx`, current protected401 guards в `frontend/src/pages/AccountPage.tsx` и `frontend/src/pages/AdminPage.tsx`; результат: history/hash не восстанавливают subtree, reload401→login, unavailable me→baseline loading error с явным retry, новый login показывает только новый account, другая вкладка очищается по next401/reload без broadcast/polling. Зависит: T072.
- [ ] T074 [US6] Расширить credential-safety assertions в `frontend/tests/browser/logout.https.spec.ts` и `frontend/tests/server.test.mjs`: нет JWT в app JS/localStorage/sessionStorage/JSON/Authorization/прикладных логах и ручного HttpOnly delete, test credential доступен только harness; через настоящий HTTPS proxy повторить public GET/HEAD/OPTIONS, normalized/mismatched/null/missing Origin и отсутствие upstream на отказе, проверить исходные Cookie/CSRF и response headers fixture; результат: C-08–C-10 проверены также на публичной HTTPS границе, HTTPS401/204 и error cookie matrix остаются PASS, late cookie effect не подменяется ложной гарантией сохранности нового cookie. Покрывает C-08–C-11, C-26, C-27. Зависит: T070, T073.
- [ ] T075 [US6] Выполнить ручной screen-reader/keyboard/narrow-screen walkthrough из `specs/001-session-logout/quickstart.md` на `frontend/src/components/Header.tsx` и `frontend/src/pages/AuthPage.tsx`, записать окружение/фактические announcements/focus/actions в `specs/001-session-logout/validation.md`; результат: C-27 подтверждён автоматическими assertions и ручным воспроизведением, DOM role не выдан за полную проверку удобства диктора. Зависит: T074.
- [ ] T076 [US6] Прогнать F/B navigation/accessibility и HTTPS api-mode two-page cases в `frontend/tests/browser/logout.spec.ts` и `frontend/tests/browser/logout.https.spec.ts`; результат: C-25/C-26/C-27 PASS, independent new session observer evidence сохранён в `specs/001-session-logout/validation.md`, граница late deletion и отсутствие мгновенной синхронизации явно зафиксированы. Зависит: T075.

## Phase 9: Polish & Cross-Cutting Concerns — обязательные release gates

- [ ] T077 Актуализировать baseline документацию `docs/endpoints/auth.md`, `docs/auth.md`, `docs/entities/session.md`, `docs/entities/user.md`, `docs/repositories.md`, `docs/security.md` и `frontend/README.md` по фактически реализованному поведению; результат: auth_logout/OpenAPI, ADR-07 исключение, factory commit-before-response с research R-03, HTTPS/PUBLIC_ORIGIN,15/20s и cookie-race отражены согласованно, CONTRACT/REVIEW/V1/V2/spec/plan/contracts не переписаны. Зависит: T076.
- [ ] T078 Провести архитектурный review `backend/app/application/usecases/logout.py`, `backend/app/presentation/api/di/logout.py`, `backend/app/infrastructure/database/session.py`, `frontend/src/auth/sessionState.ts`, `frontend/src/auth/useAuthSession.ts`, `frontend/server/proxy.mjs`; результат: Constitution I–VI и ADR-01–ADR-11 сохранены, никаких новых слоёв/DTO/SQL в Application/миграций/Auth commit в Logout/storage токенов/intertab coordinator/недоказанного rollback, findings и их task/C references в `specs/001-session-logout/validation.md`. Зависит: T077.
- [ ] T079 Выполнить полный validation sequence из `specs/001-session-logout/quickstart.md`: в `backend/` — `uv sync --group migrations --group service --group tests`, `uv run --group migrations alembic upgrade head`, `uv run --group migrations alembic check`, `uv run --group tests pytest tests/unit`, `uv run --group tests pytest tests/api`, `uv run --group tests pytest tests/integration/database`, `uvx ruff check app tests migrations run.py`; в `frontend/` — `npm ci`, `npm run build`, `npm test`, `npm run test:unit`, `npx playwright install chromium`, `npm run test:e2e -- tests/browser/app.spec.ts --workers=1`, `npm run test:e2e -- tests/browser/logout.spec.ts --workers=1`, затем обе HTTPS-команды fixture/api §4 quickstart без изменения flags/порядка; результат: семь уровней и baseline login/register/account/search/Auth renewal403 PASS без PG/HTTPS skips, TypeScript build/Ruff70/Alembic no drift, реальные команды/версии/результаты в `specs/001-session-logout/validation.md`. Зависит: T078.
- [ ] T080 Завершить acceptance report в `specs/001-session-logout/validation.md`, сверив каждую строку C-01–C-27 матрицы ниже с выполненными тестами, уровнями D/A/H/P/F/X/B и исходными acceptance scenarios `specs/001-session-logout/spec.md`; результат:27/27 доказательств без raw credential/ключей, ссылки на commit-order/PG schedules/HTTPS jar/manual a11y, baseline regression результаты и cleanup disposable окружения по quickstart; незавершённый/пропущенный gate не отмечается PASS. Зависит: T079.

## Dependencies & Execution Order

### Граф фаз и User Stories

```text
T001 → {T002 || T003 || T004} → Phase 2 (T005…T010)
  → US1 (T011…T030)
  → US2 (T031…T037)
  → US3 (T038…T047)
  → US4 (T048…T056)
  → US5 (T057…T067)
  → US6 (T068…T076)
  → Polish (T077…T080)
```

Стрелка фаз — обязательный barrier для безопасного **базового порядка исполнения**. У историй независимые критерии проверки, но общие существующие файлы создают реальные implementation dependencies. US2 расширяет core US1; US3 использует результаты204/401 и coordinator US1/US2; US4 укрепляет retry/deadline и protected callbacks US3; US5 проверяет production API/mapper/proxy US1–US3, окончательно закрепляет foundation на PostgreSQL; US6 использует guards US4 и server/cookie guarantees US5. Все P1 представлены в порядке spec; P2 следует за ними.

Внутри US1 backend цепочка: T011→T019→T020→T021→T023→T024; T013→T022→T023, T012→T020. Frontend цепочка: T015→T025→T026→T027→T028→T029; T016→T026. T014/T017/T018 и production ветки сходятся в T030. Эти ветки можно планировать отдельно после test wave, но `[P]` им намеренно не назначен: документационные/интеграционные gates остаются последовательными.

T057–T060 редактируют один concurrency test file; T061–T063 — общий commit test file; T007/T040/T064/T074 — общий proxy test file. Параллельная запись этих задач небезопасна, несмотря на различие проверяемых критериев. Все test waves ниже завершаются до implementation соответствующей фазы. Запуск PG actors внутри одного теста — проверяемая конкуренция, а не маркер `[P]` для реализации.

### Безопасные параллельные волны и примеры для каждой US

| Волна | Prerequisite | Одновременно допустимые задачи | Причина безопасности |
| --- | --- | --- | --- |
| Setup | T001 | T002 ∥ T003 ∥ T004 | npm/unit config, backend PG harness, HTTPS harness в разных файлах |
| US1 | вся Phase 2 | T011 ∥ T012 ∥ T013 ∥ T014 ∥ T015 ∥ T016 ∥ T017 ∥ T018 | независимые test files, общий harness только читается |
| US2 | T030 | T031 ∥ T032 ∥ T033 | backend unit/API, PG, frontend tests не пересекаются |
| US3 | T037 | T038 ∥ T039 ∥ T040 ∥ T041 | transport, coordinator/UI, Node proxy, PG loss tests в разных файлах |
| US4 | T047 | T048 ∥ T049 ∥ T050 ∥ T051 | state, hook, protected requests, browser tests раздельны |
| US5 | T056 | нет `[P]` | расписания последовательно расширяют одни test files и общую production finalization |
| US6 | T067 | T068 ∥ T069 ∥ T070 | unit, mocked-browser и HTTPS test/harness файлы раздельны |

Например, US1: одновременно написать T011 domain close tests и T018 HTTPS cookie tests; US2: T031 credential matrix и T033 malformed401 UI; US3: T040 gated HTTP deadlines и T041 PG lost reply; US4: T048 pure state и T051 browser event ordering; US5: выполнять T057→T058→T059→T060→T061→T062→T063→T064, не запускать редактирование общего файла параллельно; US6: T068 component focus и T070 shared-cookie two-page integration. Маркер `[P]` не отменяет фазовый prerequisite.

## Трассировка C-01–C-27 → реализация и обязательная проверка

Каждая строка имеет **обе** стороны: production задачи (включая сохранение уже существующих adapters) и задачи проверок. T079/T080 дополнительно обязательны для всех строк. Это план покрытия, не отчёт PASS.

| Критерий | Задачи реализации | Задачи проверки | Уровни / доказательство |
| --- | --- | --- | --- |
| C-01 | T019–T024, T025–T029 | T012–T014, T030, T061 | A/H/P/B; все роли,204 после commit, body0, no-store, no Location, только предъявленная сессия |
| C-02 | T020, T034, T065 | T012, T014, T030, T059 | A/P/B; inactive→204, времена/активность неизменны, reactivation не оживляет JWT |
| C-03 | T020–T024, T034–T035 | T031–T032, T037 | A/H/P; T031 — полная API credential-матрица, включая missing/empty cookie/Bearer-only; T032 — реальные JWT/Argon2id + PostgreSQL для JWT/secret/session/owner defects, observer до/после и401/reason/deletion без записи Logout; cookie attributes переиспользуют T018 |
| C-04 | T019–T020, T034–T035 | T011, T031–T032, T037 | D/A/H/P; closed reason/неизменный closed_at, no-cookie missing reason |
| C-05 | T019–T020, T034, T065 | T011, T031–T032, T058, T067 | D/A/P; T011 — domain ensure_usable при ==/> expiry; T032 — persisted-state/verify, T058 — реальный PG lock wait, no close/renewal |
| C-06 | T008, T023–T024, T066 | T007, T013, T063–T064, T067 | H/X; raw duplicate CSRF priority без auth reads/изменений/cookie |
| C-07 | T008, T023–T024, T066 | T007, T013, T063–T064, T067 | H/X; все body/query variants до cookie, body0±Content-Type, no413/422 |
| C-08 | T008, T023–T024, T066 | T007, T013, T063–T064, T067, T074 | H/X/B; public/direct405 Allow/no-store/envelope, HEAD0/OPTIONS no session/CORS; T074 — публичные GET/HEAD/OPTIONS через настоящий HTTPS proxy |
| C-09 | T008 | T007, T064, T067, T074 | X/B; полная normalized Origin matrix/trusted configuration/no upstream |
| C-10 | T008, T045 | T007, T018, T040, T064, T074 | X/B; реальные forwarding/headers/no-follow/no Logout201 |
| C-11 | T022–T024, T035, T045, T066 | T013, T018, T030, T037, T040, T061–T064, T074 | H/P/X/HTTPS B; отдельный cookie suite + finalization faults, полная status/атрибут matrix |
| C-12 | T019–T024 | T014, T030 | P/HTTPS B; copied JWT me401, независимая сессия работает |
| C-13 | T019–T020 | T011, T014 | D/P; max/idempotent/history, остальные поля неизменны |
| C-14 | T020–T021, T065 | T057, T060, T067 | real P; PG-1/2/3/7, реальные locks/refreshed ORM/observer |
| C-15 | T020, T034, T065 | T012, T059, T067 | A/real P; PG-5 owner mutations и gate уже authenticated бизнес-операции |
| C-16 | T010, T021–T024, T065–T066 | T009, T041, T061–T063, T067 | H/real P; отдельный ASGI commit-order gate, read/update/flush/commit faults, known/unknown outcome |
| C-17 | T010, T022–T024, T034–T035, T045, T066 | T009, T031, T040, T062–T064, T067, T074 | A/H/P/X; actual mapper/500/405/commit/proxy, corrupt hash400, безопасные JSON/logs |
| C-18 | T025, T034–T037, T042–T044 | T015, T033, T038–T039, T047 | F/B;204 only, known401 без JSON, точные безопасные messages |
| C-19 | T006, T026–T029, T052–T055 | T005, T016, T048–T051, T056 | F/B; onePOST, двусторонняя serialization через login me, no queue/new protected actions |
| C-20 | T026–T029, T036–T037 | T017, T030, T033, T037 | F/B; atomic personal-data clear, login success/neutral401, no extra me/retry |
| C-21 | T006, T043, T052–T055 | T005, T039, T048–T051, T056 | F/B; UI-1, current401 очищает, pending slot живёт, поздний204/error не восстанавливает |
| C-22 | T006, T026–T027, T043, T052–T055 | T005, T016, T048–T051, T056, T070 | F/B; UI-2/3, stale account/search/401/finally/callback/timer/owner |
| C-23 | T042–T045 | T038–T040, T047 | F/X/B; 14999/15000 и19999/20000, body phase, no retry, real-time representative |
| C-24 | T020–T024, T042–T045, T052–T053 | T039, T041, T046–T047, T051, T056 | real P/F/X/B; LOSS-1, manual retry401, late response не завершает новый attempt |
| C-25 | T027, T029, T052–T055, T073 | T068–T069, T076 | F/B; history/hash/reload baseline retry и только новый account |
| C-26 | T020, T052–T055, T073 | T070, T074, T076 | P/F/X/HTTPS B; shared cookie next401/reload, independent new server session, accepted late deletion |
| C-27 | T008, T025, T028–T029, T044, T071–T072 | T015, T017–T018, T068–T070, T074–T076 | F/X/B; keyboard/touch/narrow/focus/status/alert + manual reader, нет JWT JS/storage/Authorization/delete |

### Сохранение ADR-01–ADR-11

| ADR | Реализация / review | Обязательный gate |
| --- | --- | --- |
| ADR-01 | T019–T025, T034–T037 | T013–T015, T030–T033 |
| ADR-02 | T008, T023 | T007, T063–T064 |
| ADR-03 | T008, T045 | T018, T040, T064, T074 |
| ADR-04 | T022–T024, T035, T066 | T018, T061–T064, T074 |
| ADR-05 | T006, T026, T043, T052–T055 | T048–T051, T070, T076 |
| ADR-06 | T006, T027, T043, T052–T055 | T048–T051, T056 |
| ADR-07 | T020, T034–T037 | T014, T030–T033, T059 |
| ADR-08 | T008, T023 | T007, T013, T063–T064 |
| ADR-09 | T010, T024–T025, T042, T045, T066 | T038–T040, T062–T064 |
| ADR-10 | T042–T045 | T038–T041, T046–T047 |
| ADR-11 | T019–T024, T065 | T012, T014, T057–T062, T067 |

T077 документирует сохранённые решения; T078 проверяет все ADR совместно. Никакой task не разрешает изменить утверждённый контракт или усилить принятые cookie/cancellation гарантии.

## Implementation Strategy

### MVP first

Сначала Setup/Foundation, затем US1 как минимальный демонстрируемый вертикальный срез: entity→usecase→DI→HTTP/factory→proxy→transport/coordinator→UI→PG/HTTPS проверки. Его можно проверить самостоятельно на валидной сессии. Для выпуска фичи нужны все пять P1 историй, обязательная US6 и T077–T080; демонстрация US1 не означает приёмку C-01–C-27.

### Incremental delivery

После US1 добавить invalid credential путь US2, затем failure/recovery US3, полностью проверить local stale-event ordering US4, закрепить real-PG/commit/public-boundary guarantees US5, завершить navigation/accessibility/two-tab US6. После каждого story checkpoint прогнать её независимый критерий и затронутые baseline regressions. Исправления по тестам делаются только в названных production слоях, без редактирования контрактов.

### Summary и Definition of Done

| Область | IDs | Количество |
| --- | --- | ---: |
| Setup | T001–T004 | 4 |
| Foundational | T005–T010 | 6 |
| US1 (P1) | T011–T030 | 20 |
| US2 (P1) | T031–T037 | 7 |
| US3 (P1) | T038–T047 | 10 |
| US4 (P1) | T048–T056 | 9 |
| US5 (P1) | T057–T067 | 11 |
| US6 (P2) | T068–T076 | 9 |
| Polish / cross-cutting | T077–T080 | 4 |
| **Всего** | **T001–T080** | **80** |

Story subtotal — **66** (20+7+10+9+11+9), общие задачи — **14** (4+6+4), итого **80**. Параллельных задач с `[P]` — **25**:3 setup +8 US1 +3 US2 +4 US3 +4 US4 +3 US6. US5 намеренно последовательна.

Готовность будущей реализации: все80 checklist tasks выполнены, все27 C имеют production implementation и evidence нужного уровня, real-PG/commit-order/HTTPS-cookie gates не skipped, baseline и tooling checks PASS, документация синхронизирована. В текущем сеансе создаётся только этот план; implement не запускается.
