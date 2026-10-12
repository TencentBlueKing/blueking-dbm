# MongoDB 实例状态与成员状态

`StorageInstance.status` 和 `MongoDBStorageInstanceExt.state` / `state_code` 不是同一个字段。

| 字段 | 表 | 含义 |
|---|---|---|
| `StorageInstance.status` | 存储实例 | 平台实例状态：`running`、`unavailable`、`upgrading` 等 |
| `ProxyInstance.status` | 接入实例（mongos） | 同上，没有成员状态 |
| `MongoDBStorageInstanceExt.state` | 存储实例扩展 | 副本集成员状态名，如 `SECONDARY` |
| `MongoDBStorageInstanceExt.state_code` | 存储实例扩展 | 成员状态码，如 `2` |

mongos 只有实例状态，没有 `MongoDBStorageInstanceExt`。

同步任务平时只改成员状态。它改实例状态的唯一路径，是「`unavailable` 且成员已是 `SECONDARY` → `running`」。

## 成员状态

只有两分钟一次的 `mongodb_sync_instance_status_task` 在写。新建扩展行的默认值是 `state=UNKNOWN`、`state_code=-1`。

状态码定义在 `MongoDBStorageInstanceStatus`：

| 码 | 名称 |
|---|---|
| 0 | STARTUP |
| 1 | PRIMARY |
| 2 | SECONDARY |
| 3 | RECOVERING |
| 4 | FATAL |
| 5 | STARTUP2 |
| 6 | UNKNOWN |
| 7 | ARBITER |
| 8 | DOWN |
| 9 | ROLLBACK |
| 10 | REMOVED |
| -1 | NOT_INITIALIZED |
| 99 | OTHER |

变化场景：

- 本机 `my_state` 有值，且和库里的 `state_code` 不同：写成指标值。
- 本机不再上报，库里还不是 DOWN、UNKNOWN：写成 UNKNOWN。
- 本机不再上报，库里已经是 DOWN 或 UNKNOWN：保持不动，避免和旁观者互相改。
- 旁观者覆盖：多个成员看到的异常状态会写上。已经是 DOWN 时，不会被 UNKNOWN 降回去。

这几步都不改 `StorageInstance.status`。成员回到 `SECONDARY` 之后，是否把实例状态从 `unavailable` 改回 `running`，由下面的同步规则单独处理。

## 实例状态

枚举是 `InstanceStatus`：`running`、`unavailable`、`available`、`restoring`、`upgrading`、`operating`。MongoDB 流程会写 `running`、`unavailable`、`upgrading`、`operating`。`available`、`restoring` 没有 MongoDB 写入点。

| 场景 | 写成 | 写法 |
|---|---|---|
| 新实例入库（替换、扩容、容量变更的新节点） | `running` | 创建元数据 |
| 被换下的旧实例（整机替换、容量变更） | `unavailable` | 直接改字段 |
| DBHA `update_status` | 上报值，故障时为 `unavailable` | `save()` |
| 集群启用 / 禁用 | 副本集改全部存储实例；分片集群改全部 mongos。启用 `running`，禁用 `unavailable` | `update()` |
| PRE 判定替换或拉起 | 故障实例 `operating`；跟单创建失败时改回 `unavailable` | `QuerySet.update` |
| 滚动重启 | 停之前 `operating`，起来之后 `running` | `QuerySet.update` |
| 版本升级 | 先 `upgrading`，再 `running` | `QuerySet.update` |
| 进程拉起、状态修复 | 不是 `running` 的改成 `running` | `save()` 或按地址 `update()` |
| 状态同步 | 仅 `unavailable` 且成员状态已是 `SECONDARY` 时改成 `running`；`operating` 不改 | `QuerySet.update` |

`QuerySet.update` 不触发 `post_save`。`save()` 会触发 `update_cluster_status`。

DBHA 用的是 `save()`。MongoDB 的集群 `status_flag` 没有按实例状态实现，信号里这个标志是 0，会先把集群算成 `normal`。`update_status` 在实例保存之后，若上报的是 `unavailable`，再把集群写成 `abnormal`。

PRE、滚动重启、版本升级、状态同步走 `update()`，不经过这条集群状态信号。

## 集群状态

`Cluster.status` 只有三个值：`normal`（正常）、`abnormal`（异常）、`temporary`（临时）。默认是 `normal`。MongoDB 不用 `temporary`，这个值是给 Spider 定点构造用的。

启用和禁用改的是另一个字段 `Cluster.phase`（`online` / `offline`），不改 `status`。

| 场景 | 写成 |
|---|---|
| 副本集、分片集群创建 | `normal`。创建过程中 `phase` 先是 `offline`，元数据写完再改成 `online` |
| DBHA `update_status` 把实例上报为 `unavailable` | `abnormal`。实例 `save()` 会先按信号把集群算成 `normal`，随后这段代码再写成 `abnormal` |
| 存储实例或 mongos 发生 `save()`、删除，或改了和集群的关联 | 信号把集群写成 `normal`。MongoDB 的 `status_flag` 没有实现，标志恒为 0，所以只要不是 `temporary`，信号的结果就是 `normal` |
| 进程拉起最后一步 `restore_mongo_cluster_status` | 集群不是 `temporary`、当前不是 `normal`、并且全部 storage / proxy 都是 `running` 时，写成 `normal`。没有实例的集群不改 |

实例状态用 `QuerySet.update` 修改时，不会触发上面的信号，集群 `status` 保持不动。

## 集群禁用与 Autofix

当前 Autofix 的发现、PRE 分诊和跟单阶段都没有统一检查 `Cluster.phase`。因此，`phase=offline` 本身不会终止已有 Autofix，也不会直接阻止新 Autofix。

- 副本集禁用时，流程先把全部 storage 实例改成 `unavailable`，再停 mongod。mongod 故障发现只加载 `status=running` 的 storage，因此禁用完成后通常不会发现新的副本集故障。
- 分片集群禁用时，只把 mongos 改成 `unavailable` 并停止 mongos；shard 和 config storage 仍是 `running`。因此，后端 mongod/config 的故障发现仍可能创建 Autofix。
- mongos 故障来自 DBHA 切换队列。禁用后的 mongos 是 `unavailable`，正常情况下不会继续进入 DBHA 探测；但 Autofix 消费队列时不检查集群 `phase`，已经进入队列的事件仍可能创建 PRE 单。
- 禁用前已经存在的 `MongoAutofixCore`、PRE 单和跟单不会因为 `phase=offline` 自动取消，周期任务仍会继续同步和推进。

所以当前行为不是“禁用集群就全面停止 Autofix”，而是主要依靠实例变成 `unavailable`，间接阻止部分新故障进入发现阶段。若要求禁用后完全停止自愈，应在 mongod 和 mongos 的发现入口统一过滤 `cluster.phase=offline`，并明确已有 Core/单据是继续、暂停还是取消。
