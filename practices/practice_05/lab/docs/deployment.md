# Локальный запуск через Docker Compose

Основная конфигурация — `backend/docker-compose.yml`, реализованная по исходному шаблону. Корневой `docker-compose.yml` включает её через Compose include; команды можно выполнять как из каталога `lab/`, так и из `backend/`.

## Запуск

```bash
docker compose --env-file backend/.env up --build --wait
docker compose ps --all
```

API доступен на `http://localhost:8080`, OpenAPI UI — `/docs`, проверка HTTP-процесса — `/ping`.

Другой порт задаётся переменной окружения:

```bash
BACKEND_PORT=8082 docker compose up --build --wait
```

Перед запуском создать `backend/.env` по образцу `.env.example`, заполнить `JWT_PRIVATE_KEY` (base64 PEM Ed25519). Генерация ключа и параметры Argon2id описаны в [security.md](security.md). Для БД и Redis предусмотрены dev-значения по умолчанию; внутри контейнеров POSTGRES_HOST/REDIS_HOST переопределяются на `database`/`cache`. Из `backend/` достаточно `docker compose up --build --wait`; из `lab/` передавать `--env-file backend/.env` и в последующие Compose-команды либо экспортировать переменные окружения.

## Состав и порядок запуска

| Сервис | Назначение | Готовность |
| --- | --- | --- |
| `database` | PostgreSQL 18 Alpine | `pg_isready`, постоянный volume pg_data |
| `cache` | Redis 7 Alpine с паролем | `redis-cli ping` с REDISCLI_AUTH |
| `migrations` | `alembic upgrade head` | Ждёт здоровые database/cache; успешно завершается |
| `backend` | `uvicorn run:service` на 8080 | Стартует после миграций; HTTP healthcheck `/ping` |

Внешний порт публикует только backend. PostgreSQL и Redis доступны контейнерам в общей сети backend-private, без публикации портов БД/кэша на хост.

Переменные пользователя/пароля/имени БД передаются через environment; значения по умолчанию — `animemap`. Redis также использует dev-пароль `animemap`. Один и тот же пароль подставляется в Redis, его healthcheck и конфигурацию приложения.

PostgreSQL 18 хранит данные в именованном volume, смонтированном в `/var/lib/postgresql`. Повторный запуск использует существующие данные; Alembic не создаёт root повторно и не сбрасывает его пароль.

Bootstrap после первой миграции: username `root`, email `root@example.com`, начальный пароль `root`, роль admin. Репозитории, поиск, вход, регистрация и JWT-аутентификация реализованы согласно [контракту auth](endpoints/auth.md).

При старте lifespan проверяет Ed25519-ключ и подключения к PostgreSQL/Redis; при остановке освобождает оба клиента. Bootstrap выполняет миграция. В Compose TLS не завершается; для работы браузерной Secure cookie нужен HTTPS, в целевом окружении — Nginx.

## Диагностика

```bash
docker compose logs backend migrations
docker compose exec database psql -U animemap -d animemap
docker compose exec cache redis-cli ping
docker compose run --rm migrations alembic check
```

Healthcheck Redis использует REDISCLI_AUTH из environment, поэтому CLI в контейнере также аутентифицируется автоматически. При изменении имени пользователя/БД соответствующие значения нужно подставить в команду psql.

`migrations` в состоянии Exited (0) — ожидаемый результат успешного применения схемы. Backend ждёт именно `service_completed_successfully`, поэтому при ошибке миграции не стартует.

## Остановка

```bash
docker compose down
```

Volume PostgreSQL сохраняется. Для удаления данных отдельного тестового проекта:

```bash
docker compose -p animemap-compose-check down --volumes
```

## Проверки

Тестовые образы остаются в `Dockerfile.tests` с target `unit-tests`, `api-tests`, `integration-tests`. После запуска Compose интеграционные тесты можно подключить к той же сети с TEST_DATABASE_URL, указывающим на отдельную тестовую БД; инструкции — в backend/README.md.
