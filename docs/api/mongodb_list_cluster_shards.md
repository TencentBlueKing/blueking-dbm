# MongoDB：查询集群分片列表（list_cluster_shards）

> **同步说明**：本文与代码实现保持一致，可整篇复制到团队文档平台进行发布；需具备对应页面编辑权限。

## 概述

- **用途**：根据一个或多个集群 ID，查询 MongoDB **分片集群**的数据分片名列表，供缩容分片数「指定分片」下拉多选，以及「指定数量」模式下预览待缩容分片。
- **排序**：分片名按名称**尾部数字**升序排列（与缩容 flow 中 `get_shards(sort_by_set_name=True)` 一致）。
- **范围**：仅返回数据分片（不含 configsvr）。
- **代码位置**：
  - 视图：[`dbm-ui/backend/db_services/mongodb/toolbox/views.py`](../../dbm-ui/backend/db_services/mongodb/toolbox/views.py)（`ToolboxViewSet.list_cluster_shards`）
  - 入参：[`dbm-ui/backend/db_services/mongodb/toolbox/serializers.py`](../../dbm-ui/backend/db_services/mongodb/toolbox/serializers.py)（`ListClusterShardsSerializer`）
  - 逻辑：[`dbm-ui/backend/db_services/mongodb/toolbox/handlers.py`](../../dbm-ui/backend/db_services/mongodb/toolbox/handlers.py)（`ToolboxHandler.list_cluster_shards`）

关联场景文档：[mongodb_reduce_shard_flow](./mongodb_reduce_shard_flow.md)。

## 接口说明

| 项目 | 说明 |
|------|------|
| Method | `GET` |
| Path | `/apis/mongodb/bizs/{bk_biz_id}/toolbox/list_cluster_shards/` |
| Swagger 标签 | `db_services/mongodb/toolbox` |
| 分页 | 无（`pagination_class=None`） |

### 路径参数

| 名称 | 类型 | 说明 |
|------|------|------|
| `bk_biz_id` | int | 蓝鲸业务 ID（路径中） |

### 查询参数（Query）

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cluster_ids` | int[] | 是 | 集群 ID 列表。DRF 中通过**同名参数重复**传递，例如 `cluster_ids=1&cluster_ids=2`。至少 1 个，不可为空列表。 |

### 权限与鉴权

- ViewSet 默认使用 `DBManagePermission`（与 `list_available_versions` 相同；以实际 IAM / 登录态为准）。

### 业务校验与错误

- 缺少 `cluster_ids`：参数校验失败。
- 任一 `cluster_id` 在元数据中不存在：校验失败（「集群不存在」）。
- 任一集群不是 `MongoShardedCluster`：校验失败（「不是分片集群」）。
- 集群无数据分片时：该集群 `shard_list` 为 `[]`（成功返回）。

## 响应说明

外层结构以项目统一封装为准，常见字段包括：

| 字段 | 类型 | 说明 |
|------|------|------|
| `result` | boolean | 是否成功 |
| `code` | int | 业务码，`0` 通常表示成功 |
| `message` | string | 提示信息 |
| `data` | array | 成功时为对象数组，顺序与入参 `cluster_ids` 一致 |

### `data` 数组元素结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `cluster_id` | int | 集群 ID |
| `immute_domain` | string | 集群主域名 |
| `shard_list` | string[] | 数据分片名列表，按尾部数字升序 |

#### 示例（`data` 片段）

```json
[
  {
    "cluster_id": 1001,
    "immute_domain": "demo.mongodb.db",
    "shard_list": ["demo-s1", "demo-s2", "demo-s3"]
  }
]
```

## 请求示例

### cURL（多集群）

```bash
curl -sS -G "https://{host}/apis/mongodb/bizs/2/toolbox/list_cluster_shards/" \
  --data-urlencode "cluster_ids=1001" \
  --data-urlencode "cluster_ids=1002"
```

### cURL（单集群）

```bash
curl -sS -G "https://{host}/apis/mongodb/bizs/2/toolbox/list_cluster_shards/" \
  --data-urlencode "cluster_ids=1001"
```

### Postman

- Method：`GET`
- URL：`https://{host}/apis/mongodb/bizs/{bk_biz_id}/toolbox/list_cluster_shards/`
- **Params**：新增多行同名键 `cluster_ids`，值为各集群 ID。

## 响应示例

### 成功

```json
{
  "result": true,
  "code": 0,
  "data": [
    {
      "cluster_id": 1001,
      "immute_domain": "demo.mongodb.db",
      "shard_list": ["demo-s1", "demo-s2", "demo-s3"]
    }
  ],
  "message": "ok"
}
```

### 失败（参数校验，示例：缺少 cluster_ids）

```json
{
  "result": false,
  "code": 8700100,
  "data": null,
  "message": "{\"cluster_ids\": [\"该字段是必填项。\"]}（8700100）",
  "errors": null
}
```

（具体 `code`、`message` 格式以运行环境为准。）

## 备注

- 与 [`get_mongo_shard`](../../dbm-ui/backend/db_services/mongodb/toolbox/views.py) 的差异：本接口**无分页**，只返回分片名列表；`get_mongo_shard` 返回分片下实例明细且走分页。
- 仅返回路径业务 `bk_biz_id` 下的集群；跨业务 `cluster_id` 视为不存在。
- 缩容「指定数量」预览：对 `shard_list` 取末尾 N 个即为将要从大编号缩容的分片（仍须通过剩余部署均衡等业务校验）。
- 分片名按尾部数字升序；无尾部数字时排序键为 `0`。
- 分片名语义与元数据 `NosqlStorageSetDtl.seg_range` / flow 层 `ReplicaSet.set_name` 一致。
