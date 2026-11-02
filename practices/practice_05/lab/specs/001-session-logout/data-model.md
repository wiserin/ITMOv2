# Phase 1 Data Model: Session Logout

**Date**: 2026-11-02. Модель существующих данных и будущего поведения, не миграция.
Основания: [spec FR-001,009–015,020–028](spec.md),
[CONTRACT §1,3,5–8](../../docs/sdd/logout/CONTRACT.md), [research R-01/02/05](research.md).

## 1. Серверная SessionEntity — существующая сущность

| Поле | Тип / значение | Правило Logout |
| --- | --- | --- |
| id | UUIDv4 | Не меняется; определяется jti предъявленного JWT |
| user_id | UUID владельца | Не меняется; владелец должен существовать и совпадать при refreshed read |
| secret_hash | Argon2id hash | Не меняется; сверка актуального hash с проверенным обязательна |
| created_at | timezone-aware timestamp | Не меняется |
| last_used_at | timezone-aware timestamp | Не меняется этим Logout, сохраняется более свежее конкурентное продление |
| expires_at | timezone-aware timestamp | Не меняется этим Logout; пригодность now < expires_at |
| closed_at | nullable timezone-aware timestamp | Для нового close max(now,last_used_at); при повторе исходное значение |

Сессия — frozen, slots=True, kw_only=True dataclass; команда возвращает новый объект.
Открытый secret существует лишь в локальном credential-контексте проверки,
не добавляется в Entity/Repository/ORM/ответ. SessionORM уже содержит все эти поля
и CHECK closed_at >= last_used_at. Owner→sessions связь и CASCADE delete сохраняются.
Новые таблицы, индексы, Redis-структуры и миграции не нужны.

### Команда и пригодность — разные обязанности

- `close(now=None)` на незакрытой сущности задаёт closed_at и сохраняет остальные поля.
  Default now — свежий aware UTC; обратный сдвиг часов не делает closed_at < last_used_at.
- `close` на закрытой сущности возвращает эквивалентное состояние с прежним временем.
- Публичный сценарий перед close проверяет `ensure_usable` и после locks повторяет проверку.
  Доменная идемпотентность не превращает закрытый/истёкший credential в публичный204.
- `now == expires_at` и `now > expires_at` — истечение; close не материализуется.
- `use()` принадлежит ordinary Auth и в Logout не вызывается.

## 2. UserEntity — существующий владелец

Для Logout существенны id, role и is_active. Все три роли имеют одинаковое право
закрыть собственную пригодную сессию. is_active=false не мешает закрытию и не меняется.
Это узкое ADR-07 исключение, не право получить UserDTO или доступ к account/me.
Отсутствие/удаление пользователя — session_not_found; CASCADE не является записью Logout.

## 3. Локальный credential-check context — не persisted entity

| Значение | Назначение |
| --- | --- |
| JWT строка | Вход прикладного сценария; извлечён Presentation из cookie |
| jti / secret / iat | Existing verified claims, без нового exp/rotation |
| initial owner ID / verified hash | Сравнить с актуальной locked entity после verify |
| свежий UTC now | Финальная проверка срока и вычисление closed_at после locks |

Этот контекст не логируется и не становится публичным DTO. Проверка подписи и Argon2id
предшествует row locks; permission на запись выводится только из финального актуального состояния.

## 4. Состояния серверной записи

| Исходное состояние / событие | Эффект | Публичный исход |
| --- | --- | --- |
| Open, now < expires_at, credential/владелец подтверждены | close + commit; только closed_at | 204 после commit |
| То же, is_active=false | Тот же close; аккаунт не активируется | 204 |
| Closed | Нет нового close | 401/session_closed |
| Expired, включая время verify/lock wait | Без close/use | 401/session_expired |
| Владелец/сессия отсутствуют | Нет записи этим Logout | 401/session_not_found |
| Незавершённое изменение, подтверждённый rollback | Сохранённого close нет | Ошибка без удаления cookie |
| Commit acknowledgement потерян | Persisted outcome неизвестен | Ошибка без обещания rollback |

Все domain/state401 предполагают прохождение method/Origin/CSRF/input checks.
Идемпотентен эффект closed_at, не последовательность HTTP-статусов204→401.

## 5. Клиентская модель — только память вкладки

Ни JWT, ни cookie, ни личные данные не добавляются в browser storage.

| Составляющая | Поля / значения | Время жизни и инвариант |
| --- | --- | --- |
| AuthContext | generation, account или null | Generation меняется при clear/replacement; старые события не применяются |
| AuthOperation | unique operationId, kind login/logout, busy | Синхронный ref-owned slot; максимум один; clear auth не снимает slot |
| LogoutAttempt | attemptId, operationId, capturedGeneration, startedAt/deadline, terminal | Deadline20s; завершённый ID не оживает; release только своего slot |
| LogoutUI | idle/pending/failed; safe reason | Состояние App, а не dropdown/page; error пока auth актуальна |
| LoginOutcome | success/session-invalid notice | Только актуальное поколение; ручное закрытие, сброс новым login |
| ProtectedRequestContext | generation, request identity | Guard success/error/401/finally; search freshness дополнительно к generation |

Состояния signed-out/unauthenticated определяют account=null и разные итоги выхода.
AuthOperation занята независимо от них: protected401 может открыть login, пока Logout ожидается.
Login включает получение аккаунта; его slot нельзя освободить между login и me.

### Переходы и очистка

Полная таблица UI — [contracts/logout-ui.md](contracts/logout-ui.md).
Ключевые правила модели:

1. acquire slot → attempt+captured generation → pending; второй send/queue запрещён.
2. Актуальный204 → clear/generation++, signed-out, success;401 → clear, unauthenticated,
   нейтральный итог. Очищаются account, search/page/card/errors вместе со скрытием subtree.
3. Failure/timeout → failed только при текущих generation/attempt и сохранённой auth.
   После чужого актуального401 остаётся unauthenticated; snapshot не восстанавливается.
4. Terminalize attempt перед release; late callback/finalizer не меняет новое поколение,
   новую попытку или принадлежащую ей занятость.
5. generation-aware unmount и callbacks защищают UI. Доставка Set-Cookie не входит в эту модель:
   поздний ответ может удалить новую одноимённую cookie, не закрывая новую серверную запись.

## 6. Консистентность и отсутствие общей транзакции

Серверная финальная проверка/close/update — одна PG-транзакция с user→session locks.
После неё идёт commit, затем HTTP start. Cookie delivery и React clear — отдельные эффекты.
Возможны commit без доставленного подтверждения и позднее удаление cookie после нового login.
Ни timeout, ни local abort, ни очистка UI не доказывают rollback. Межвкладочная координация
не добавляется; другая вкладка обнаруживает закрытие по следующему protected401/reload.
