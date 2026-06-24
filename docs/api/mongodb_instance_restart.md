# MongoDB：实例重启（multi_instance_restart / MONGODB_INSTANCE_RELOAD）

> **同步说明**：本文与代码实现保持一致。

## 概述

- **用途**：对 MongoDB 副本集或分片集群执行**滚动重启**——RS 内节点串行、多 RS 并行；分片集群按 **shard RS 并行 → config RS 串行 → mongos 并行** 分阶段执行。
- **入口形态**：
  1. **Scene 直调**：`POST /v1/flow/scene/multi_instance_restart`（运维/测试）
  2. **工具箱单据**：`MONGODB_INSTANCE_RELOAD`（MongoDB 实例重启），审批通过后由 Builder 调用同一 Flow
- **代码位置**：
  - 视图：[`dbm-ui/backend/flow/views/mongodb_scene.py`](../../dbm-ui/backend/flow/views/mongodb_scene.py)（`MongoDBInstanceRestartView`）
  - 控制器：[`dbm-ui/backend/flow/engine/controller/mongodb.py`](../../dbm-ui/backend/flow/engine/controller/mongodb.py)（`instance_restart`）
  - 主流程：[`dbm-ui/backend/flow/engine/bamboo/scene/mongodb/mongodb_instance_restart.py`](../../dbm-ui/backend/flow/engine/bamboo/scene/mongodb/mongodb_instance_restart.py)
  - 子任务：[`dbm-ui/backend/flow/engine/bamboo/scene/mongodb/sub_task/rolling_restart.py`](../../dbm-ui/backend/flow/engine/bamboo/scene/mongodb/sub_task/rolling_restart.py)
  - 目标解析 / 入参校验：[`dbm-ui/backend/flow/utils/mongodb/restart_target_resolver.py`](../../dbm-ui/backend/flow/utils/mongodb/restart_target_resolver.py)
  - 单据 Builder：[`dbm-ui/backend/ticket/builders/mongodb/mongo_instance_reload.py`](../../dbm-ui/backend/ticket/builders/mongodb/mongo_instance_reload.py)

---

## 接口说明

| 项目 | 说明 |
|------|------|
| Method | `POST` |
| Path | `/v1/flow/scene/multi_instance_restart` |
| Content-Type | `application/json` |
| 鉴权 | `FlowTestView`：`login_exempt` + `AllowAny`（以实际部署登录策略为准） |
| 单据 | 审批通过后 `FlowTree.uid` 为 ticket id |

### 请求体（JSON）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `uid` | int / string | 建议 | 自动生成 | 任务唯一标识，传给 dbactuator。**不可为空**；Scene 建议 `{场景}-{bk_biz_id}-{日期}-{后缀}` |
| `bk_biz_id` | int | 是 | — | 蓝鲸业务 ID |
| `bk_cloud_id` | int | 条件 | — | 云区域 ID；Scene 直调必填；单据可从 `infos[].bk_cloud_id` 推断 |
| `created_by` | string | 是 | — | 发起人 |
| `infos` | array | 是 | — | 重启目标列表，见下表；**同请求可混合多种 info 模式** |
| `force` | bool | 否 | `false` | 重启策略开关，详见下文 **[`force` 参数对比](#force-参数对比)** |
| `ticket_type` | string | 否 | `MONGODB_INSTANCE_RELOAD` | 单据路径自动写入 |

#### `infos[]` 元素（四选一）

每个元素使用下列模式之一：

| 模式 | 字段 | 说明 |
|------|------|------|
| **显式实例** | `ip` + `port` + `cluster_id` | 重启单个实例；单据 UI 选实例走此模式 |
| **整集群** | 仅 `cluster_id` | 展开该集群全部 mongod/mongos |
| **主机** | 仅 `ip` | 展开该 IP 上全部 MongoDB 实例 |
| **实例地址** | 仅 `instance`（`ip:port`） | 重启单个实例 |

**工具箱单据**额外字段（`MongoDBInstanceReloadDetailSerializer`）：`bk_host_id`、`instance_id`；Builder 补全 `ip`、`bk_cloud_id`、`role`。

---

## `force` 参数对比

`force` 仅控制 **停服方式** 与 **RS 可用性预检**，**不影响** RS 内节点重启顺序与 Flow 拓扑（仍为 RS 内串行、多 RS 并行）。**生产环境默认使用 `force=false`**。

### RS 内重启顺序（`force` 无关）

无论 `force` 取值，RS 内均采用同一套排序规则：

1. 查询 `MongoDBStorageInstanceExt` 中 `state=PRIMARY` 的实例（巡检任务写入）
2. **若查到 PRIMARY**：其余成员按元数据 `role` 排序（backup → M1 → M2 → …）先重启，**ext 中标记为 PRIMARY 的实例最后重启**
3. **若未查到 PRIMARY**：全部成员按元数据 `role` 顺序重启

| 维度 | `force=false`（默认，推荐） | `force=true`（强制） |
|------|------------------------------|----------------------|
| **适用场景** | 在线滚动重启，尽量保证 RS 可用性与选主安全 | 应急、已知集群不健康、或明确接受可用性风险时 |
| **停服方式** | **graceful**（`gracefulStop=true`） | **非 graceful**（`gracefulStop=false`），直接 SIGINT |
| **RS 可用性预检**（mongod） | **有**：停服前 `replSetGetStatus` 检查其它成员均为 `PRIMARY`/`SECONDARY` 且 `health=1`；且本节点停掉后仍须 **严格过半** 成员存活 | **无** |
| **PRIMARY 处理** | 停服前若本节点为运行时 PRIMARY，执行 `replSetStepDown` → 等待变为 `SECONDARY` → **固定等待 30s** → 再 SIGINT 关停 | 不 stepDown，直接 SIGINT 关停（可能触发短暂无主或异常选主） |
| **mongos** | graceful 停服（无 RS / stepDown 逻辑） | 直接 SIGINT 停服 |
| **启服与就绪** | 相同：`start` 后等待就绪，超时 **300s** | 相同 |

### `force=false` 时 graceful `stop` 内部顺序（actuator）

对 **mongod**（副本集成员），单次 `stop` act 内依次执行：

1. **RS 可用性检查**（mongos / 非 replSet 单机自动跳过）
2. 若当前节点为 **PRIMARY**：`replSetStepDown` → 轮询至 `SECONDARY` → 等待 **30s**
3. 发送 **SIGINT** 优雅关停，直至端口释放（整段 `stop` 超时 **300s**）

Flow 侧不再拆分为多个独立 act，上述逻辑均在 `stop` 内完成。

### `force=true` 风险提示

- 不校验 RS 成员健康与过半 quorum，可能在集群已降级时继续重启，**加剧不可用**。
- PRIMARY 可能在不 stepDown 的情况下被直接关停，存在 **短暂写不可用** 或选主抖动风险。

---

## 流程行为

### 编排拓扑

```
介质下发（全局一次）
└─ 并行（按集群 / RS）
   ├─ 副本集集群：各 RS 子流程并行；RS 内节点子流程串行 → RS 全员就绪检查
   └─ 分片集群（单集群子流程内顺序）：
        1. 全部 shard RS 并行（RS 内串行 → 全员就绪检查）
        2. config RS 串行 → 全员就绪检查
        3. 全部 mongos 并行
```

### 单节点子流程

| 顺序 | 步骤 | 说明 |
|------|------|------|
| 0（`force=false` 的 mongod） | RS 可用性检查 | `check_rs_availability`；RS 串行时确保上一节点已恢复且 quorum 满足后再继续 |
| 1 | 屏蔽 dbmon | `shield_dbmon` |
| 2 | 停实例 | `stop`；`force=false` 时 graceful（含 PRIMARY stepDown 等），且跳过重复 RS 检查 |
| 3 | 启实例并等待就绪 | `start`；传入 `startTimeoutSeconds=300`，启动后自动 `wait_until_ready` |
| 4 | 解除屏蔽 dbmon | `unblock_dbmon` |

- **RS 内顺序**：见 [RS 内重启顺序（`force` 无关）](#rs-内重启顺序force-无关)
- **密码**：启动前对全部目标 **批量** 查询一次（`batch_get_restart_node_credentials`）
- **可重试**：Flow 节点默认 `retryable=true`（`SubBuilder.add_act` 默认值），可在任务详情重试失败步骤；actuator 侧重试最多 **3** 次，且各 op 幂等

### 失败语义

- 单节点任一步失败 → 该节点子流程 FAILED；RS 内后续节点不再执行。
- RS 全部成员滚动重启完成后，执行 **RS 全员就绪检查**（`check_rs_all_members_ready`）：`replSetGetStatus` 要求每个成员均为 `PRIMARY`/`SECONDARY`/`ARBITER` 且 `health=1`。
- 分片集群：任一 shard RS 失败 → 该集群后续 config / mongos 阶段不执行。

---

## 请求示例

### 显式实例（兼容旧接口 / 单据）

```bash
curl -sS -X POST "http://{host}/v1/flow/scene/multi_instance_restart" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "mongo-instance-restart-3-20260624-001",
    "bk_biz_id": 3,
    "bk_cloud_id": 0,
    "created_by": "admin",
    "force": false,
    "infos": [
      {"ip": "127.0.0.1", "port": 27001, "cluster_id": 19, "role": "mongodb"}
    ]
  }'
```

### 按 cluster_id 整集群滚动

```json
{
  "uid": "mongo-instance-restart-3-20260624-002",
  "bk_biz_id": 3,
  "bk_cloud_id": 0,
  "created_by": "admin",
  "force": false,
  "infos": [{"cluster_id": 19}]
}
```

### 按 IP 滚动该主机全部实例

```json
{
  "uid": "mongo-instance-restart-3-20260624-003",
  "bk_biz_id": 3,
  "bk_cloud_id": 0,
  "created_by": "admin",
  "infos": [{"ip": "127.0.0.2"}]
}
```

### manage.py shell

**1. 显式实例**

```python
import uuid

from backend.flow.engine.controller.mongodb import MongoDBController

payload = {
    "uid": "mongo-instance-restart-3-20260624-001",
    "bk_biz_id": 3,
    "bk_cloud_id": 0,
    "created_by": "admin",
    "force": False,
    "infos": [
        {"ip": "127.0.0.1", "port": 27001, "cluster_id": 19, "role": "mongodb"},
    ],
}

root_id = uuid.uuid1().hex
print("root_id:", root_id)

MongoDBController(root_id=root_id, ticket_data=payload).instance_restart()
```

**2. 整集群（cluster_id）**

```python
import uuid

from backend.flow.engine.controller.mongodb import MongoDBController

payload = {
    "uid": "mongo-instance-restart-3-20260624-002",
    "bk_biz_id": 3,
    "bk_cloud_id": 0,
    "created_by": "admin",
    "force": False,
    "infos": [{"cluster_id": 19}],
}

root_id = uuid.uuid1().hex
print("root_id:", root_id)

MongoDBController(root_id=root_id, ticket_data=payload).instance_restart()
```

**3. 按 IP 滚动该主机全部实例**

```python
import uuid

from backend.flow.engine.controller.mongodb import MongoDBController

payload = {
    "uid": "mongo-instance-restart-3-20260624-003",
    "bk_biz_id": 3,
    "bk_cloud_id": 0,
    "created_by": "admin",
    "force": False,
    "infos": [{"ip": "127.0.0.2"}],
}

root_id = uuid.uuid1().hex
print("root_id:", root_id)

MongoDBController(root_id=root_id, ticket_data=payload).instance_restart()
```

---

## 校验与错误

| 场景 | 表现 |
|------|------|
| `infos` 为空 | Serializer 校验失败 |
| info 字段组合不合法 | Serializer 校验失败 |
| `cluster_id` / 实例在元数据中不存在 | `ValueError` |
| 解析后无实例 | `no MongoDB instances resolved from infos` |
| 密码服务查不到 dba 密码 | `get password from password service failed` |
| `force=false` 且 RS 其它成员不健康 | actuator `stop` 失败：`rs member ... is not healthy before restart` |
| `force=false` 且重启后无法保持过半存活 | actuator `stop` 失败：`strict majority required` |
| `force=false` 且 PRIMARY stepDown 超时 | actuator `stop` 失败：`did not become secondary after rs.stepDown` |
| 目标机 actuator 过旧 | `unknown op` 或缺少 `start` 内建等待就绪逻辑 |

---

## 依赖与备注

1. **mongo-dbactuator** 需支持：`stop`（graceful + RS 检查 + stepDown）、`start`（可选 `startTimeoutSeconds` 内建等待就绪）。
2. 目标机已安装 **bk-dbmon**。
3. 显式实例模式：同一 RS 内仅重启 `infos` 中选中的成员。
4. 单据 Builder 只查 `StorageInstance`；mongos 重启需 Scene 传 `{"cluster_id": N}` 或显式 `infos`。
5. 修改代码后需重启 `runserver` / shell 再触发新 Flow。
6. **`force` 默认 `false`**：工具箱 / Scene 未传时即为安全滚动模式。
