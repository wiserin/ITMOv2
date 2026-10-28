# AnimeMap API — backend

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
- email: `root@animemap.local`;
- начальный пароль: `root`;
- роль: `admin` (`3`), аккаунт активен.

Пароль хранится только в виде Argon2id-хэша в текущем credential. Bootstrap выполняется один раз миграцией: повторный `upgrade head` и перезапуск приложения не сбрасывают пароль, роль или профиль. Вход через API ещё не реализован.

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

Без `TEST_DATABASE_URL` интеграционные тесты пропускаются. Проверяются bootstrap-хэш, связи, каскадное удаление, обязательность username, ограничения сессий и единственность текущего пароля при сохранении истории.

### Запуск интеграционных тестов в Docker

Target `integration-tests` содержит приложение, миграции Alembic и `tests/integration/`. БД запускается отдельно. В `.env.test` задаются поля из `.env.example` для тестовой БД и `TEST_DATABASE_URL`, указывающий на ту же БД. Адрес PostgreSQL должен быть доступен из контейнера: например, `host.docker.internal` для БД на хосте Docker Desktop или имя контейнера в общей Docker-сети.

```bash
docker build --target integration-tests -f Dockerfile.tests -t animemap-integration-tests .
docker run --rm --env-file .env.test --entrypoint alembic animemap-integration-tests upgrade head
docker run --rm --env-file .env.test animemap-integration-tests
```

Для БД в пользовательской Docker-сети добавить `--network <имя-сети>` к обоим `docker run`. Миграция применяется отдельной командой; запуск pytest сам схему не меняет. JUnit-отчёт сохраняется в `/reports/report.xml`; для сохранения на хосте можно смонтировать каталог в `/reports`.

На временной БД также проверяется цикл `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head`. Откат первой миграции удаляет все три таблицы вместе с их данными.
