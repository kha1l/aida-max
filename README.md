# aida_max

Проект уже умеет:
- принимать `/start` в MAX;
- связывать MAX-пользователя с аккаунтом после OAuth через `dodovkus`;
- работать с PostgreSQL и Redis;
- показывать главное меню, настройки, разделы `Notifications`, `Reports`, `Live data`;
- сохранять подписки в `aida.orders`;
- запускать manual job в Dagster по inline-кнопкам;
- слушать очередь RabbitMQ `aida-max` и отправлять сообщения в MAX.

## Что важно понимать

В MAX есть два разных идентификатора:

- `user_id` — идентификатор пользователя MAX;
- `chat_id` — идентификатор диалога, куда бот реально отправляет сообщения.

В `aida_max` ключевым внешним идентификатором считается именно `chat_id`.

Поэтому:
- в `special.users.platform_id` для `platform='max'` мы храним `chat_id`;
- в `special.settings.chat_id` тоже хранится `chat_id`;
- payload из RabbitMQ должен отправляться в `chat_id`, а не в `user_id`.

## Структура

- `main.py`
  Точка входа приложения.
- `config.py`
  Загрузка конфигурации из `.env`.
- `logger.py`
  Настройка логирования.
- `database/`
  SQLAlchemy-модели, engine и запросы к БД.
- `bot/handlers/`
  Хендлеры `/start`, меню, inline-действий и ошибок.
- `bot/keyboards/`
  Построение клавиатур для MAX.
- `bot/callback/`
  Payload-модели callback-кнопок.
- `bot/middlewares/`
  Middleware для логирования, БД, i18n и user context.
- `bot/helpers/`
  Небольшие вспомогательные функции для работы с MAX update-объектами.
- `services/max_auth.py`
  Клиент bind-flow между `aida_max` и `dodovkus`.
- `services/dagster.py`
  Клиент запуска job через Dagster GraphQL.
- `services/rabbitmq.py`
  Consumer очереди `aida-max`.

## Текущий flow авторизации

1. Пользователь приходит на страницу авторизации в `dodovkus`.
2. `dodovkus` делает OAuth в Dodo IS.
3. После callback сохраняются:
   - `special.accounts`
   - `special.tokens`
   - `special.units`
   - `special.subscribes`
4. Пользователь открывает MAX-бота по deeplink с подписанным payload.
5. `aida_max` ловит `BotStarted` через `DeeplinkFilter` и вызывает bind endpoint в `dodovkus`.
6. В bind-flow создаются и связываются:
   - `special.users`
   - `special.user_account`
   - `special.settings`

## RabbitMQ

`aida_max` слушает отдельную очередь:

```env
RABBIT_QUEUE=aida-max
```

Payload ожидается в формате:

```json
{
  "chat_id": 44752075,
  "text": "<b>Текст отчета</b>",
  "post": "couriers",
  "unit_uuid": "000d3a240c719a8711e68aba13f81faa"
}
```

Поддерживаются поля:
- `chat_id`
- `text`
- `post`
- `topic_id`
- `unit_uuid`

Важно:
- `topic_id` в MAX сейчас игнорируется;
- для action-клавиатур нужен `unit_uuid`;
- если отправить в `user_id` вместо `chat_id`, MAX вернет ошибку `dialog.not.found`.

## Manual reports и Dagster

По inline-кнопкам бот умеет запускать manual job через Dagster:

- `couriers`
- `waiting`
- `later`
- `certificates`
- `sectors`
- `longers`
- `stationary`
- `later_rest`
- `assembly_rest`
- `drink_rest`
- `tracking`
- `metrics`
- `revenue`
- `stock`

Для этого в `.env` должны быть настроены:

```env
DAGSTER_GRAPHQL_URL=
DAGSTER_REPOSITORY_LOCATION=
DAGSTER_REPOSITORY_NAME=__repository__
DAGSTER_AUTH_HEADER_NAME=
DAGSTER_AUTH_HEADER_VALUE=
DAGSTER_REQUEST_TIMEOUT_SECONDS=15
```

## Основные env

Минимальный набор:

```env
TOKEN=

DBASE_NAME=
DBASE_USER=
DBASE_PASSWORD=
DBASE_HOST=

REDIS_HOST=localhost
REDIS_PORT=6379

RABBIT_URL=amqp://guest:guest@localhost:5672/
RABBIT_QUEUE=aida-max

MAX_BIND_URL=https://dodovkus.ru/aida/max/bind/
MAX_BIND_REQUEST_TIMEOUT_SECONDS=15
```

## Запуск локально

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Что уже перенесено

- базовый runtime на `maxo`;
- middleware chain;
- `/start`;
- settings и смена языка;
- `Notifications`;
- `Reports`;
- `Live data`;
- `RabbitMQ` consumer;
- запуск manual report через Dagster.

## Что пока ограничено

- `topic_id` для MAX пока не используется;
- часть логики пока адаптирована минимально, а не переписана «идеально по-maxo»;
- `bot/dialogs/` теперь содержит только текстовые константы и справочники, а не полный dialog-слой.

## Практические замечания

- Если MAX-пользователь «не авторизован», сначала проверь:
  - есть ли запись в `special.users` с `platform='max'`;
  - совпадает ли `platform_id` с `chat_id` диалога MAX;
  - есть ли `special.user_account`;
  - есть ли `special.settings`.
- Если из RabbitMQ ничего не приходит в чат, почти всегда проблема одна из двух:
  - отправка идет в `user_id`, а не в `chat_id`;
  - payload пришел без `unit_uuid`, и action-клавиатура не построилась.
