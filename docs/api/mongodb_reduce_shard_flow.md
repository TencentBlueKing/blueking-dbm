# MongoDB：缩容分片数（multi_cluster_reduce_shard）

> **同步说明**：本文与代码实现保持一致。

## 概述

- **用途**：对 MongoDB **分片集群**减少分片数量（整片移除），支持两种入参模式：
  1. **指定分片**（默认）：显式传入待缩容的分片名列表
  2. **指定数量**：传入缩容数量，**从 shard 编号大的开始**选取并缩容
- **入口形态**：Scene 直调 `POST /v1/flow/scene/multi_cluster_reduce_shard`（运维/测试）
- **代码位置**：
  - 视图：[`dbm-ui/backend/flow/views/mongodb_scene.py`](../../dbm-ui/backend/flow/views/mongodb_scene.py)（`MongoDBClusterReduceShardView`）
  - 控制器：[`dbm-ui/backend/flow/engine/controller/mongodb.py`](../../dbm-ui/backend/flow/engine/controller/mongodb.py)（`cluster_reduce_shard`）
  - 主流程：[`dbm-ui/backend/flow/engine/bamboo/scene/mongodb/mongodb_cluster_reduce_shard.py`](../../dbm-ui/backend/flow/engine/bamboo/scene/mongodb/mongodb_cluster_reduce_shard.py)
  - 入参校验 / 分片解析：[`dbm-ui/backend/flow/utils/mongodb/calculate_cluster.py`](../../dbm-ui/backend/flow/utils/mongodb/calculate_cluster.py)（`calculate_cluster_reduce_shard`）
  - 子任务：[`dbm-ui/backend/flow/engine/bamboo/scene/mongodb/sub_task/cluster_reduce_shard.py`](../../dbm-ui/backend/flow/engine/bamboo/scene/mongodb/sub_task/cluster_reduce_shard.py)
  - Meta 清理：[`dbm-ui/backend/db_meta/api/cluster/mongocluster/reduce_shard.py`](../../dbm-ui/backend/db_meta/api/cluster/mongocluster/reduce_shard.py)
  - Actuator：`dbm-services/mongodb/db-tools/dbactuator/.../remove_shard_from_cluster.go`

关联查询接口：[mongodb_list_cluster_shards](./mongodb_list_cluster_shards.md)（指定分片模式下拉）。

---

## 接口说明

| 项目 | 说明 |
|------|------|
| Method | `POST` |
| Path | `/v1/flow/scene/multi_cluster_reduce_shard` |
| Content-Type | `application/json` |
| 鉴权 | `FlowTestView`：`login_exempt` + `AllowAny`（以实际部署登录策略为准） |

### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `uid` | string | 是 | 任务唯一标识，**不可为空**。建议 `{场景}-{bk_biz_id}-{日期}-{后缀}` |
| `bk_biz_id` | int | 是 | 蓝鲸业务 ID |
| `created_by` | string | 是 | 发起人 |
| `infos` | array | 是 | 非空；每个元素对应一个待缩容集群，见下表 |
| `bk_cloud_id` | int | 否 | 云区域 ID（可在 `infos[]` 内覆盖） |
| `ticket_id` | string | 否 | 关联单据 ID |
| `ticket_type` | string | 否 | 默认 `MongoDBReduceShardFlow` |
| `bk_app_abbr` | string | 否 | 业务英文缩写 |

#### `infos[]` 公共字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cluster_id` | int | 是 | 分片集群 ID（≥ 1） |
| `reduce_mode` | string | 否 | `by_shard_names`（默认）或 `by_count` |
| `bk_cloud_id` | int | 否 | 未传时从集群元数据读取 |

#### 模式 A：指定分片（默认）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `reduce_mode` | string | 否 | `by_shard_names` 或省略 |
| `shard_names` | string[] | 是 | 待缩容分片名列表（非空，不可重复） |

`reduce_shards_num` 若传入会被忽略。

#### 模式 B：指定数量

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `reduce_mode` | string | 是 | 固定 `by_count` |
| `reduce_shards_num` | int | 是 | 缩容分片数量（≥ 1） |

按分片名**尾部数字升序**后，取编号最大的 N 个作为待缩容分片。`shard_names` 若传入会被忽略。

---

## 业务校验

| 规则 | 说明 |
|------|------|
| 集群存在且类型正确 | 必须为 `MongoShardedCluster` |
| 分片名有效 | 指定模式下名称必须存在于集群 |
| 不可删 configsvr | 配置服务器分片不可被选中 |
| 至少保留 1 片 | 缩容后剩余数据分片数 ≥ 1（指定数量：`reduce_shards_num < 当前分片数`） |
| 剩余部署均衡 | **指定分片 / 指定数量均校验**。缩容后主机剩余实例数可为 **0**（回收机器）；仍有实例的主机，剩余分片实例数必须一致。例：3 组机器共 6 片、单机 2 片时，可缩 2/4/5，不可缩 1/3 |

补充说明：

- 若集群**当前**已不均衡（例如各组单机片数已是 2/2/1），多数缩容方案会因「剩余仍不均衡」被拒绝；需先按可留下均匀片数的方式缩（如先缩掉多余的那 1 片组）。
- 指定数量按分片名**尾部数字**排序后取编号最大的 N 个；无尾部数字的分片名排序键视为 `0`，顺序不稳定，生产命名请保持 `*-sN` 等规范。

---

## 流程行为

单集群子流程顺序：

1. 介质下发（mongos + 待删分片主机）
2. 创建原子任务执行目录
3. 获取管理密码
4. 打开 balancer（`waitForBalance=false`）
5. `removeShard`（dbactuator）
6. **人工确认**（Pause）
7. 多实例卸载（mongod）
8. 删除密码
9. Meta 清理
10. 关闭 balancer

多集群：`infos` 中多个集群以并行子流水线执行。

---

## 请求示例

### 指定分片（默认）

```json
{
  "uid": "mongo-reduce-shard-3-20260804-001",
  "bk_biz_id": 3,
  "bk_cloud_id": 0,
  "created_by": "admin",
  "infos": [
    {
      "cluster_id": 1001,
      "reduce_mode": "by_shard_names",
      "shard_names": ["demo-s2", "demo-s3"]
    }
  ]
}
```

### 指定数量（从大编号缩）

```json
{
  "uid": "mongo-reduce-shard-3-20260804-002",
  "bk_biz_id": 3,
  "created_by": "admin",
  "infos": [
    {
      "cluster_id": 1001,
      "reduce_mode": "by_count",
      "reduce_shards_num": 2
    }
  ]
}
```

若集群分片为 `demo-s1` / `demo-s2` / `demo-s3`，则等价于缩容 `demo-s2`、`demo-s3`。

### cURL

```bash
curl -sS -X POST "https://{host}/v1/flow/scene/multi_cluster_reduce_shard" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

## 响应示例

### 成功

```json
{
  "root_id": "a1b2c3d4e5f64789a0b1c2d3e4f50617"
}
```

### 失败（参数校验示例）

```json
{
  "result": false,
  "code": 8700100,
  "data": null,
  "message": "shard_names is required when reduce_mode=by_shard_names"
}
```

（具体 `code` / 外层封装以运行环境为准。业务逻辑错误也可能以 `ValueError` 形式在 flow 启动阶段抛出。）

---

## 备注

- **勿与** `MONGODB_REDUCE_SHARD_NODES`（缩容每分片**节点数**）混淆；本接口是减少分片**个数**。
- `uid` 会写入 dbactuator 工作目录，禁止空字符串。
- 指定分片名可通过 [list_cluster_shards](./mongodb_list_cluster_shards.md) 获取；按数量缩容时可取 `shard_list` 末尾 N 个做预览。
