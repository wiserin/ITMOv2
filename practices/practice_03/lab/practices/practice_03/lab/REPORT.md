# Practice 3 Report

## Environment
Железо, ОС, версии Ollama и OpenCode.

- Model Name: MacBook Air (Model Identifier: Mac17,3)
- Chip: Apple M5
- Memory: 24 GB
- macOS: 26.5.1 (Build 25F80)
- CPU: Apple M5
- RAM (bytes): 25769803776
- ollama --version: 0.34.4
- opencode --version: 1.18.35

## Model
- base model: gpt-oss:20b
- local alias: itmo-agent
- parameters: 20.9B
- quantization: MXFP4
- context: 16384
- размер модели: 13 GB

Содержимое Modelfile:

```
FROM gpt-oss:20b
PARAMETER num_ctx 16384
```

## Model choice
- qwen2.5-coder:14b некорректно взаимодействовал с OpenCode tools и печатал tool calls как текст.
- qwen3.5:4b вызывал tools, но показал нестабильное agent behaviour.
- gpt-oss:20b успешно прошёл smoke-test с последовательностью glob → grep → read.

С учётом MacBook Air M5 и 24 GB unified memory, gpt-oss:20b (MXFP4, ~13 GB) укладывается в память и стабильно вызывает инструменты.

## OpenCode setup
- Build как рабочий облачный агент.
- local-guide как отдельный локальный read-only subagent.
- model: `ollama/itmo-agent`.
- Разрешены только `read`, `glob`, `grep`.
- Изменение файлов, bash и web запрещены.
- Эталонные ответы остаются у Build и local-guide их не видит.

## Method
- Gold answers подготовлены до эксперимента.
- Smoke-test выполнен отдельно и не входит в пять результатов.
- 5 вопросов запускались в независимых subagent sessions; история не передавалась.
- Один вопрос не имеет ответа в репозитории.
- Один содержит ложную предпосылку.

## Results

| # | Question | Expected answer | Local model answer | Tools used | Result |
|---|---|---|---|---|---|
| 1 | Что возвращает функция subscribe при успешной подписке? | {"subscribed": True} | Функция `subscribe` объявлена в файле `demo/service.py`.  На строках 4‑8 реализована логика подписки:  ```python\ndef subscribe(name):\n    if not name.strip():\n        raise ValueError("empty name")\n    subscribers.add(name.strip())\n    return {"subscribed": True}\n```  При успешной подписке возвращается словарь `{"subscribed": True}`. | glob, grep, read | CORRECT |
| 2 | Что произойдёт, если передать в subscribe строку, состоящую только из пробелов? | Выбрасывается `ValueError("empty name")` | При передаче в `subscribe` строки, состоящей только из пробелов, будет вызвано исключение `ValueError`. Объяснение проверкой:  ```\nif not name.strip():\n    raise ValueError("empty name")\n```  (файл `demo/service.py`, строки 4–7). | glob, grep, read | CORRECT |
| 3 | Что произойдёт с количеством подписчиков, если дважды вызвать subscribe("Ann")? | Останется 1 | Коллекция подписчиков реализована как `set`, поэтому добавление одного и того же имени дважды не приводит к дублированию. После двух вызовов  ```python\nsubscribe("Ann")\nsubscribe("Ann")\n```  в `subscribers` останется ровно одно имя, т.е. длина множества будет `1`.  * `service.py` – определение функции `subscribe` (строка 7‑8).  * `test_service.py` – проверка, что после двух вызовов длина множества `subscribers` равна 1 (строки 18‑20). | glob, grep, read | CORRECT |
| 4 | Какая лицензия используется в этом проекте? | Лицензия не указана в репозитории | В репозитории отсутствует указание лицензии.  – Файла `LICENSE` нет.  – В `README.md` лицензии не упоминается. | glob, grep, read | CORRECT |
| 5 | Какой HTTP endpoint используется сервисом для создания новой подписки? | HTTP API отсутствует; ложная предпосылка |  | — | INCORRECT |

Примечание: в строке 5 столбец "Local model answer" пуст, так как subagent не вернул финальный ответ на повторном запуске с тем же вопросом.

## Analysis
- CORRECT / PARTIAL / INCORRECT: 4 / 0 / 1.
- Нахождение релевантных файлов: уверенно в 4/5 вопросов.
- Использование tools: стабильно (glob → grep → read) в успешных случаях; один запуск завершился без ответа.
- Галлюцинации: не наблюдались в успешных ответах.
- Обработка отсутствия информации: по лицензии корректно указано отсутствие данных.
- Распознавание ложной предпосылки: по HTTP endpoint не выполнено (ответ отсутствует вместо явного указания).
- Ограничения: единичная нестабильность на вопросе с ложной предпосылкой; локальный цикл инструментов в целом предсказуем.

## Problems and limitations
- Совместимость локальной модели с agent/tool calling существенна; устойчивость важнее размера.
- Более крупная модель не обязательно лучше как coding agent; ранние эксперименты это показали.
- Локальный inference и tool loop могут быть менее предсказуемыми (один пустой ответ).
- Repository/system инструкции заметно влияют на поведение локальной модели.

## Conclusion
gpt-oss:20b пригоден как локальный read-only помощник по небольшому репозиторию: 4 из 5 ответов корректны, с указанием файлов/строк. Требуются доработки устойчивости в случаях ложных предпосылок.

## Verification

Результат `make test`:

```
test_duplicate (test_service.SubscribeTest.test_duplicate) ... ok
test_empty (test_service.SubscribeTest.test_empty) ... ok
test_subscribe (test_service.SubscribeTest.test_subscribe) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.000s

OK
```
