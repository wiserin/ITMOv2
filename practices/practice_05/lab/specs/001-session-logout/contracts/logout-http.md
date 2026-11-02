# Session Logout: API / Proxy Contract

**Date**: 2026-11-02 · **Authority**: [CONTRACT v1.0 §2–5,7–10](../../../docs/sdd/logout/CONTRACT.md).
Это производный интерфейсный артефакт Phase1, не новая редакция согласования.
При расхождении действует CONTRACT; новые требования здесь не вводятся.
Трассировка: spec FR-003–019,025–026 и C-01–C-17,C-23–C-24,C-26–C-27.

## Request

| Аспект | Контракт |
| --- | --- |
| Path/method | POST /v1/auth/logout, ровно этот путь, без path-ID |
| Backend operation | auth_logout; OpenAPI tag auth |
| Credential | Cookie session_token, не Bearer/Authorization |
| CSRF | X-AnimeMap-Logout: 1, имя case-insensitive; нет/иное/неоднозначное множественное значение →403 |
| Body | Ровно0 bytes; не JSON null, {}, пробел или damaged JSON |
| Query | Параметры отсутствуют, включая параметры с пустым значением |
| Content-Type | Не обязателен и допустим при нулевом теле |
| Browser | Relative same-origin URL, credentials:same-origin, cache:no-store |

Нулевое тело не требует искусственного Request DTO/JSON-parser. Query/body не выбирают
другую сессию даже при известном ID. JWT/secret проверяются в неизменном формате baseline.

## Validation precedence and methods

1. На распознанном пути неподдерживаемый метод →405 с Allow: POST, без аутентификации,
   чтения сессии для auth, записи и Set-Cookie. HEAD без тела; OPTIONS не открывает CORS.
2. Для POST присутствующий недопустимый Origin может быть отклонён proxy до API.
3. Проверка CSRF →403 независимо от body/query/cookie.
4. После правильного CSRF непустое тело/любой query →400 до cookie.
5. Затем cookie/JWT/secret/состояние сессии/владельца.

Примеры: bad CSRF + damaged JSON→403; valid CSRF + {} + no cookie→400;
valid CSRF + empty input + no cookie→401. Приоритет нескольких credential-дефектов
не гарантируется; в одиночном дефекте возвращается причина таблицы ниже.
Ни общий proxy buffer413, ни автоматический parser422 не заменяют согласованный порядок.

## Success response

```http
HTTP/1.1 204 No Content
Cache-Control: no-store
Set-Cookie: session_token=; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; HttpOnly; SameSite=Lax
```

Ровно0 bytes body, нет Location/redirect/JSON/JWT/срока сессии.
204 подтверждает сохранённый close только предъявленной записи. Commit предшествует
HTTP start; подготовленный Response при ошибке commit не отправляется.
Неактивный владелец при подтверждённой пригодной сессии получает204 без активации аккаунта.
Другие сессии и last_used_at/expires_at не меняются этим Logout.

После commit новая аутентификация сохранённой копией JWT отклоняется. Повтор даёт401,
не меняет closed_at. Истечение now>=expires_at даёт401 без materialized close/use.
Ранее аутентифицированный бизнес-запрос может завершиться после Logout.

## Errors and cookie policy

Все фактические контролируемые ошибки backend/proxy имеют no-store.
Где тело разрешено HTTP, Content-Type application/json (charset допустим) и envelope:

```json
{"error":"authentication_failed","message":"Authentication failed","details":{"reason":"session_closed"}}
```

error/message — strings, details — object, включая пустой. Текст message не machine contract.

| Условие после более приоритетных проверок | Status / error | details.reason / baseline | session_token |
| --- | --- | --- | --- |
| Unsupported method | 405 / method_not_allowed | Безопасный объект, Allow: POST | Не менять |
| Invalid/mismatched present Origin | 403 / access_denied | origin_check_failed | Не менять |
| Bad/missing/ambiguous CSRF | 403 / access_denied | csrf_check_failed | Не менять |
| Nonempty body / any query | 400 / bad_request | Безопасная validation context | Не менять |
| Cookie отсутствует/пуста; только Bearer | 401 / authentication_failed | missing_session_cookie | Удалить |
| Invalid JWT signature/algorithm/claims/UUID | 401 / authentication_failed | invalid_token | Удалить |
| Нет сессии/владельца | 401 / authentication_failed | session_not_found | Удалить |
| Closed | 401 / authentication_failed | session_closed | Удалить |
| Expired, включая verify/locks | 401 / authentication_failed | session_expired | Удалить |
| Wrong secret | 401 / authentication_failed | invalid_secret | Удалить |
| Corrupt stored hash | 400 / bad_request | Existing mapper, без hash | Не менять |
| PostgreSQL unavailable, включая commit | 503 / service_unavailable | Existing mapper | Не менять |
| Другая backend-ошибка | docs/errors.md; unexpected500/internal_error | Safe baseline, retryable/sqlstate где применимо | Не менять |
| Upstream timeout | 504 / service_unavailable | upstream_timeout | Не менять |
| Upstream connection failure / unexpected3xx | 502 / service_unavailable | upstream_failure | Не менять |

Удаление **на204 и каждом Logout-401**: пустое значение, host-only без Domain,
Path=/, Max-Age=0, Expires в прошлом, Secure/HttpOnly/SameSite=Lax — scope как у login.
Приведённая дата illustrative; порядок атрибутов и кавычки пустого значения несущественны.
На остальных ошибках session Set-Cookie отсутствует, включая фактический mapper/commit/500.
Это свойство ответа, не гарантия отсутствия другого параллельного browser-cookie эффекта.
Proxy не синтезирует cookie; JS не читает и не удаляет HttpOnly.

Logout-401 означает отказ credential/состояния этого сценария. Инфраструктурный401
не подменяет Logout-401. Cookie deletion/локальный вход/401 не доказывают нового close.
Raw JWT, Cookie/Set-Cookie, secret/hash, SQL/параметры/исключения не отражаются в ошибках/логах.

## Proxy interface and topology

- Только Browser→same-origin Node.js proxy→FastAPI; рабочая Secure-cookie проверка по HTTPS.
- Present Origin POST сравнивается по полной нормализованной тройке scheme/hostname/effective port;
  null/malformed/mismatch→403 без upstream, эквивалентные порты проходят.
- PUBLIC_ORIGIN — выбранная планом trusted runtime configuration, не клиентский заголовок;
  отсутствие Origin не является доверием и не отменяет CSRF.
- На допустимом запросе передаются исходные Cookie/CSRF; отсутствующий CSRF не добавляется,
  неверное/неоднозначное значение не исправляется. Backend повторяет свои проверки.
- Route-specific local отказ CSRF/body/query не превращает invalid request в valid upstream.
  Bad body/query не обнуляются перед валидацией и не дают413 общего buffer вместо400.
- Status, Set-Cookie, Cache-Control и Allow передаются без потери семантики.
  204 не получает JSON body; unsupported HEAD также без body.
- Upstream redirect не следует; unexpected3xx→502 без его Set-Cookie.
  Registration303→201 здесь не применяется.
- Upstream deadline15 000ms от dispatch до завершения чтения ответа; до buffer completion
  status/cookie успеха браузеру не отправляются. При timeout504, если соединение доступно;
  при иной ошибке связи502. Deadline включает body phase. Автоповторов нет.

## Commit and uncertainty boundary

Финальная проверка/close/save выполняются атомарно с locks user→session и refreshed state.
Factory commit/rollback завершает function-scope dependency до Response.__call__.
На unknown commit возвращается ошибка без удаления cookie и без обещания rollback.
Потерянный после успешного commit ответ не отменяет запись; повтор старым JWT/без cookie→401.
15/20s и abort не являются DB deadline. Commit, HTTP, cookie delivery и UI не атомарны.
Late deletion может удалить cookie нового login; новая независимая серверная сессия
не закрывается. Эта принятая граница сохраняется без межвкладочного координатора.
