# handler

请求里的 SQL 文件名是不可信输入。使用前必须校验，禁止拼进 shell。

- `files`、`execute_objects[].sql_files`、`schema_sql_file` 以及从 path 取出的文件名，先走 `pkg/util.ValidateSQLFileName`，落到工作目录时走 `pkg/util.SQLFilePath`。
- 只接受单个文件名。拒绝空串、`.`、`..`、`/`、`\` 和控制字符。
- 调 `tmysqlparse` 或其他外部命令时，文件名放进参数数组，沿用 `getCommandArgs`。不要用 `sh -c`，也不要把文件名格式化进一条 shell 命令。
