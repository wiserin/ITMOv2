# Session Logout: Verification Strategy

**Date**: 2026-11-02 · **Status**: план будущих проверок, не test execution report.
Основание: [CONTRACT C-01–C-27](../../docs/sdd/logout/CONTRACT.md),
[spec](spec.md), [Constitution V](../../.specify/memory/constitution.md).
Команды, environment и границы готового tooling — [quickstart](quickstart.md).

## 1. Семь уровней и существующий baseline

| Код | Уровень | Что доказывает / чего не подменяет |
| --- | --- | --- |
| D | Domain unit | Immutable close, идемпотентность, времена; без SQL/HTTP/env |
| A | Application unit | Порядок decode/read/verify/locks/recheck/close/update, constructor DI, no Auth/use/commit; моки допустимы только здесь |
| H | API | Raw HTTP validation/order, статусы/envelope/cookies/mapper/405/HEAD; overrides не доказывают реальный commit |
| P | PostgreSQL integration | Реальные transactions/locks/refreshed ORM/commit/rollback, HTTP+production factory и persisted effects |
| F | Frontend unit/component | Auth slot/generation/attempt ownership, transport и React actions/states/focus с deferred results/fake clocks |
| X | Proxy integration | Реальные Node HTTP server и upstream fixture, вход/выход/Origin/методы/таймеры, не только mock-fetch |
| B | Browser E2E | Взаимодействия, navigation/focus/mobile, real HTTPS cookie; full-stack mode подтверждает API integration |

Переиспользуются backend fixtures и baseline `test_session_use`, `test_auth`, security/thread
tests, `test_repository_di`, `test_auth_flow`, `test_repositories`. Production commit tests
не подменяют SessionController фабрикой `session.begin()`, как делает часть старых auth fixtures.
API test app должен иметь те же handlers/router/DI scopes, что production.

Frontend: сохранить `node:test` из `tests/server.test.mjs` и Playwright из
`tests/browser/app.spec.ts`; заменить expectation Logout-заглушки. Vitest/Testing Library
и HTTPS config добавляются позже как dev-only tooling. Старые page.route UI stubs не доказывают
работу proxy/cookie или сохранение сессии.

## 2. Контрольные точки по уровням

### D — Domain unit

`backend/tests/unit/domain/test_session_close.py`:

- now before/equal/after last_used_at → closed_at=max; default now — aware UTC.
- Повтор close с другим временем сохраняет исходный closed_at; исходная сущность не мутирована.
- Сравнение всех immutable полей, hash/history; отличие domain close от HTTP eligibility.
- Совместно с ensure_usable проверить now==expires_at/>, closed и не вызывать use при close.

### A — Application unit

`backend/tests/unit/application/test_logout.py`:

- Existing JWT decode offload и async secret verify, не блокирующие event loop.
- Предварительное чтение/eligibility/verify перед owner→session locks, fresh UTC после locks.
- После verify изменить возвращённые owner/hash/expiry/closed state: не сохранить stale entity;
  owner/hash mismatch не даёт success, без нового публичного error-кода.
- Missing owner/session, invalid secret/JWT, expired/closed и inactive owner ветви.
- No AuthUseCaseDI/authenticate/use/explicit commit; repo receives close result.
- Verify corrupt hash DataFormatException сохраняется400, а не broad401 conversion.

### H — API

`backend/tests/api/test_logout.py` и existing DI regression:

- Request body0 с/без Content-Type; {}, null, space, arbitrary/damaged JSON; query с пустым value.
- Missing/invalid/ambiguous CSRF raw headers и их приоритет над input/cookie.
- Cookie missing/empty/Bearer-only; все одиночные credential reasons через appropriate boundary.
- POST204 zero bytes/no Location/no JSON; фактические401 cookies со всеми атрибутами.
- Ошибки400/403/405/500/503 без session Set-Cookie, no-store/envelope, HEAD без body, Allow.
- Сбой function dependency после создания204: новый error response, не успех/deletion.
- Unexpected500 проверять с TestClient raise_server_exceptions=False; отдельно logged context
  не содержит secrets/raw SQL/exception text. Baseline errors других endpoints не меняются.

### P — PostgreSQL integration

Три будущих файла: `test_logout.py`, `test_logout_concurrency.py`, `test_logout_commit.py`
в `backend/tests/integration/database/`.

- Existing migrations applied; committed per-test users/sessions, разные AsyncSession/connection
  для участников; observer connection проверяет фактически сохранённые поля после завершения.
- Real adapters/security, role/inactive/reactivation, old JWT rejection и независимая сессия.
- Production SessionController error translation и function-scope DI, не только simplified fixture.
- Gated реальный commit + ASGI send capture: до release commit нет http.response.start;
  после успешного commit возможен только204. Flush/UseCase return не являются этим доказательством.
- Для read/update/flush/commit failures использовать controllable wrappers/fault hooks вокруг
  реальных соединений; сохранить реальную транзакцию и independent observer. Unit mock не выдаётся
  за integration. Проверить safe mapper, отсутствие success/deletion и persisted state.
- Known rollback: искусственный отказ до successful commit, observer видит open.
  Unknown acknowledgement: реально выполнить commit, затем симулировать потерю подтверждения
  в wrapper; ответ ошибка/no cookie, observer может видеть closed. API/лог не обещает rollback.
  Это детерминированная fault model потери acknowledgement, не заявление о реальном TCP-сбое.

### F — Frontend unit/component

`frontend/tests/unit/`: transport, state/coordinator и App/Header/AuthPage integration.

- Deferred transport/response-body promises, fake time с14999/15000 для proxy adapter и
 19999/20000 для UI; UI20s отсчитывается от dispatch, не после response headers.
- Два вызова до React render получают ровно одного operation owner; login держит slot через me.
- При protected401 в pending auth очищена, slot busy; каждый из поздних204/ошибки/timeout
  не меняет новый notice/account, а release применяется только к owner.
- Два порядка Logout204/protected401, stale account/search/error401/finally после login/retry,
  timeout→новый attempt→старый timer; никаких snapshot restores или unlock нового owner.
- Header progress вне dropdown, repeat/dismiss persistent alert, exact messages;
  клавиатурные действия, focus heading/trigger и modal cleanup.
- Не-2042xx/403/5xx/non-JSON не успех; malformed JSON401 сохраняет known401; network/status0
  отличается от полученного HTTP. Не логировать/показывать raw message/details.

### X — Proxy integration

Расширить `frontend/tests/server.test.mjs` с настоящим frontend HTTP server и gated upstream.

- Полный Origin matrix (scheme/hostname/effective port, normalized equivalents, null/malformed,
  absence), config PUBLIC_ORIGIN, forged X-Forwarded-Proto не меняет trust.
- Methods405/Allow/no-store/envelope, HEAD0, OPTIONS без auth/upstream/CORS.
- Raw HTTP duplicate CSRF, missing value без синтеза; bad CSRF+bad body/query/cookie→403;
  valid CSRF+любой непустой body/query→400, включая >16KiB против regression generic413.
- Проверить число upstream-вызовов/исходные Cookie/CSRF и не-lossy response headers.
- Upstream302/303 с Set-Cookie→502 без его cookie/no follow; registration303→201 regression.
- Отдельные stalls до headers и посреди body: статус/cookie не попадают downstream до read end.
  Через15s504/upstream_timeout, другая ошибка502/upstream_failure, no cookie, no retry.
- Для точных границ inject deadline scheduler/clock в test harness с production default15000;
  реальный HTTP и upstream gates сохраняются. Проверить отсутствие раннего timeout14999ms,
  затем advance1ms. Не менять production budget ради быстрого теста.

### B — Browser E2E

- Mocked-UI project: deterministic event ordering, exact texts, double pointer/Enter/Space,
  hash/menu/history/reload, protected401, next login, keyboard/screen-reader semantics, narrow screen.
- Отдельный HTTPS project: Browser→real Node proxy→fixture upstream без page.route bypass;
  проверить actual response Set-Cookie и browser cookie jar (host-only/path/secure/httpOnly/
  sameSite/expires), удаление на204/401 и сохранение командой ответа на остальных ошибках.
- Full-stack HTTPS mode: Browser→real proxy→real API→real PostgreSQL, сохранить копию JWT
  в test harness (не в app JS/storage), после204 проверить отказ старого и другую сессию.
- Снимки/trace только тестового окружения; приложение не читает JWT/localStorage/sessionStorage,
  Authorization не отправляется, нет ручного cookie удаления.
- Две страницы одного browser context разделяют cookie: после close другая очищает UI на
  следующем protected401/reload. Контролируемо задержать старый ответ и выполнить новый login;
  не требовать сохранности новой cookie, проверить независимость server session и stale UI guard.
- Представительный15/20s сквозной сценарий выполняется с реальным временем/тестовым timeout>20s;
  точные deadline boundaries и остальные permutations — виртуальные часы уровнейF/X.
  Скринридерная проверка включает accessible roles/names/status/alert и ручное воспроизведение
  объявлений; наличие DOM role само по себе не доказывает удобство всех экранных дикторов.

## 3. Детерминированные конкурентные расписания

Все PostgreSQL actors используют отдельные connection/session и одинаковый lock order.
Сохранить существующий pytest pattern: один `asyncio.run(...)` на сценарий, все конкурентные
actors и barriers внутри одного event loop; дополнительный pytest-asyncio plugin не нужен.
Events/barriers в test wrappers вокруг реальных adapters координируют стадии, но не заменяют SQL.
Для подтверждения lock wait можно использовать pg_blocking_pids и контрольный запрос observer;
ограниченный polling — диагностика ожидания, не случайный sleep как доказательство порядка.
Не ставить rendezvous после захвата одного exclusive lock обоими участниками: второй не дойдёт.
Каждое ожидание ограничено; finally освобождает gates/locks, удаляет свои committed fixtures
и dispose engines. Bootstrap root не используется как изменяемая fixture.

| Schedule | Управление порядком | Проверяемый результат |
| --- | --- | --- |
| PG-1: Logout/Logout | Оба preliminary read+verify open; A lock/save/commit; B продолжает lock+reread после A | Один204, один401/session_closed; один closed_at |
| PG-2: Auth→Logout | Logout держит stale preliminary entity; Auth use+commit; release Logout на locks | Закрыта свежая продлённая запись; времена Auth сохранены |
| PG-3: Logout→Auth | Auth проверил secret до locks; Logout close+commit; release Auth | Auth401, без use/update renewal; closed_at сохранён |
| PG-4: Expiry | Pause verify или удерживать owner lock другой connection; final now сдвинуть контролируемыми часами после получения locks | now==/>expiry→401 без close/use; lock wait реально PostgreSQL |
| PG-5: Owner mutation | Pause после verify; отдельный actor commits deactivation/delete; затем финальные locks | Inactive→204 без активации; missing→401; CASCADE не считается close |
| PG-6: Commit/send | Gate production commit; collector ASGI send проверяет отсутствие start; затем commit success/failure |204 только после commit, либо mapped error без deletion |
| PG-7: Identity map | Сохранить strong reference loaded SessionORM; другой actor commits renewal/close; locked populate_existing read | Ни lost times, ни resurrect closed snapshot |
| UI-1: protected401 first | Deferred protected401 до Logout result; затем каждый из204/error/timeout | Clear, login locked до own completion, notice не заменён |
| UI-2: Logout first |204 меняет generation, затем old protected401/search success/failure | Success notice/new account не меняются старыми событиями |
| UI-3: timeout/new attempt | Advance20s, acquire retry/login slot, resolve old promise и old finally | Только новый owner меняет UI/release; late cookie effect отдельно |
| LOSS-1: reply lost | Доказать persisted close observer после commit, оборвать доставку подтверждения | Нет UI success; manual retry401; исходный closed_at прежний |

## 4. Полная матрица C-01–C-27

Каждая строка сохраняет требования исходного критерия; сокращения уровней определены выше.
Это план coverage, не отметки выполненных тестов.

| Contract | Будущее доказательство | Уровни / schedules |
| --- | --- | --- |
| C-01 | Все3 роли, только предъявленная сессия; commit→204 zero body/no-store/no Location | A,H,P,B; PG-6 |
| C-02 | Inactive owner204, не активирован, usage/expiry неизменны, reactivation не оживляет old JWT | A,P,B; PG-5 |
| C-03 | Missing/empty cookie/Bearer-only, все одиночные JWT/UUID/secret дефекты, missing session/owner → appropriate401/deletion, без записи | A,H,P,X |
| C-04 | Closed→401/session_closed, исходный closed_at; no cookie→401/missing_session_cookie | D,A,H,P |
| C-05 | now==expiry/>expiry, expiry during verify/lock wait→401, no close/renewal | D,A,P; PG-4 |
| C-06 | Bad CSRF dominates bad cookie/body/query→403, no session auth read/write/no cookie mutation | H,X |
| C-07 | Nonempty body {},null,space,damaged JSON/any query incl empty value→400 before cookie; zero body±Content-Type allowed | H,X |
| C-08 | Public/direct GET405/Allow/no-store/envelope, no DB/cookie changes; HEAD0, OPTIONS no session/CORS | H,X,B |
| C-09 | Normalized Origin equivalent pass; scheme/host/port/null/malformed fail403 without upstream; no-Origin still CSRF | X,B |
| C-10 | Actual Cookie/CSRF forwarding, no synthesis; status/Set-Cookie/no-store/Allow preserved; no redirect follow/Logout201 | X,B |
| C-11 | Actual204/401 delete cookie with every attribute;400/403/405/500/502/503/504 no mutation header, including finalization errors | H,P,X,B; PG-6 |
| C-12 | Saved old JWT on account/me401 after204; independent session remains usable | P,B |
| C-13 | Domain close idempotence, backward-clock invariant, all other fields/history unchanged | D,P |
| C-14 | TwoLogout204+401/one closed_at; both Auth/Logout orders preserve times and do not resurrect | P; PG-1/2/3/7 |
| C-15 | Inactive owner before final check allowed; deletion401; preauthenticated business request may complete | A,P; PG-5 плюс gate бизнес-операции после Auth |
| C-16 | Real boundary read/update/flush/commit faults; no204/cookie, known rollback open, unknown commit not promised rollback, no HTTP before commit | H,P; PG-6, fault models §2P |
| C-17 | Actual controlled mapper/commit/405/proxy errors envelope/no-store; malformed hash400, safe JSON/logs | A,H,P,X |
| C-18 | Exact204 only; other2xx/403/5xx/malformed JSON no false success;401 still clear, exact safe messages | F,B |
| C-19 | Double click/Enter/hash/menu onePOST; login blocked during waiting, protected new actions gated | F,B |
| C-20 | Atomic account/search/page/card/error clear + Header/protected hide; login success204/neutral401, no repeat401 | F,B |
| C-21 | Current protected401 clears in pending without releasing slot; old result not restoring auth; failure retains only current auth | F,B; UI-1 |
| C-22 | Old account/search/Logout callbacks/timers/finalizers do not alter new data/route/notice/waiting | F,B; UI-2/3 |
| C-23 |15s504 no cookie if connection available;20s UI terminal ID; no early deadline, no autoretry | F,X,B; controlled clocks и representative real-time case |
| C-24 | Commit with lost reply: no UI success; explicit retry401 and clear; late result cannot finish new attempt | P,F,X,B; LOSS-1/UI-3 |
| C-25 | History/hash no data restore; reload401→login/unavailable→baseline error+retry; new login only new account | F,B |
| C-26 | Other tab next protected401/reload clears; accepted late-cookie race, independent new server record unaffected, old callback no UI mutation | P,F,X,B; two-page shared context |
| C-27 | Keyboard/screen-reader/narrow view, progress/status/alert/focus/retry/dismiss; no JWT JS/storage/Authorization/manual HttpOnly delete | F,X,B |

## 5. Exit criteria будущей реализации

Все27 критериев имеют выполненные проверки соответствующих уровней, а не только mock coverage.
Интеграционные skips без TEST_DATABASE_URL не считаются PASS; HTTPS suite не заменяется HTTP
localhost допущением Secure-cookie. Сохраняются baseline tests login/register/account/auth.
Ruff по исходникам/тестам и TypeScript build пройдены. Findings имеют привязку к C/FR;
новые расхождения с контрактом предъявляются на согласование, не «исправляются» усилением гарантий.
