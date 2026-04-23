# dbactuator 单元/集成测试与环境变量

`go test ./...`（或 `make test`）默认**不需要**设置任何环境变量即可跑通大部分用例。

以下为**可选**环境变量：仅用于开启「依赖本机环境」的集成/冒烟测试；未设置时对应测试会跳过或行为见说明。

## 1. `RUN_DF_SMOKE_TEST`


| 项      | 说明                                                                                             |
| ------ | ---------------------------------------------------------------------------------------------- |
| **用途** | 开启 `pkg/atomjobs/atommongodb` 中 `TestDf`：对本机 `**/`** 执行真实 `df -B1 -P`（经 `env LC_ALL=C`），并解析输出。 |
| **取值** | 设为 `**1`** 时执行；其它或未设置则 `**Skip**`。                                                             |
| **文件** | `pkg/atomjobs/atommongodb/instance_op_df_test.go`                                              |


示例：

```bash
RUN_DF_SMOKE_TEST=1 go test -vet=off ./pkg/atomjobs/atommongodb/... -run '^TestDf$' -v
```

## 2. `TestDump_*`（Mongo 备份集成测试）


| 变量                  | 用途                           |
| ------------------- | ---------------------------- |
| `TestDump_PORT`     | 目标 MongoDB 端口（**必填**，否则整测跳过） |
| `TestDump_HOST`     | 目标主机 IP/主机名                  |
| `TestDump_USER`     | 管理员用户名                       |
| `TestDump_PASS`     | 管理员密码                        |
| `TestDump_FILE_TAG` | 备份 file tag                  |



| 项      | 说明                                                        |
| ------ | --------------------------------------------------------- |
| **用途** | 开启 `TestBackupJob`：走完整 `mongodb_backup` 任务链路（需可达实例与合法参数）。 |
| **取值** | `**TestDump_PORT` 非空** 才执行；为空则 `**Skip`**。                |
| **文件** | `pkg/atomjobs/atommongodb/backup_test.go`                 |


## 3. 无需环境变量的测试


| 包/文件                    | 说明                                    |
| ----------------------- | ------------------------------------- |
| `pkg/common/*_test.go`  | 纯逻辑单测，无 `Getenv`。                     |
| `pkg/util/util_test.go` | 使用 `/tmp` 建临时目录；需本机可写 `/tmp`，无环境变量开关。 |


## 4. `TEST_MONGO_`*（mongo_execute_script 执行步骤单测）


| 变量                | 用途                                               |
| ----------------- | ------------------------------------------------ |
| `TEST_MONGO_HOST` | 测试中传给 `execScript()` 的 Mongo 地址（默认 `127.0.0.1`）。 |
| `TEST_MONGO_PORT` | 测试中传给 `execScript()` 的 Mongo 端口（默认 `27017`）。     |
| `TEST_MONGO_USER` | 测试中传给 `execScript()` 的 Mongo 用户名（默认 `admin`）。      |
| `TEST_MONGO_PASS` | 测试中传给 `execScript()` 的 Mongo 密码（默认 `super-secret-pass`）。 |



| 项      | 说明                                                       |
| ------ | -------------------------------------------------------- |
| **用途** | 用于 `mongo_execute_script_test.go` 中“仅执行 js 脚本步骤”的单测输入参数。 |
| **取值** | 未设置时使用默认值；`TEST_MONGO_PORT` 需为整数。                        |
| **文件** | `pkg/atomjobs/atommongodb/mongo_execute_script_test.go`  |


## 5. 与「运行二进制」相关、非测试专用

生产/运行时代码中的 `os.Getenv`（如 `MONGO_DATA_DIR`、`MONGO_BACKUP_DIR`、`REDIS_`*、`PROCESS_EXEC_USER` 等）见 `pkg/consts/` 等；**一般不作为 `go test` 的前置条件**，除非某测试将来显式依赖这些数据目录（当前测试未引用）。