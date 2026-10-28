---
name: test-and-fix
description: Use ONLY to reproduce failing pytest tests, diagnose root cause in intervals.py and related code, apply a minimal fix, and re-run tests until they pass
---

# Test And Fix

Workflow:

1. Воспроизвести ошибку тестов (использовать доступный MCP tool для запуска тестов или make test)
2. Проанализировать падающий тест и связанный production code (основной модуль: intervals.py)
3. Определить корневую причину проблемы, не подгонять код под assertion
4. Внести минимальную и корректную правку кода
5. Не изменять тесты, за исключением очевидно ошибочного теста
6. Запустить проверку через доступный project test MCP tool
7. Если тесты продолжают падать — повторить цикл диагностики и исправления
8. В конце кратко объяснить причину ошибки и сделанное исправление
