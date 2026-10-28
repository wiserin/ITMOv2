# Репозитории пользователей, паролей и сессий

Интерфейсы находятся в `backend/app/domain/repositories/`, реализации — в `app/infrastructure/database/repositories/`. Репозитории возвращают доменные сущности, не ORM и не application DTO.

| Интерфейс | Реализация | Сущность |
| --- | --- | --- |
| `UserRepository` | `SQLAlchemyUserRepositoryAdapter` | `UserEntity` |
| `CredentialRepository` | `SQLAlchemyCredentialRepositoryAdapter` | `CredentialEntity` |
| `SessionRepository` | `SQLAlchemySessionRepositoryAdapter` | `SessionEntity` |

## Общий контракт

- Адаптер получает `AsyncSession` через конструктор: `SQLAlchemyUserRepositoryAdapter(session=session)`.
- `create(entity)`, `update(entity)`, `delete(entity)` принимают доменную сущность и возвращают доменную сущность. Delete возвращает снимок удалённой записи.
- У каждого адаптера есть `_to_orm()` и `_from_orm()`. UUIDv4 уже существует в domain до обращения к БД; flush не используется для генерации ID.
- Все запросы строятся через SQLAlchemy ORM и выполняются явно через await. Relationships настроены с `lazy="raise"`; мапперы работают только со скалярными полями.
- Update/delete сначала явно читают запись с `SELECT FOR UPDATE`. В чтениях блокировку можно включить аргументом `for_update=True`.
- Отсутствующая одиночная запись вызывает `NotFoundException` с сущностью/селектором в `details`. Пустые списки возвращаются как `()`.
- Неизменяемые поля проверяются при update: время создания пользователя; владелец, хэш и время создания credential; владелец, секрет, его хэш и время создания сессии. Попытка изменить их — общий `ConflictException`, в details передаются только названия полей.
- Адаптеры не выполняют commit/rollback и не владеют сессией. Все записи завершаются `await session.flush()` и возвращают актуальное ORM-представление в виде domain entity.

## UserRepository

- `create(entity)` — добавить пользователя.
- `get_by_id(user_id, for_update=False)` — получить по UUID.
- `get_by_email(email, for_update=False)` — получить по каноническому email. Нормализация выполняется до обращения к репозиторию.
- `find_by_username_prefix(prefix, limit=..., offset=...)` — буквальный, регистрозависимый префикс; SQL wildcard `%`, `_` и escape-символ экранируются ORM. Сортировка по username, затем UUID; limit/offset применяются в PostgreSQL.
- `update(entity)` — обновить профиль, роль, активность и updated_at.
- `delete(entity)` — удалить пользователя. Зависимые credentials/sessions удаляются через ON DELETE CASCADE.

## CredentialRepository

- `create(entity)` — добавить хэш пароля, сохранив историю.
- `get_by_id(credential_id, for_update=False)` — получить конкретную запись.
- `get_current_by_user_id(user_id, for_update=False)` — получить текущий credential; при отсутствии — NotFoundException.
- `list_by_user_id(user_id, limit=..., offset=...)` — страница истории по created_at, затем UUID.
- `update(entity)` — изменить признак текущего пароля без перезаписи старого хэша.
- `delete(entity)` — удалить выбранную запись.

Единственность текущего пароля обеспечивает частичный уникальный индекс. Для смены пароля UseCase сначала блокирует владельца через UserRepository.get_by_id(..., for_update=True), деактивирует старую запись (с flush), затем создаёт новую в той же сессии. Репозиторий сам не разделяет это на транзакции и не коммитит промежуточное состояние.

## SessionRepository

- `create(entity)` — сохранить сессию и оба поля секрета согласно MVP.
- `get_by_id(session_id, for_update=False)` — прочитать сессию для проверки/изменения.
- `list_by_user_id(user_id, limit=..., offset=...)` — страница сессий по created_at, затем UUID.
- `update(entity)` — сохранить last_used_at, expires_at и closed_at, не изменяя секрет и владельца.
- `delete(entity)` — физически удалить запись.

Проверка действительности JWT, активности владельца, скользящего срока и допустимости продления/закрытия остаётся обязанностью domain/UseCase. Репозиторий выполняет сохранение; он не хэширует секреты и не подписывает JWT.

## Владение транзакцией

`SessionController.session()` (`infrastructure/database/session.py`) создаёт AsyncSession, выполняет commit при нормальном выходе и rollback при ошибке. `factory.py` конфигурирует экземпляр контроллера из настроек приложения.

Все репозитории запроса получают один и тот же PostgresSessionDI. Функциональный scope yield-dependency завершает транзакцию до отправки ответа; ошибка commit может быть преобразована общим HTTP mapper вместо уже отправленного успеха.

Ошибки драйвера переводятся в [общие доменные ошибки](errors.md). Адаптер не пытается продолжать транзакцию после неудачного flush. Для восстановления нужен rollback владельца транзакции либо заранее открытый вызывающим кодом savepoint. Редкий самостоятельный commit UseCase должен быть явно обоснован и не переносится в адаптер.

## Структура DI

```text
presentation/api/di/
├── clients/
│   ├── postgres.py     # get_postgres_session + PostgresSessionDI
│   └── redis.py        # get_redis_client + RedisClientDI
├── repositories/
│   ├── user.py
│   ├── credential.py
│   └── session.py
├── entities/
│   └── user.py         # текущий пользователь и AuthUseCaseDI
├── ports/              # DI внешних портов по мере их реализации
├── login.py
├── register.py
├── auth.py
└── find_accounts.py
```

Каждый провайдер возвращает конкретный объект с аннотацией интерфейса; рядом объявлен `Annotated[..., Depends(provider)]`-алиас. DI UseCase перечисляет необходимые репозитории/порты в сигнатуре и передаёт их в конструктор. Login получает три репозитория, register — пользователей и credentials, auth — пользователей и сессий, find_accounts — пользователей.

Repository DI и работа с PostgreSQL реализованы. Бизнес-методы login/register/auth пока возвращают доменный NotImplementedException; их реализация — следующий отдельный этап. Поиск уже использует реальный ORM-репозиторий.
