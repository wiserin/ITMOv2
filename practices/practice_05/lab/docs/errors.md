# Общие доменные ошибки и HTTP-контракт

Собственные ошибки всех слоёв определяются в `backend/app/domain/exceptions/entities/` и наследуются от `BaseDomainException` (`domain/exceptions/base.py`). Контекст сущности или сценария задаётся в `details`, а не названием отдельного класса ошибки.

```python
raise NotFoundException(details={"entity": "user", "id": str(user_id)})
raise ConflictException(details={"entity": "location", "operation": "verify"})
```

У ошибки есть `message` (общее человекочитаемое сообщение) и `details` (словарь контекста). Domain/application не знают HTTP-статусов и не импортируют FastAPI. Ошибки драйверов и внешних библиотек переводятся инфраструктурой в те же общие исключения.

## Mapper presentation

`setup_exception_handlers(app)` регистрируется при сборке FastAPI-приложения. Точка входа `run.py` уже вызывает эту функцию; тестовые приложения подключают те же обработчики. Ручки и DI не перехватывают доменные ошибки для локального преобразования в `HTTPException`.

| Доменная ошибка | HTTP | `error` |
| --- | --- | --- |
| `AlreadyExistsException` | 409 | `conflict` |
| `ConflictException` | 409 | `conflict` |
| `DataFormatException` | 400 | `bad_request` |
| `NotFoundException` | 404 | `not_found` |
| `AuthenticationException` | 401 | `authentication_failed` |
| `PermissionException` | 403 | `access_denied` |
| `NotImplementedException` | 501 | `not_implemented` |
| `ServiceUnavailableException` | 503 | `service_unavailable` |
| Прочий `BaseDomainException` | 500 | `internal_error` |

Единый формат `ErrorResponse`:

```json
{
  "error": "not_found",
  "message": "Entity not found",
  "details": {
    "entity": "user",
    "id": "899f2a44-9842-4d1a-b951-03bc78d1e6e9"
  }
}
```

Неверный пароль, истёкшая сессия и отсутствие cookie используют один `AuthenticationException`, но разные `details.reason`. Отказ в поиске аккаунтов — общий `PermissionException` с `details.entity`, `details.operation` и `details.min_permission`.

## Валидация запроса

`RequestValidationError` переводится в `400 Bad Request` тем же presentation-модулем:

```json
{
  "error": "bad_request",
  "message": "Ошибка валидации данных.",
  "details": {
    "errors": [
      {
        "type": "missing",
        "loc": ["body", "email"],
        "msg": "Field required"
      }
    ]
  }
}
```

Включаются тип, путь и описание ошибки поля; исходное тело, пароли и токены не отражаются в ответе. Контракт `/v1` описывает `400` и общий ответ `4XX` в OpenAPI; стандартный автоматически добавляемый `422` не используется.

## Инфраструктура

PostgreSQL: нарушение уникальности (`23505`) → `AlreadyExistsException`; NOT NULL/CHECK/длина (`23502`, `23514`, `22001`) → `DataFormatException`; конфликт FK и другие ограничения целостности → `ConflictException`; ошибки доступности → `ServiceUnavailableException`. SQLSTATE хранится в `details.sqlstate`, а deadlock/serialization failure дополнительно имеют `details.retryable = true`. Исходные SQL и параметры не передаются клиенту.

Ожидаемые ошибки Redis при проверке/закрытии соединения переводятся в `ServiceUnavailableException` с `details.storage` и `details.operation`. Неподключённые сценарии и репозитории используют общий `NotImplementedException` с операцией в `details`, а не специализированные имена исключений.
