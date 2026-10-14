# dbactuator 单元/集成测试与环境变量

`go test ./...`（或 `make test`）默认**不需要**设置任何环境变量即可跑通大部分用例。

以下为**可选**环境变量：仅用于开启「依赖本机环境」的集成/冒烟测试；未设置时对应测试会跳过或行为见说明。

## 1. `RUN_DF_SMOKE_TEST`


| 项      | 说明                                                                                             |
| ------ | ---------------------------------------------------------------------------------------------- |
| **用途** | 开启 `pkg/atomjobs/atommongodb` 中 `TestDf`：对本机 `**/`** 执行真实 `df -B1 -P`（经 `env LC_ALL=C`），并解析输出。 |
| **取值** | 设为 `**1`** 时执行；其它或未设置则 `**Skip`**。                                                             |
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


| 变量                | 用途                                                       |
| ----------------- | -------------------------------------------------------- |
| `TEST_MONGO_HOST` | 测试中传给 `execScript()` 的 Mongo 地址（默认 `127.0.0.1`）。         |
| `TEST_MONGO_PORT` | 测试中传给 `execScript()` 的 Mongo 端口（默认 `27017`）。             |
| `TEST_MONGO_USER` | 测试中传给 `execScript()` 的 Mongo 用户名（默认 `admin`）。            |
| `TEST_MONGO_PASS` | 测试中传给 `execScript()` 的 Mongo 密码（默认 `super-secret-pass`）。 |



| 项      | 说明                                                       |
| ------ | -------------------------------------------------------- |
| **用途** | 用于 `mongo_execute_script_test.go` 中“仅执行 js 脚本步骤”的单测输入参数。 |
| **取值** | 未设置时使用默认值；`TEST_MONGO_PORT` 需为整数。                        |
| **文件** | `pkg/atomjobs/atommongodb/mongo_execute_script_test.go`  |


## 5. 与「运行二进制」相关、非测试专用

生产/运行时代码中的 `os.Getenv`（如 `MONGO_DATA_DIR`、`MONGO_BACKUP_DIR`、`REDIS`_*、`PROCESS_EXEC_USER` 等）见 `pkg/consts/` 等；**一般不作为 `go test` 的前置条件**，除非某测试将来显式依赖这些数据目录（当前测试未引用）。

## 6. 本地冒烟：mongo / mongosh 选择

不启动 MongoDB，也不访问资源池。用一个只有 `mongod` 和 `mongosh`、没有 `mongo` 的临时 8.0 安装目录，逐一初始化本次涉及的 actuator 任务并断言任务实际选择了 mongosh：

- 用户、复制集与分片任务：`add_user`、`delete_user`、`init_replicaset`、`replicaset_stepdown`、`mongod_replace`、`mongod_node_hidden`、`add_shard_to_cluster`、`remove_shard_from_cluster`、`cluster_balancer`。
- 实例与升级任务：`mongo_restart`、`mongo_start_process`、`mongo_deinstall`、`mongo_deferred_deinstall`、`mongo_execute_script`、`mongodb_instance_op`、`mongo_set_fcv`、`mongo_upgrade_rs_protocol`。
- 安装任务：`mongod_install`、`mongos_install` 在非 tlinux4 本机验证依赖准备步骤安全跳过；真实 `tos` / `dnf` 留给 tlinux4 E2E。

同时覆盖主版本 `4.4` 使用 mongo、`>= 5` 使用 mongosh，以及 `8.0` 安装目录没有 mongo。

```bash
cd dbm-services/mongodb/db-tools/dbactuator
tests/smoke/mongo_shell_local.sh
```

如果本机 `/usr/local/mongodb/bin/mongod` 存在，脚本还会核对真实安装包里的客户端和主版本一致。

## 7. 核心原子任务集成测试（`tests/integration/`）

在本地用真实 MongoDB 4.4.30 进程，把核心 actuator 原子任务各跑一遍。不覆盖备份/PITR/dbmon/导出等外部依赖任务，但会对照 `mongo-dbactuator debug --list` 做覆盖清单校验，新增未分类任务会失败。

### 命令

```bash
cd dbm-services/mongodb/db-tools/dbactuator
sudo tests/integration/run_core_atoms.sh              # 全量核心集成
sudo tests/integration/run_core_atoms.sh --preflight  # 只检查前置条件
sudo tests/integration/run_core_atoms.sh --cleanup-only
sudo tests/integration/run_core_atoms.sh --keep-on-failure
```

### 前置条件

- root
- Go、python3、rg、netstat、ip
- OS 用户 `mysql`（可用 `TEST_OS_INIT_USER` 覆盖）
- 介质 `/data/install/mongodb-linux-x86_64-rhel70-4.4.30.tar.gz`，md5=`0856af7ed34231d4b533581c11d9ebe6`
- 可写目录 `/data/mongo_actuator_lab`（可用 `TEST_LAB_ROOT` 覆盖）

### 默认拓扑与端口

| 沙箱 | IP | 端口 |
|------|----|------|
| 复制集 3+1 | `127.0.0.71`–`.74` | `27517`–`27520` |
| configsvr x3 | `127.0.0.81`–`.83` | `27617`–`27619` |
| shard1 x3 | `127.0.0.91`–`.93` | `27717`–`27719` |
| shard2 x3 | `127.0.0.94`–`.96` | `27817`–`27819` |
| mongos | `127.0.0.97` | `27917` |

端口必须落在 actuator 允许范围 `[27000, 29999]`。

脚本会自动给 `lo` 添加上述别名。数据/二进制/工作目录默认在 `/data/mongo_actuator_lab/<run_id>/`。

### 覆盖范围

必跑（22）：`os_mongo_init`、`mongodb_hello`、`mongod_install`、`mongos_install`、`init_replicaset`、`add_user`、`delete_user`、`mongo_execute_script`、`replicaset_stepdown`、`mongod_node_hidden`、`mongo_restart`、`mongo_start`、`mongodb_instance_op`、`mongo_set_fcv`、`mongo_upgrade_rs_protocol`、`replace_package`（同版本幂等）、`mongod_replace`、`mongo_deferred_deinstall`、`add_shard_to_cluster`、`cluster_balancer`、`remove_shard_from_cluster`、`mongo_deinstall`。

显式跳过（7）：`mongodb_backup`、`mongodb_restore`、`mongodb_pitr_restore`、`mongodb_pitr_rebuild`、`mongodb_remove_ns`、`install_dbmon`、`mongodb_data_export`。

### 破坏面与恢复

- 会改 `vm.swappiness` / `kernel.pid_max`（退出时尽量恢复）。
- 会在 `/data/install` 使用现有介质，并在 lab 目录下写数据/日志。
- 失败默认清理实例；`--keep-on-failure` 保留现场，之后用 `--cleanup-only`（可设 `TEST_RUN_DIR`）清理。
- 产物：`work/coverage.tsv`、`work/logs/`。

## 8. E2E 脚本（`tests/e2e/*.sh`）

以下脚本需要在 `dbm-services/mongodb/db-tools/dbactuator` 目录执行，且通常要求 `root`（脚本内部会检查 `EUID`）：


| 脚本                                                   | 用途                                                   | 关键默认变量                                                                                                            |
| ---------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `tests/e2e/mongo_single_node_lifecycle.sh`           | 单节点副本集安装/初始化/加用户/卸载全流程                               | `TEST_PORT`、`TEST_DATA_DIR`、`TEST_BACKUP_DIR`、`TEST_BIN_DIR`                                                      |
| `tests/e2e/mongo_three_node_replicaset_lifecycle.sh` | 三节点副本集生命周期                                           | `TEST_BASE_PORT`、`TEST_DATA_DIR`、`TEST_BACKUP_DIR`                                                                |
| `tests/e2e/mongo_sharded_cluster_deploy.sh`          | 分片集群部署与验收                                            | `TEST_MONGOS_PORT`、`TEST_CONFIGSVR_PORT`、`TEST_SHARD_BASE_PORT`                                                   |
| `tests/e2e/mongo_add_user_idempotent.sh`             | `add_user` 幂等与不匹配失败验证                                | `TEST_PORT`、`TEST_ADMIN_USER`、`TEST_ADMIN_PASS`                                                                   |
| `tests/e2e/mongo_os_init_e2e.sh`                     | `os_mongo_init` / `mongo_init_shell` 验证（目录、锁文件、内核参数） | `TEST_OS_INIT_USER`、`TEST_OS_INIT_GROUP`、`TEST_OS_INIT_PASSWORD`、`TEST_DATA_DIR`、`TEST_BACKUP_DIR`、`TEST_BIN_DIR` |
| `tests/e2e/mongo_instance_op_graceful_stop.sh`       | `mongodb_instance_op` 的 `gracefulStop=true/false` 停主验证并恢复 | `TEST_PORT1/2/3`、`TEST_NODE1_IP/2_IP/3_IP`、`TEST_DBA_USER`、`TEST_DBA_PASS`、`TEST_DATA_DIR`、`TEST_BACKUP_DIR`、`TEST_BIN_DIR` |


`mongo_os_init_e2e.sh` 额外说明：

- 会校验 `vm.swappiness=0` 和 `kernel.pid_max=200000`。
- 脚本退出时会自动恢复执行前的内核值（`trap cleanup EXIT`）。

示例：

```bash
cd dbm-services/mongodb/db-tools/dbactuator
sudo TEST_OS_INIT_USER=mongoosinit TEST_OS_INIT_GROUP=mongoosinit \
  tests/e2e/mongo_os_init_e2e.sh
```

