# Именование и dependency injection

## Суффиксы типов

| Тип | Обязательный суффикс | Пример |
| --- | --- | --- |
| Внутренний DTO приложения | `DTO` | `LoginDTO`, `LoginResultDTO`, `UserDTO` |
| Внешняя Pydantic-схема запроса | `Request` | `LoginRequest`, `RegisterRequest` |
| Внешняя Pydantic-схема ответа | `Response` | `LoginResponse`, `ErrorResponse` |
| Доменная сущность | `Entity` | `UserEntity`, `CredentialEntity`, `SessionEntity` |
| Прикладной сценарий | `UseCase` | `LoginUseCase`, `RegisterUseCase`, `AuthUseCase` |
| Репозиторий (контракт) | `Repository` | `UserRepository` |
| Адаптер репозитория | `RepositoryAdapter` | `SQLAlchemyUserRepositoryAdapter` |
| Порт | `Port` | `PasswordHasherPort` |
| Адаптер порта | `PortAdapter` | `Argon2PasswordHasherPortAdapter` |
| DI type alias | `UseCaseDI` | `LoginUseCaseDI`, `RegisterUseCaseDI`, `AuthUseCaseDI` |
| Функция сборки UseCase | `get_<name>_usecase` | `get_login_usecase`, `get_register_usecase` |

ORM-модели не являются доменными сущностями и сохраняют суффикс `ORM`: `UserORM`, `CredentialORM`, `SessionORM`.

## Размещение

- Зависимости и их инъекция — `backend/app/presentation/api/di/`.
- Для каждого UseCase — отдельный DI-файл, например `di/login.py`, `di/register.py`, `di/auth.py`.
- Внутри DI выделены `clients/` (PostgreSQL/Redis), `repositories/`, `ports/` и `entities/` (в том числе текущий пользователь). Для каждого провайдера используется функция `get_*` и отдельный `Annotated[..., Depends(get_*)]`-алиас.
- DI UseCase принимает готовые алиасы репозиториев/портов в сигнатуре и передаёт зависимости в конструктор. Репозиторная DI принимает `PostgresSessionDI` и возвращает интерфейс с конкретным SQLAlchemy-адаптером.
- Pydantic-схемы запросов — `api/schemas/requests/`, ответов — `api/schemas/responses/`. Схемы login/register размещаются в соответствующих файлах этих директорий.
- Документация ручек — `docs/endpoints/<group>.md`, один файл на группу. Она обновляется при каждом добавлении/изменении ручек и содержит назначение, права доступа, параметры, ответы, ошибки и дополнительные сведения.
- Application DTO — `app/application/dto/`; они не зависят от Pydantic и FastAPI. DTO — внутренние объекты приложения, не внешние схемы Request/Response.
- В application нет портов и репозиторных интерфейсов. Порты внешних интеграций находятся в domain; все операции с сущностями, включая поиск, выражаются методами доменных репозиториев в `domain/repositories/`.
- Репозиторий принимает/возвращает доменные сущности, не application DTO. Адаптеры находятся в infrastructure; UseCase преобразует сущность в application DTO для результата сценария.
- По умолчанию прикладная логика реализуется в UseCase. Application service с CRUD-логикой вокруг сложной сущности создаётся только по прямому указанию пользователя.
- Все dataclasses создаются с `kw_only=True`; для моделей domain/application также обязателен `slots=True`. Аргументы передаются по имени.
- Внешний Request преобразуется в application DTO в presentation. Результат UseCase преобразуется в Response там же; application DTO не принимаются и не возвращаются напрямую HTTP-ручкой.
- Request-модель содержит типизированный метод `to_dto(self) -> CorrespondingDTO`, выполняющий маппинг presentation → application.
- Response-модель создаётся из соответствующего application DTO через типизированный `@classmethod from_dto(cls, dto: CorrespondingDTO) -> Self`.
- Маппинг полей находится в Request/Response-моделях. Ручки вызывают `request.to_dto()` и `Response.from_dto(result)` вместо ручной сборки DTO или Response из полей.
- Валидация email — `pydantic.EmailStr` (зависимость `pydantic[email]`); нормализация `trim + lowercase` выполняется перед встроенной валидацией.

## DI и выполнение UseCase

UseCase — конкретный класс application, реализующий единицу прикладной работы. UseCase не объявляется абстрактным: не используются `ABC`, `@abstractmethod` или отдельный интерфейс самого сценария.

- Все зависимости UseCase передаются извне в `__init__` и типизируются интерфейсами репозиториев и портов.
- DI собирает конкретные адаптеры и передаёт их в конструктор UseCase. Конфигурационные значения также передаются извне при инициализации.
- UseCase не создаёт собственные репозитории, адаптеры, клиенты БД/Redis и не обращается к DI или глобальному `app_config`.
- Абстракции относятся к зависимостям сценария, а реализация прикладной логики находится в самом UseCase.

### Общая авторизация UseCase

- Все UseCase наследуются от конкретного `BaseUseCase` в application.
- `BaseUseCase.__init__` принимает `min_permission: UserRole = UserRole.USER` и сохраняет его как `access_level`.
- Наследник задаёт минимальный уровень в своём `__init__` через `super().__init__(min_permission=...)`; для общего уровня достаточно `super().__init__()`.
- `authorize(user: UserDTO) -> bool` проверяет `self.access_level <= user.role`. Роли образуют иерархию `USER (1) < MODERATOR (2) < ADMIN (3)`.
- Защищённый сценарий вызывает `authorize` перед обращением к зависимостям; при отказе presentation возвращает `403`. `FindAccountsUseCase` требует уровень `MODERATOR`.
- Аутентификация и проверка активности остаются задачей auth-сценария/DI. Публичные login/register не требуют существующего пользователя и не вызывают `authorize` до аутентификации.
- Проверки владения ресурсом остаются отдельными от сравнения уровней ролей.

UseCase **не callable**: `__call__` не используется. Сценарий имеет метод с именем, выражающим его доменную логику: `login`, `register`, `authenticate` и т. п.

Обычная DI собирает и **возвращает экземпляр UseCase**, не выполняя прикладной сценарий. Функция сборки и `Annotated`-алиас объявляются отдельно; в presentation вызывается именованный метод:

```python
def get_login_usecase(
        user_repository: UserRepositoryDI,
        credential_repository: CredentialRepositoryDI,
        session_repository: SessionRepositoryDI) -> LoginUseCase:
    return LoginUseCase(
        user_repository=user_repository,
        credential_repository=credential_repository,
        session_repository=session_repository,
    )


LoginUseCaseDI = Annotated[
    LoginUseCase,
    Depends(get_login_usecase),
]


async def login(
        data: LoginRequest,
        use_case: LoginUseCaseDI) -> LoginResponse:
    result = await use_case.login(data.to_dto())
    # Установить result.token в HttpOnly cookie.
    return LoginResponse.from_dto(result)
```

`AuthUseCase` — единственное исключение: DI-обёртка `get_authenticated_user` извлекает JWT из HttpOnly cookie, передаёт токен в `use_case.authenticate(token)` и возвращает аутентифицированного пользователя (в текущем контракте — `UserDTO`). `AuthUseCaseDI = Annotated[UserDTO, Depends(get_authenticated_user)]`. Endpoint принимает `user: AuthUseCaseDI`, не вызывая auth повторно. Сам AuthUseCase собирается через `get_auth_usecase`, принимает строку токена и не знает о cookie или FastAPI.

### ORM-репозитории и транзакции

- Сначала определяются доменные интерфейсы Repository, затем их инфраструктурные реализации.
- SQLAlchemy-адаптер получает `AsyncSession` извне через `__init__`. Адаптер не создаёт сессии и не обращается к фабрике/DI.
- Запросы пишутся через ORM; всё I/O выполняется явно и асинхронно. Связи ORM имеют `lazy="raise"`; при необходимости используется явная eager-загрузка.
- Каждый адаптер имеет `_to_orm(entity)` и `_from_orm(orm)`. Изменения принимают доменную сущность, работают с ORM и возвращают доменную сущность. Чтения используют UUID/критерии и возвращают сущности; списки всегда ограничены limit/offset.
- После создания, изменения и удаления вызывается `await session.flush()`. В адаптерах запрещены `commit()` и `rollback()`.
- Commit/rollback выполняет фабрика при выходе из контекста сессии. Только явно обоснованный UseCase может самостоятельно управлять commit.
- Все репозитории запроса используют одну кэшированную `PostgresSessionDI`. Её yield-dependency имеет `scope="function"`, чтобы финальный commit выполнялся до отправки успешного HTTP-ответа.
- Блокировки чтения запрашиваются явно через `for_update=True`; update/delete используют явный SELECT FOR UPDATE. Смена текущего пароля и авторизация остаются многошаговыми UseCase в общей транзакции.

## Форматирование многострочных сигнатур

Общий кодстайл описан в `agent-rules/codestyle.md`. Максимальная длина строки Python-кода — **70 символов**, включая отступ; это касается также тестов, комментариев и миграций. Правило проверяется Ruff E501.

- При переносе параметров функции или метода на отдельные строки использовать дополнительный уровень отступа (TAB): параметры располагаются на 8 пробелов глубже строки `def`/`async def`.
- Закрывающая скобка, аннотация возвращаемого типа и двоеточие остаются на строке последнего параметра.
- Тело функции имеет обычный отступ в 4 пробела относительно строки `def`/`async def`, чтобы отличаться от перенесённых параметров.
- Правило применяется к обычным и асинхронным функциям и методам. Отступы записываются пробелами без смешивания с символами табуляции.

```python
async def login(
        data: LoginRequest,
        response: Response,
        use_case: LoginUseCaseDI) -> LoginResponse:
    result = await use_case.login(data.to_dto())
    return LoginResponse.from_dto(result)
```

## FastAPI

- Не указывать `response_model` в декораторе: FastAPI выводит схему из аннотации возвращаемого типа.
- Request-модели в GET-ручках подключаются как `Annotated[Model, Query()]`, а не как JSON-тело или набор отдельных query-параметров.
- Ответы без JSON-тела, например `RedirectResponse`, не требуют выдуманной схемы тела.
- JWT устанавливается сервером в `Secure; HttpOnly` cookie и автоматически отправляется браузером. Токен не возвращается в JSON и не извлекается из `Authorization`.
- Срок сессии — внутреннее состояние SessionEntity; клиенту он не возвращается. Успешный login возвращает `200` с пустым JSON-объектом `LoginResponse` и устанавливает cookie.

### Пагинация

- Общая модель — `PaginationRequest` в `api/schemas/requests/pagination.py`. Все Request-модели с пагинацией наследуются от неё.
- `limit`: по умолчанию 20, минимум 1, максимум 100. `offset`: по умолчанию 0, минимум 0, максимум 10 000.
- Числовые строки query-параметров разбираются в int; границы валидируются Pydantic. Неизвестные query-поля запрещены; ошибки возвращаются общим mapper как `400`.
- Если дополнительных query-параметров нет, использовать `pagination: Annotated[PaginationRequest, Query()]` напрямую. Префикс username в `/account/find/{username_prefix}` остаётся отдельным параметром пути и не требует специальной query-модели.
- `PaginationRequest.to_dto()` возвращает внутренний `PaginationDTO`. UseCase передаёт `limit`/`offset` в репозиторий; постраничное чтение выполняется в хранилище, не срезом полного результата в application.
- GET-ручки без query-параметров, например `/account/me`, не требуют искусственного Request или пагинации.

## Ошибки

- Собственные ошибки всех слоёв — общие доменные исключения из `domain/exceptions/entities/`, наследники `BaseDomainException` из `domain/exceptions/base.py`.
- Использовать общие типы `NotFoundException`, `ConflictException`, `AlreadyExistsException`, `DataFormatException`, `AuthenticationException`, `PermissionException` и т. п. Не создавать `UserNotFound`, `AccountSearchForbiddenError` и другие типы с контекстом конкретной операции в имени.
- Человекочитаемое описание находится в `message`, контекст (сущность, операция, поле, причина) — в `details`.
- Infrastructure переводит ожидаемые ошибки библиотек в эти же доменные исключения. HTTP-статусы не задаются в domain, application, infrastructure или DI.
- Единственное место преобразования доменных ошибок в HTTP — `presentation/setup_exceptions.py`, функция `setup_exception_handlers(app)`.
- Формат ответа: `{"error": "<код>", "message": "<описание>", "details": {...}}`. Ошибки валидации FastAPI возвращают `400`, контекст ошибок полей — в `details.errors` без исходных секретов запроса.
