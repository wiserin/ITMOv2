# Session Logout: UI / Transport / Coordinator Contract

**Date**: 2026-11-02. Производный контракт взаимодействия существующих компонентов.
Нормативные источники: [CONTRACT §6–8](../../../docs/sdd/logout/CONTRACT.md),
[UI V2 §3–8](../../../docs/sdd/logout/UI_SPEC_V2.md), [spec FR-002,019–030](../spec.md).
Это интерфейсы будущей реализации, не код и не новые продуктовые требования.

## Ownership

| Граница | Вход | Выход / обязанность |
| --- | --- | --- |
| App-owned useAuthSession | login/logout action, protected expiry с generation, transport result | Account/generation, auth busy, logout state, notices, guarded callbacks |
| sessionState | Current state + event с generation/operationId/attemptId | Pure transitions; stale no-op; release только своего owner |
| API logout helper | Abort/deadline context | Exact status outcome closed204 / invalid401 / safe failure; без JWT данных |
| Header | start/retry/dismiss callbacks, busy/status | Кнопка, menu/focus, progress вне dropdown; не владеет попыткой |
| AuthPage | Shared busy, login action, notice/dismiss | Guard submit, login+me одна операция, focus heading |
| Account/Admin requests | Captured generation/request ID, pending permission | No new protected requests while pending; guarded success/error/401/finally |

Детальные представления полей — [data-model.md](../data-model.md).
Ref-owned operation gate захватывается синхронно до отправки запроса; React state отражает
занятость, но не является единственным lock. Generation не подменяет operation ownership.

## Transport outcomes

- POST `/v1/auth/logout`, body отсутствует, query отсутствует, CSRF1, same-origin/no-store.
- closed — только точный204; invalid — достоверный Logout401, даже без корректного error JSON.
- failure — сеть/status0, timeout, unavailable502/503, rejected/other включая403 и не2042xx.
  Не показывать raw message/details или generic search error.
- При ошибке optional JSON чтения не терять уже известный достоверный401.
  Budget20 000ms от отправки охватывает получение результата/потребление ответа.
- Transport не хранит account, не меняет hash, не читает JWT/cookie и не повторяет запрос.
  Смена UI разрешается только coordinator после проверки identity.

## State transitions

Для изменения UI результатом требуются текущие generation и live attemptId.
Освобождение auth slot отдельно проверяет operation owner: оно допустимо и после смены
generation, если slot всё ещё принадлежит завершившейся операции, но не новому владельцу.

| Current / event | Next state / effect |
| --- | --- |
| authenticated idle/failed + explicit logout, slot free | Acquire slot, new attempt, pending; один POST; close menu; progress |
| pending + click/Enter/menu/hash | Не отправлять повтор, не сбрасывать ожидание/блокировку |
| pending +204 current | Clear account/data, generation++, signed-out, login+success |
| pending +401 current | Clear account/data, generation++, unauthenticated, login+neutral notice, no repeat |
| pending +failure current + auth retained | authenticated/failed, screen/account retained without validity promise, release own slot |
| idle/failed/pending +protected401 current generation | Clear/generation++, unauthenticated; если Logout ждёт, его slot остаётся busy |
| Any +stale success/error/401/timer/finalizer | Не менять current account/hash/notice/attempt; release лишь собственного operation owner |
| failed +dismiss | idle без восстановления snapshot |
| failed +manual retry, slot free | pending с новым attempt/operation ID |
| signed-out/unauthenticated +successful login, slot free | New generation/account, home, no previous personal state/notices |

Сначала terminalize/invalidate attempt, затем release своего slot. Завершённая или просроченная
попытка не активируется повторно. Новый login после timeout допустим, даже если предыдущая
серверная операция ещё продолжается. Protected401 не освобождает чужую незавершённую операцию.
Если Logout первым сменил generation, более поздний старый protected401 также игнорируется.

## Data privacy and actions

Clear одновременно убирает account, search/pagination/results, selected card, personal errors
и memory state; Header/защищённые экраны скрываются без кадра личных данных на login.
Generation-keyed subtree remount и guards callbacks действуют совместно.
Hash navigation не запускает новые protected effects во время pending; начатые запросы
могут завершиться на сервере, но после clear их данные не применяются.
Login и Logout не отправляются параллельно в одной вкладке и не ставятся в auto queue;
login держит slot через `/account/me`. Регистрация сохраняет baseline.

## Exact presentation

| Outcome | Text |
| --- | --- |
| 204 | Вы вышли из аккаунта. |
| Logout401 | Сессия недействительна. Войдите снова |
| Network / status0 | Не удалось подтвердить выход: нет соединения. Попробуйте ещё раз. |
| UI timeout /504 | Не удалось подтвердить выход: сервер не ответил вовремя. Попробуйте ещё раз. |
| 502/503 | Не удалось подтвердить выход: сервис временно недоступен. Попробуйте позже. |
| Other errors / unexpected responses | Не удалось подтвердить выход. Попробуйте ещё раз. |

Pending: «Выходим…», вне dropdown, role=status; trigger остаётся focusable,
но не разрешает открытия/действий pending. Старт закрывает меню и возвращает focus на trigger.
Кнопка без «Скоро», доступна pointer/touch/Enter/Space. Failure role=alert, «Повторить выход»
и «Закрыть уведомление» доступны клавиатурой; error не auto-dismiss.
На login focus heading и итог role=status; notice закрывается вручную, сбрасывается новым login.
Проверить что cleanup dialog не перехватывает focus обратно. Узкий экран не обрезает текст/действия.

## Navigation and accepted boundaries

Back/Forward/protected hash не восстанавливают данные. Reload использует baseline me:
401→login, unavailable→loading-error с повтором. Дополнительный me после204 не нужен.
Другая вкладка очищается на next current protected401/reload, без polling/broadcast.
UI generation не блокирует браузерный Set-Cookie. После timeout или между вкладками
позднее удаление может затронуть новый credential; новая серверная сессия не закрывается.
В UI и proxy нет автоповторов, включая retryable. Abort/уход со страницы не доказывают rollback.
