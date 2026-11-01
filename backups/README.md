# VASIKO backups

Этот контур резервирует сам ВАСИКО: Core, Admin, задачи, память, конфигурацию и документацию по выбранной политике. Он не является backup-папкой Palm или другого пользовательского продукта.

```text
backups/
├── vasiko/       # tar.gz snapshots + manifest с SHA-256
├── database/     # зарезервировано для будущей БД
├── n8n/          # зарезервировано для будущих workflow
├── memory/       # зарезервировано для отдельных экспортов памяти
├── modules/      # зарезервировано для registry/modules
└── workspaces/   # зарезервировано для версий рабочих пространств
```

`core.backup_manager.BackupManager` исключает Git, virtualenv, кэши, вложенные backup-архивы, `.env`, credentials, пароли, токены, secrets и приватные ключи по имени пути. Сгенерированные `.tar.gz` и manifest не коммитятся в GitHub.

Каждый snapshot имеет timestamp, version, file count и SHA-256. Перед recovery создаётся отдельный `pre-restore` snapshot. Полное восстановление требует явного approval.
