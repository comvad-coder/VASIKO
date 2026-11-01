# VASIKO memory

Локальная память ВАСИКО разделена по архитектурным категориям:

```text
memory/
├── events/
├── tasks/
├── projects/
├── knowledge/
├── procedures/
├── preferences/
└── exports/
```

`core.memory_store.LocalMemoryStore` поддерживает добавление, поиск, экспорт и удаление записей. Секреты, пароли, токены, credentials, платёжные данные и похожие значения блокируются до записи.

JSONL-файлы памяти являются локальными данными и не коммитятся в GitHub.
