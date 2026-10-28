# Auth — вход и регистрация

Префикс группы: `/v1/auth`. Запросы — JSON. Подробный жизненный цикл JWT и сессии описан в [docs/auth.md](../auth.md).

| Метод и путь | Назначение | Кто может пользоваться |
| --- | --- | --- |
| `POST /v1/auth/login` | Войти и получить сессионную HttpOnly cookie | Не требует существующей сессии; вход разрешён активному пользователю с текущим паролем |
| `POST /v1/auth/register` | Зарегистрировать обычного пользователя и перейти к входу | Публичная ручка, аутентификация не требуется |

## POST /v1/auth/login

Тело (`LoginRequest`):

```json
{
  "email": "root@example.com",
  "password": "root"
}
```

- Email обязателен, нормализуется через `trim + lowercase`, проверяется `pydantic.EmailStr`, не длиннее 254 символов.
- Пароль — непустая строка; пробелы не удаляются и регистр не меняется.
- Дополнительные поля запрещены. Вход по username не используется: username пока не уникален.

При успехе — `200 OK`, тело `LoginResponse` — `{}`. Сервер устанавливает:

```http
Set-Cookie: session_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/
Cache-Control: no-store
```

Cookie автоматически отправляется браузером по HTTPS. JWT не передаётся в JSON или bearer-заголовке. Срок сессии клиенту не возвращается. У cookie нет фиксированного `Expires/Max-Age`; действительность определяется серверной сессией со скользящим сроком.

Ошибки: `401` — неверные данные/неактивный пользователь; `400` — ошибка схемы или повреждённый сохранённый хэш; `503` — недоступность инфраструктуры. При неуспехе новая cookie не устанавливается. Отсутствие пользователя/текущего credential, неверный пароль и блокировка дают общий `AuthenticationException` с `details.reason = invalid_credentials`.

## POST /v1/auth/register

Тело (`RegisterRequest`):

```json
{
  "email": "anime-fan@example.com",
  "username": "anime-fan",
  "password": "user password",
  "display_name": "Anime Fan"
}
```

- Email и пароль валидируются как при входе.
- Username обязателен: 1–100 символов после trim; уникальность не предполагается.
- Display name необязателен (`null` или отсутствие поля); если указан — 1–100 символов после trim.
- Клиент не задаёт ID, роль, активность, хэши или временные метки. Обычный пользователь создаётся с ролью user; bootstrap root — отдельное исключение.

После успешного завершения регистрации — `303 See Other` с `Location` на именованный login-маршрут, например `https://api.example.com/v1/auth/login`. Тело пустое, cookie не устанавливается, автоматический вход не выполняется.

REST-клиент обрабатывает `303/Location` как переход к шагу входа. Автоматическое следование редиректу выполняет GET, а login принимает POST: нужно отключить автоматическое следование и отправить отдельный POST после ввода учётных данных. Страницы входа в бэкенде нет.

Ошибки: `409` — email уже зарегистрирован (`AlreadyExistsException` с `details.entity = user`, `details.field = email`); `400` — ошибка схемы; `503` — недоступность инфраструктуры. При ошибке редиректа нет. Пользователь и текущий credential создаются в одной транзакции.

## Дополнительная информация

Все ошибки используют единый [контракт `error/message/details`](../errors.md) и централизованный mapper `presentation/setup_exceptions.py`. HTTP-статусы задаются только presentation, а не UseCase, DI или инфраструктурой.

- Оба endpoint используют `Request.to_dto()`. Login создаёт ответ через `LoginResponse.from_dto()`; при регистрации возвращается `RedirectResponse` без схемы JSON-тела.
- DI возвращает UseCase, presentation вызывает именованные методы `login`/`register`. Application DTO не являются HTTP-схемами.
- Репозитории внедряются через конструкторы: login получает UserRepository, CredentialRepository, SessionRepository; register — UserRepository и CredentialRepository. Адаптеры используют общую сессию с commit/rollback в фабрике. Login дополнительно получает JwtProviderPort и SecretManagerPort, register — SecretManagerPort. Используются EdDSA/Ed25519 и Argon2id; настройки — в [security.md](../security.md).
- UseCase наследуют `BaseUseCase` с уровнем USER по умолчанию. Login/register публичны: `authorize(user)` не вызывается перед входом или созданием пользователя, когда аутентифицированного пользователя ещё нет.
- Реальные сценарии входа, регистрации и проверки сессии подключены. API-тесты проверяют контракты с подменой зависимостей; интеграционные тесты выполняют реальный цикл регистрации, входа, `/account/me` и проверки прав с PostgreSQL и криптографическими адаптерами.
- Bootstrap на новой БД: username `root`, email `root@example.com`, начальный пароль `root`, роль admin. Специального обхода аутентификации для него нет.
