# Implementation Plan: AnimeMap Session Logout

**Branch**: `practice_5` (фактическая Git-ветка) | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: `/specs/001-session-logout/spec.md`.
Spec Kit разрешает feature identifier `001-session-logout` через `.specify/feature.json`;
setup_plan сообщает его как BRANCH. Git-ветка не создавалась и не переключалась.
**Status**: Phase 0 research и Phase 1 design завершены; код и тесты не реализованы.

## Summary

Закрыть только предъявленную сессию через отдельный LogoutUseCase, существующие доменные
репозитории и транзакционную фабрику. Предметная команда immutable close сохраняет историю;
locks user→session и refreshed reread защищают от конкурентного продления/закрытия.
FastAPI function-scope DI сохраняет commit до отправки HTTP; mapper обрабатывает фактические
ошибки без утечки подготовленного удаления cookie. React получает App-owned coordinator
поколений и клиентских auth-операций; Node proxy сохраняет строгий публичный контракт.

Нормативный источник — [CONTRACT v1.0](../../docs/sdd/logout/CONTRACT.md),
поддерживающие источники — [UI V2](../../docs/sdd/logout/UI_SPEC_V2.md),
[Backend V2](../../docs/sdd/logout/BACKEND_SPEC_V2.md),
[Constitution](../../.specify/memory/constitution.md) и `agent-rules/`.
ADR-01–ADR-11 не меняются. Спецификация и исходные документы остаются без изменений.

## Technical Context

**Language/Version**: Python >=3.14 (локальная .venv 3.14.7); TypeScript5.9.3;
Node22.12+ в существующей Node22-линии (ограничение locked Vite).

**Primary Dependencies**: FastAPI0.162.0, Starlette1.10.0, SQLAlchemy2.1.6/asyncpg,
PyJWT EdDSA/Ed25519, Argon2id; React/ReactDOM19.3.1, Vite7.3.7;
Node HTTP/HTTPS и fetch без нового server framework. Версии взяты из lockfiles,
не являются запросом обновить runtime-зависимости.

**Storage**: существующий PostgreSQL18 и SessionORM.closed_at; Redis остаётся baseline
окружения, но не участвует в Logout. Схема, индексы и миграции не меняются.

**Testing**: pytest с существующим `asyncio.run(...)` pattern, HTTPS TestClient,
real PostgreSQL; node:test и Playwright1.64.1. pytest-asyncio не установлен и не требуется.
Для frontend unit/component запланированы dev-only Vitest3.2.x, jsdom26.x,
Testing Library React16.x/user-event14.x с закреплением совместимых patch в lockfile.
Их пока нет; `test:unit` и HTTPS Playwright config — будущие артефакты реализации.

**Target Platform**: существующее контейнерное приложение, браузер с HTTPS
Browser → same-origin Node.js proxy → FastAPI. Локальная проверка реального PostgreSQL
и HTTPS возможна вне Compose без смены production topology.

**Project Type**: web application с Python API, React SPA и Node static/proxy server.

**Performance Goals**: proxy15 000ms и UI20 000ms — бюджеты ожидания до завершения чтения,
не SLA скорости успешного Logout/завершения БД. JWT decode/Argon2id не блокируют event loop;
дорогой verify до row locks. Новые throughput/uptime цели не вводятся.

**Constraints**: только текущая сессия; неизменный JWT; no refresh/blacklist/new store;
no intertab lock/broadcast/polling; unknown commit не называется rollback;
исключение is_active только для собственного Logout. Python70 chars, установленные DI/naming.

**Scale/Scope**: одна фича, один endpoint, три существующие роли, все27 критериев контракта.
Число пользователей/сессий не переопределяется; новые scale-требования не требуются.

## Constitution Check

GATE проверен до Phase0 и повторно после Phase1. PASS здесь означает соответствие дизайна,
а не прохождение будущих функциональных тестов.

| Принцип | До research | После design | Проверяемое соответствие |
| --- | --- | --- | --- |
| I. Hexagonal / DDD | PASS | PASS | close в Domain, orchestration в Application, ORM и locks в адаптерах, HTTP в Presentation |
| II. Explicit Contracts | PASS | PASS | normative CONTRACT сохранён; contracts/ фиксирует интерфейсы, матрица покрывает C-01–C-27 |
| III. Dependency Injection | PASS | PASS | 4 доменные зависимости через constructor; get_logout_usecase собирает экземпляр, не выполняет его |
| IV. Transactional Consistency | PASS | PASS | общая cached session, factory commit/rollback, owner→session locks, refreshed validation, commit→ASGI start |
| V. Verification | PASS | PASS | семь уровней тестов, реальные PG races/commit и HTTPS proxy/browser; моки ограничены unit/API |
| VI. Documentation / Maintainability | PASS | PASS | существующие каталоги/суффиксы/70 chars; план будущей актуализации baseline без изменения согласованных V1/V2 |

Нарушений или новых исключений нет. Утверждённый отдельный Auth commit остаётся baseline,
но не используется Logout. Разрешение на реализацию этим документом не выдаётся.

## Project Structure

### Documentation (this feature)

```text
specs/001-session-logout/
├── spec.md                         # существующая specification, не меняется
├── checklists/requirements.md      # существующий checklist, не меняется
├── plan.md                         # этот план
├── research.md                     # решения, факты кода, альтернативы
├── data-model.md                   # доменные и локальные состояния
├── test-strategy.md                # 7 уровней, все C-01–C-27, deterministic schedules
├── quickstart.md                   # будущая воспроизводимая валидация
└── contracts/
    ├── logout-http.md              # API/proxy контракт и ошибки
    └── logout-ui.md                # UI/transport/coordinator interface
```

### Source Code (repository root)

Это **план будущих изменений**, не перечень уже созданных исходников. M — изменить,
A — добавить, reuse — использовать существующее без функционального расширения.

```text
backend/app/
├── domain/entities/session.py                         M close()
├── domain/repositories/{user,session}.py               reuse
├── application/usecases/logout.py                     A LogoutUseCase
├── infrastructure/database/session.py                 M safe failure logging
├── infrastructure/database/repositories/{user,session}.py reuse refresh/locks
├── infrastructure/security/{jwt,secret}.py             reuse
└── presentation/
    ├── logout_response.py                            A cookie/no-store policy helper
    ├── setup_exceptions.py                           M actual Logout errors/405/500
    └── api/
        ├── di/logout.py                              A constructor DI
        ├── di/clients/postgres.py                     reuse function scope
        ├── di/repositories/{user,session}.py           reuse shared session
        └── routes/auth/
            ├── logout.py                             A strict POST transport
            └── __init__.py                           M router registration

backend/tests/
├── unit/domain/test_session_close.py                  A
├── unit/application/test_logout.py                    A
├── api/test_logout.py                                A
├── api/test_repository_di.py                          M finalization regression
└── integration/database/
    ├── test_logout.py                                A real adapters + HTTP
    ├── test_logout_concurrency.py                        A deterministic races
    └── test_logout_commit.py                            A production factory + ASGI send

frontend/
├── src/
│   ├── api/logout.ts                                 A status-preserving transport
│   ├── auth/sessionState.ts                          A pure state/ownership rules
│   ├── auth/useAuthSession.ts                        A App-owned orchestration
│   ├── App.tsx                                      M auth/privacy boundary
│   ├── components/Header.tsx                        M action/pending/accessibility
│   ├── components/AccountModal.tsx                   M only if focus cleanup needs guard
│   ├── pages/AuthPage.tsx                           M shared login slot/notices/focus
│   └── pages/{AccountPage,AdminPage}.tsx              M generation/request tags/pending guard
├── server/{proxy,app,index}.mjs                       M Logout policy/PUBLIC_ORIGIN
├── tests/unit/                                      A transport/state/component tests
├── tests/server.test.mjs                            M real HTTP proxy cases
├── tests/browser/app.spec.ts                        M replace placeholder/regressions
├── tests/browser/logout.spec.ts                     A controlled UI event ordering
├── tests/browser/logout.https.spec.ts               A real proxy + HTTPS + API modes
├── vitest.config.ts                                 A unit/component setup
├── playwright.https.config.ts                       A isolated HTTPS project
└── package.json + package-lock.json                  M dev-only test dependencies/scripts
```

**Structure Decision**: сохранить `backend/app` слои и существующий React/static-server
layout, добавить только Logout usecase/route/DI, небольшой UI coordinator и проверочный tooling.
ORM/DTO/Request/Response не смешиваются. Для пустого запроса и204 не создаются искусственные
JSON Request/Response или application DTO. Регистрация/login не переопределяются.

### Backend design and transaction boundary

1. **Domain**: `close(now=None)` возвращает dataclasses.replace с closed_at=max(now,last_used_at),
   либо эквивалентное состояние при уже заданном closed_at; остальные поля immutable.
   Eligibility (`ensure_usable`) остаётся отдельной проверкой сценария, не HTTP-логикой entity.
2. **Application**: LogoutUseCase получает четыре существующих интерфейса; JWT decode через
   to_thread, предварительный get/ensure_usable и Argon2id verify до locks. Зафиксировать owner ID
   и проверенный hash только в локальном контексте. В общей транзакции lock user, затем
   refreshed lock session; сверить существование/владение/hash/closed_at/срок по свежему UTC.
   `is_active` не запрещает закрытие. Передать результат close в update; не читать global config,
   не вызывать authorize как запрет неактивному владельцу, Auth, use или commit.
3. **Repositories**: сохранить имеющийся populate_existing=True и FOR UPDATE; update уже
   защищает immutable owner/hash/created_at и flush. Новых методов/SQL обходов не требуется.
4. **Presentation**: валидирующая dependency читает raw headers, затем query/raw body,
   затем cookie. Плохой CSRF не запускает JSON parsing/auth session reads; форма проверяется
   до cookie. UseCase DI собирается без business I/O; маршрут вызывает именованный logout.
   OpenAPI: auth_logout/auth, cookie security без ordinary Auth DI, required CSRF,
   отсутствующее requestBody, response204 без content; ошибки и headers описаны явно.
5. **Shared factory**: обычные repo DI используют одну PostgresSessionDI(scope=function).
   Фабрика владеет commit/rollback; AuthPostgresSessionDI/AuthCommitDI сюда не подключаются.

#### Создание ответа не равно отправке

Фактическая последовательность текущих FastAPI/Starlette (см. research R-03):

```text
handler/usecase → flush → создать Response(204, deletion, no-store)
  → выход function dependency → SessionController.commit()
    ├── success → выйти function exit stack → Response.__call__ → http.response.start/body
    └── failure → отбросить подготовленный Response → exception mapper
                    → actual error(no-store, без session Set-Cookie) → http.response.start
```

Нельзя отправлять204, удаление cookie или stream до finalization; также нельзя «чинить»
ошибку через headers на уже подготовленном Response. Cookie/no-store helper используется
на фактическом доменном mapper-ответе, HTTPException405 и контролируемом unexpected500.
Выбор Logout-401 опирается на AuthenticationException и отмеченный Presentation-контекст
проверки credential, не просто любой status401. На401 применяется удаление без нового close.
На400/403/405/500/503 ошибки подготовленные success cookies не копируются.
Для исключений вне handled mapper существующий ServerErrorMiddleware должен получить
безопасный Logout500 handler; нельзя полагаться только на внутренний user middleware.
HEAD отдаётся без body,405 сохраняет Allow: POST.

SessionController сохраняет управление rollback и исходный безопасный domain mapping.
Логи ошибки содержат только безопасную категорию/стадию, не exception/SQL/secret;
потеря подтверждения commit не называется доказанным откатом. Не добавляются retries,
новый DB timeout или обещание отмены уже аутентифицированной бизнес-операции.

### Frontend and proxy integration

- **Transport**: отдельный logout helper, POST без тела/query, CSRF1, same-origin/no-store.
  Не переиспользовать generic response.ok/поисковую403 ошибку. Достоверный status сохраняется
  независимо от optional JSON; только204→closed,401→invalid, остальные→safe failure.
  Бюджет20s охватывает fetch/потребление ответа; malformed JSON не стирает известный401.
- **Coordinator**: синхронный ref-owned auth slot, отображаемый через state; generation
  отдельно от operation/attempt IDs. Login захватывает slot до fetch и держит через me.
  Clear/replacement меняет generation, но не снимает slot ожидающего Logout. Изменения UI
  проверяют generation/attempt; release finalizer проверяет owner отдельно и может освободить
  свой slot после смены generation, но никогда чужой. Identity refs меняются синхронно;
  React state — их отображение, а не единственная защита между render.
  Timeout делает попытку terminal до release; старый Promise не может завершить новую попытку.
- **App/pages**: account-based render boundary и generation-keyed protected subtree очищают
  search/page/card/errors при смене аккаунта. Tagged startup/account/search requests не применяют
  старые success/error/401/finally. Во время pending не запускать новые защищённые запросы,
  включая route effects после hash navigation; уже запущенные могут дать актуальный401.
- **Header/AuthPage**: Header — presentation для callback/pending; фокусируемый trigger с guard
  и aria-disabled, без действий pending. Progress вне dropdown; ошибка alert с явным repeat/dismiss.
  AuthPage принимает shared busy, итог/ручное закрытие; focus heading после перехода,
  login submit защищён и синхронно, и в UI. Проверить modal-unmount focus cleanup.
- **Proxy**: точный Logout path распознаётся до общей allowlist/body buffer.405 без upstream;
  POST проверяет trusted PUBLIC_ORIGIN, CSRF, отсутствие query/первого body byte; плохой вход
  отклоняется без накопления всего payload, не silently drops body и не даёт общий413.
  Валидный запрос передаёт исходные Cookie/CSRF; backend повторяет проверки независимо.
- **Origin config**: явный PUBLIC_ORIGIN из доверенной startup configuration, нормализация
  scheme/hostname/effective port. Пример HTTPS localhost:3443 в quickstart; произвольные
  клиентские Host/X-Forwarded-Proto не определяют доверенную схему. Внешняя CORS-схема не вводится.
- **Proxy response**: manual redirect, buffer body до отправки status/cookies внутри15s;
  timeout на header/body этапе→504, другой upstream сбой/3xx→502 без чужой redirect cookie.
  Сохранять status/Set-Cookie/Cache-Control/Allow;204/HEAD без body. Registration303→201
  остаётся отдельным baseline. Автоповторов нет.
- **Accepted boundary**: generation защищает UI, не браузерный Set-Cookie. Позднее удаление
  может затронуть новую cookie другой вкладки или той же после timeout; новая серверная
  сессия не закрывается. Нет глобального lock, polling или гарантированного cancellation.

### Verification and delivery gates

Полная стратегия, paths будущих проверок, детерминированные расписания и матрица27/27 —
[test-strategy.md](test-strategy.md). Валидационный запуск — [quickstart.md](quickstart.md).

Готовность будущей реализации проверяется по семи уровням: Domain unit → Application unit →
API → PostgreSQL integration → frontend unit → proxy integration → browser E2E.
Каждый уровень проверяет собственные гарантии, не заменяет другой. Existing regression suites
должны сохранять auth renewal on403, login/register redirect и account-search baseline.
Обязательны commit-before-ASGI-start с production factory, real-PG refresh/lock races,
реальный HTTPS Set-Cookie и управляемые stale-event/timeout сценарии.

После отдельного разрешения реализации актуализируются `docs/endpoints/auth.md`,
`docs/auth.md`, `docs/entities/{session,user}.md`, применимые repository/security docs,
OpenAPI и `frontend/README.md` (ссылка на R-03, exception ADR-07, HTTPS/15–20s/cookie-race).
В этой задаче они не меняются; V1/V2/REVIEW/CONTRACT и spec.md сохраняются.

## Complexity Tracking

Нарушений Constitution нет; таблица исключений не требуется. Новая сложность ограничена
одним usecase/route, политикой фактического ответа и локальным координатором UI.
Обоснования и отклонённые альтернативы записаны в [research.md](research.md).
