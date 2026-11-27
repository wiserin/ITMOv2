# AnimeMap Frontend

React + TypeScript; Vite собирает клиент, встроенный HTTP/HTTPS-сервер
Node.js 22+ раздаёт сборку и проксирует API. Nginx не требуется.
Контракты взяты из `../docs/endpoints/`.

## Локальный запуск

Из `frontend/`:

```bash
npm ci
npm run build
npm start
```

Открыть **http://localhost:3000**. API по умолчанию ожидается на
`http://localhost:8080`. Другой адрес и порт:

```bash
API_ORIGIN=http://localhost:8082 PORT=3001 npm start
```

`API_ORIGIN` — origin бэкенда без `/v1`. Это runtime-настройка:
пересобирать клиент при смене адреса не нужно. Сервер сам не запускает
бэкенд. Порядок запуска API описан в `../docs/deployment.md`.
`npm run dev` перезапускает Node.js при изменениях сервера;
после изменения клиента повторить `npm run build` и обновить браузер.

## Docker Compose

Из `frontend/`, при уже работающем API на порту 8080 хоста:

```bash
docker compose up --build --wait
docker compose logs -f frontend
docker compose down
```

Открыть **http://localhost:3000**. Настройки:

```bash
API_ORIGIN=http://host.docker.internal:8082 FRONTEND_PORT=3001 docker compose up --build --wait
```

`host.docker.internal` поддерживается Docker Desktop; для Linux
в Compose добавлен `host-gateway`. API должен быть доступен из
контейнера по указанному адресу. Frontend Compose независим от
корневого Compose. Используется `Dockerfile.node`; исходный
`Dockerfile` сохранён согласно ограничению на существующие файлы.

### Если фронтенд показывает «API недоступен»

На старте лог `API upstream: ...` показывает фактический адрес API.
При сетевой ошибке лог `[API proxy]` содержит адрес и код причины,
например `ECONNREFUSED`, без паролей и cookie.

В Docker значение `API_ORIGIN=http://localhost:8080` указывает на
сам контейнер фронтенда, а не на Mac. Переменная из shell или `.env`
переопределяет значение Compose по умолчанию. Для API на хосте:

```bash
API_ORIGIN=http://host.docker.internal:8080 docker compose up --build
```

Для обычного `docker compose up --build` удалите неправильный
`API_ORIGIN` из своего окружения (`unset API_ORIGIN`) или исправьте
его в используемом `.env`. При запуске Node.js вне Docker,
наоборот, подходит `http://localhost:8080`.

Production-образ не содержит npm-зависимостей, исходников клиента
или инструментов сборки и запускается от пользователя `node`.
`/health` проверяет процесс фронтенда, а не доступность API.

## Cookie и HTTPS

Клиент обращается к `/v1/` на своём origin. Node.js передаёт cookie
в API и возвращает `Set-Cookie` без изменения `Secure`, `HttpOnly`,
`SameSite` и `Path`. JWT не попадает в JS или localStorage.
Браузеры допускают Secure cookie на `http://localhost`; для доступа
по IP или внешнему домену нужен HTTPS.

Сервер умеет завершать TLS самостоятельно:

```bash
TLS_CERT=/absolute/path/localhost.pem TLS_KEY=/absolute/path/localhost-key.pem npm start
```

Используйте доверенный браузером сертификат. В Docker можно добавить
отдельный Compose override с read-only volume сертификатов,
`TLS_CERT`/`TLS_KEY` и HTTPS healthcheck. Базовый Compose рассчитан
на локальный HTTP через localhost. Для внешнего TLS termination
перед Node.js можно использовать имеющуюся инфраструктуру.

## Поведение

- `#/login`, `#/register`: вход по email, регистрация без автовхода.
  Прямые адреса `/login` и `/register` также поддерживаются.
  Пароль передаётся без trim. Имя и email нормализуются по контракту.
- Node.js не следует `303` регистрации: преобразует его в `201`,
  после чего UI показывает форму входа и подтверждение регистрации.
- `#/`: placeholder AnimeMap, меню по наведению, клику и клавиатуре.
- `#/account`: актуальные данные из `GET /v1/account/me`, ссылка назад.
- `#/admin`: только moderator/admin. Поиск по буквальному префиксу
  username с учётом регистра, debounce 300 мс, отмена устаревших
  запросов, страницы по 20 аккаунтов, максимальный offset 10 000.
  Карточка использует данные найденного аккаунта; отдельной ручки
  получения чужого профиля нет. UUID различает одинаковые username.
- Модальное окно поддерживает Escape, focus trap и возврат фокуса.
- `401` защищённых запросов возвращает к входу; ошибки сервиса
  показываются отдельно от пустого результата. `403` поиска выводится
  как отказ в доступе. Права также проверяются API.
- «Выйти» — запрошенная заглушка с уведомлением; сессия сохраняется.

Шрифт Manrope загружается из Google Fonts; при отсутствии сети
используется системный шрифт. Остальная графика создаётся CSS.

## Структура

```text
src/
  api/          # HTTP-клиент и типы контрактов
  components/   # меню, профиль, модальное окно, бренд
  pages/        # авторизация, главная, аккаунт, админка
  styles/       # адаптивное оформление
server/         # Node.js static server, TLS и API proxy
tests/          # проверки прокси и браузерных сценариев
```

## Проверки

```bash
npm run build
npm test
npx playwright install chromium
npm run test:e2e
```

Браузерные проверки используют подмену API по документированным
контрактам; серверные — настоящий HTTP mock upstream. Для проверки
с реальным API запустить backend по его документации и пройти
регистрацию/вход. Bootstrap admin: `root@example.com` / `root`.
