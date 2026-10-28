# AnimeMap API — backend

## Запуск всего окружения

Создать `backend/.env` по `.env.example` и заполнить `JWT_PRIVATE_KEY` по инструкции [security.md](../docs/security.md). Из `backend/`:

```bash
docker compose up --build --wait
docker compose ps --all
```

Запускаются PostgreSQL, Redis, миграции и API. Backend ждёт успешного завершения Alembic; адрес — `http://localhost:8080`, Swagger — `/docs`, healthcheck — `/ping`. При необходимости порт меняется через `BACKEND_PORT`.

Из `lab/` передавать `--env-file backend/.env` в Compose-команды. Для БД/Redis предусмотрены dev-значения; ключ JWT задаётся явно. Подробности — в [docs/deployment.md](../docs/deployment.md).

Лимит Python-строки — 70 символов, включая отступ. Проверка:

```bash
uvx ruff check app tests migrations run.py
```

## Миграции PostgreSQL

Требуются Python 3.14+, `uv` и отдельная PostgreSQL для разработки.

1. Создать `.env` по образцу `.env.example`, указав параметры своей БД.
2. Установить зависимости и применить миграции из каталога `backend/`:

```bash
uv sync --group migrations --group service --group tests
uv run --group migrations alembic upgrade head
uv run --group migrations alembic check
```

Настройки читаются из env или `.env`. Redis для миграций не запускается и не используется, но его поля пока обязательны в общей `AppConfig`; пример содержит необходимые значения.

Первая миграция создаёт `users`, `credentials`, `sessions`, ограничения и частичные индексы, а также bootstrap-аккаунт:

- username: `root`;
- email: `root@example.com`;
- начальный пароль: `root`;
- роль: `admin` (`3`), аккаунт активен.

Пароль хранится только в виде Argon2id-хэша в текущем credential. Bootstrap выполняется один раз миграцией: повторный `upgrade head` и перезапуск приложения не сбрасывают пароль, роль или профиль. Сценарии входа, регистрации и проверки сессии реализованы через EdDSA JWT и Argon2id.

## Presentation: вход и регистрация

Документация групп ручек: [auth](../docs/endpoints/auth.md) и [account](../docs/endpoints/account.md). Она обновляется при добавлении или изменении endpoint.

- `POST /v1/auth/login`: email и пароль → `200` с `{}` и `Set-Cookie: session_token=<jwt>; Secure; HttpOnly; SameSite=Lax; Path=/`. JWT и срок сессии не передаются в JSON; браузер прикладывает cookie автоматически по HTTPS.
- `POST /v1/auth/register`: email, username, пароль и необязательный display_name → `303` с `Location` на login. API-клиент обрабатывает редирект без автоматического GET; следующий вход выполняется отдельным POST.
- Запросы — JSON, email проверяется `pydantic.EmailStr`. Внешние схемы `LoginRequest`, `RegisterRequest`, `LoginResponse` расположены в `api/schemas/requests/` и `responses/`. Суффикс `DTO` используется только для внутренних объектов приложения. Полный контракт — в [`docs/auth.md`](../docs/auth.md).
- В `api/di/` функция `get_<name>_usecase` возвращает UseCase, а алиас `<Name>UseCaseDI = Annotated[UseCase, Depends(provider)]` используется в сигнатуре ручки. В presentation вызываются именованные методы `login`/`register`. `AuthUseCaseDI` возвращает пользователя после вызова `authenticate`. Порты и настройки EdDSA/Argon2id — в [security.md](../docs/security.md). API-тесты работают без БД и env; интеграционные тесты проверяют реальные адаптеры.

```bash
uv run --group tests pytest tests/api
docker build --target api-tests -f Dockerfile.tests -t animemap-api-tests .
docker run --rm animemap-api-tests
```

## Presentation: аккаунты

- `GET /v1/account/me` — текущий аккаунт из auth DI, доступен любому активному аутентифицированному пользователю.
- `GET /v1/account/find/{username_prefix}?limit=20&offset=0` — страница совпадений по префиксу username, доступен moderator/admin. Роль проверяется до поиска, обычный user получает `403`. Limit ограничен диапазоном 1–100, offset — 0–10 000; оба поля принимает общий `PaginationRequest` через `Annotated[PaginationRequest, Query()]`.
- Роли возвращаются строками; JWT, хэши и сроки сессий в ответ не попадают.
- `FindAccountsUseCase` получает доменный `UserRepository` извне через конструктор и DI. SQLAlchemy-адаптер возвращает страницу `UserEntity`; UseCase преобразует сущности в DTO. Auth проверяет JWT, Argon2id-секрет и актуальное состояние сессии в PostgreSQL.

## Репозитории и DI

Реализованы `SQLAlchemyUserRepositoryAdapter`, `SQLAlchemyCredentialRepositoryAdapter`, `SQLAlchemySessionRepositoryAdapter`. Каждый получает AsyncSession извне, имеет `_to_orm`/`_from_orm`, выполняет явные async ORM-запросы и flush после записи. Commit/rollback выполняет SessionController при выходе из контекста; в адаптерах commit отсутствует.

DI разделена на `clients`, `repositories`, `entities`, `ports`; фабрики UseCase объединяют зависимости. Репозитории бизнес-сценария используют общую сессию с завершением транзакции до отправки ответа. Auth использует отдельную сессию и фиксирует продление до возврата пользователя, независимо от дальнейшего 403/rollback.

Контракты CRUD, блокировки и транзакции — в [docs/repositories.md](../docs/repositories.md).

## Ошибки и границы application

Общие ошибки всех слоёв находятся в `domain/exceptions/entities/`, наследуются от `BaseDomainException` и передают контекст в `details`. Mapper `presentation/setup_exceptions.py` формирует `error/message/details`; валидация запросов возвращает `400`. Полный контракт — в [docs/errors.md](../docs/errors.md).

В application нет портов и собственных репозиторных интерфейсов. Поиск и другие операции с сущностями выполняются через доменные репозитории. Application service допускается только по прямому указанию пользователя; по умолчанию прикладная логика находится в UseCase.

## Генерация следующей миграции

Каждая ORM-модель находится в отдельном файле в `app/infrastructure/database/models/` и импортируется в `models/__init__.py`, чтобы Alembic видел её в `Base.metadata`.

```bash
uv run --group migrations alembic revision --autogenerate -m "describe schema change"
uv run --group migrations alembic upgrade head
uv run --group migrations alembic check
```

Автогенерированную миграцию необходимо просмотреть: Alembic не генерирует bootstrap-данные и не гарантирует обнаружение изменений CHECK-ограничений. Условия частичных индексов задаются через `postgresql_where`, а не только комментариями из DBML.

## Unit-проверки схем БД

Группа `tests` включает зависимости сервиса, миграций и pytest. Для запуска тестов достаточно одной группы:

```bash
uv sync --group tests
uv run --group tests pytest tests/unit/database
```

Проверки находятся в `tests/unit/database/`: отдельные файлы для User, Credential, Session и общих правил схемы. Они не требуют PostgreSQL, Redis, `.env` или `TEST_DATABASE_URL`: проверяются SQLAlchemy metadata, компиляция PostgreSQL DDL, частичные индексы, ключи, обязательность полей, CHECK-ограничения, часовые пояса и ORM-связи.

Для запуска в Docker:

```bash
docker build --target unit-tests -f Dockerfile.tests -t animemap-unit-tests .
docker run --rm animemap-unit-tests
```

## Интеграционные проверки моделей

Использовать отдельную тестовую БД, на которую предварительно применена первая миграция. Тесты откатывают свои изменения, но ожидают исходный bootstrap-аккаунт.

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:password@127.0.0.1:5432/animemap_test \
  uv run --group tests pytest tests/integration/database
```

Без `TEST_DATABASE_URL` интеграционные тесты пропускаются. Проверяются bootstrap, схема, CRUD трёх репозиториев, буквальный поиск с пагинацией, история паролей, каскадное удаление, маппинг доменных ошибок, отсутствие commit в адаптерах и commit/rollback фабрики. Отдельно проверяется HTTP-поиск через реальные DI/UseCase/ORM/PostgreSQL с подменой аутентификации.

### Запуск интеграционных тестов в Docker

Target `integration-tests` содержит приложение, миграции Alembic и `tests/integration/`. БД запускается отдельно. В `.env.test` задаются поля из `.env.example` для тестовой БД и `TEST_DATABASE_URL`, указывающий на ту же БД. Адрес PostgreSQL должен быть доступен из контейнера: например, `host.docker.internal` для БД на хосте Docker Desktop или имя контейнера в общей Docker-сети.

```bash
docker build --target integration-tests -f Dockerfile.tests -t animemap-integration-tests .
docker run --rm --env-file .env.test --entrypoint alembic animemap-integration-tests upgrade head
docker run --rm --env-file .env.test animemap-integration-tests
```

Для БД в пользовательской Docker-сети добавить `--network <имя-сети>` к обоим `docker run`. Миграция применяется отдельной командой; запуск pytest сам схему не меняет. JUnit-отчёт сохраняется в `/reports/report.xml`; для сохранения на хосте можно смонтировать каталог в `/reports`.

На временной БД также проверяется цикл `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head`. Откат первой миграции удаляет все три таблицы вместе с их данными.
