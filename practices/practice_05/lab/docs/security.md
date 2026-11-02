# JWT и секреты

## Порты и адаптеры

- `domain/ports/jwt.py`: `JwtProviderPort`, синхронные `encode` и `decode` над `SessionTokenEntity` и строкой JWT.
- `domain/ports/secret.py`: `SecretManagerPort`, асинхронные `hash_secret`, `verify_secret` и синхронный `generate_random_secret`.
- `infrastructure/security/jwt.py`: `EdDSAJwtProviderPortAdapter`, PyJWT и cryptography, подпись **EdDSA / Ed25519**.
- `infrastructure/security/secret.py`: `Argon2SecretManagerPortAdapter`, **Argon2id**, отдельная соль для каждого хэша. Хэширование и verify выполняются через `asyncio.to_thread`, вне event loop.
- DI адаптеров — `presentation/api/di/ports/`. Экземпляры кэшируются; ключ подписи проверяется при старте приложения. UseCase получают интерфейсы, а не создают адаптеры.

Синхронные `encode`, `decode` и `generate_random_secret` вызываются
из async UseCase через `await asyncio.to_thread(...)`. Загрузка и
проверка PEM-ключа при старте также вынесена в `asyncio.to_thread`.
PostgreSQL (`asyncpg` / AsyncSession) и Redis (`redis.asyncio`)
выполняют I/O асинхронно и не передаются в поток.

В SessionEntity, ORM и БД хранится только `secret_hash`.
Открытый секрет нужен для создания JWT при входе и для проверки
предъявленного JWT; репозиторий его не принимает и не возвращает.
Единственная стартовая миграция `43b8dfef97c1` сразу создаёт
`sessions` без открытого секрета, только с `secret_hash`.

## JWT

Payload содержит только `jti` (UUIDv4 сессии), `secret` (непустая строка) и `iat` (целочисленный NumericDate). Нет `exp`, роли, ID пользователя и access/refresh-пары. Неожиданные поля отклоняются. Подпись проверяется только EdDSA с публичным ключом, полученным из настроенного приватного ключа. Недействительные подпись, структура и значения дают `AuthenticationException` → `401`.

`JWT_PRIVATE_KEY` — base64 от незашифрованного PEM приватного Ed25519-ключа (PKCS8). Пустой, повреждённый ключ или ключ другого типа отклоняется. Автоматическая генерация ключа при старте не выполняется: рестарт не должен менять доверенный ключ.

Генерация из `backend/` после установки service-зависимостей:

```bash
uv run --group service python -c 'import base64; from cryptography.hazmat.primitives import serialization as s; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as K; print(base64.b64encode(K.generate().private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption())).decode())'
```

Значение сохранить в `backend/.env` как `JWT_PRIVATE_KEY=...`. Для Compose из `lab/` использовать `docker compose --env-file backend/.env up --build --wait`; из `backend/` `.env` подхватывается автоматически.

## Argon2id и настройки

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `SESSION_IDLE_TIMEOUT_MINUTES` | 30 | Положительный интервал неактивности в минутах |
| `ARGON2_TIME_COST` | 3 | Число проходов |
| `ARGON2_MEMORY_COST` | 65536 | Память на операцию, KiB |
| `ARGON2_PARALLELISM` | 1 | Параллелизм |
| `ARGON2_HASH_LEN` | 32 | Длина хэша, байт |
| `ARGON2_SALT_LEN` | 16 | Длина соли, байт |

Настройки стоимости положительны; memory ≥ 8 × parallelism, hash_len ≥ 4, salt_len ≥ 8. Приведённые значения — начальные настраиваемые значения MVP; нагрузочные измерения пока не выполнены. Закодированный Argon2-хэш содержит собственные параметры, поэтому ранее созданные credentials, включая bootstrap, продолжают проверяться.

Несовпадение секрета даёт `AuthenticationException` → `401`; повреждённый сохранённый хэш — `DataFormatException` → `400`; ошибка выполнения хэширования — `ServiceUnavailableException` → `503`. Сырые секреты и хэши не включаются в details. Генератор использует `secrets.token_urlsafe` и минимум 32 случайных байта. Пароли передаются без trim и изменения регистра.

## Использование в сценариях

- Register: хэширование пароля, создание пользователя с ролью USER и текущего credential в общей транзакции. Конфликт email → `409`; ошибка создания credential откатывает пользователя.
- Login: проверка активного пользователя и текущего пароля, генерация/хэширование секрета, повторная проверка пользователя и текущего credential под блокировками, создание сессии и подпись JWT. Commit общей транзакции завершается до отправки cookie. Неверный пароль, отсутствие пользователя/credential и блокировка дают единый `401 invalid_credentials`.
- Auth: проверка JWT и сессии, Argon2id verify, блокировка пользователя, затем сессии, проверка активности владельца. Доменная команда `session.use(idle_timeout=...)` проверяет актуальный срок/закрытие и возвращает новую сессию с обновлёнными временными метками; UseCase сохраняет её через репозиторий и выполняет отдельный commit. Закрытая/истёкшая сессия не возобновляется; время использования не уменьшается.

Auth DI использует отдельную AsyncSession (`AuthPostgresSessionDI`). В AuthUseCase внедряется callback commit, реализованный `SessionController.commit`; это обоснованное исключение из обычного владения commit фабрикой. Продление фиксируется до возврата пользователя и сохраняется при последующем `403` или откате бизнес-транзакции. Репозитории не коммитят. Login и смена пароля блокируют владельца до зависимых записей; закрытие сессии должно соблюдать совместимый порядок блокировок.

HTTP-ручка logout и сценарии смены/сброса пароля в текущий набор endpoint не добавлены; их поведение описано как последующее развитие в `auth.md`.
