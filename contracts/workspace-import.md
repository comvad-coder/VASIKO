# Workspace import contract

```text
input: ZIP archive + workspace_id + product_id
output: isolated workspace manifest + import report
```

Порядок: validate archive → validate entries → preserve original → extract safely → detect stack → write report → create backup before future changes.

Запрещены абсолютные пути, `..`, symlink, encrypted ZIP, secret-like files, превышение размера архива, числа файлов, размера файла, общего распакованного объёма и compression ratio.
