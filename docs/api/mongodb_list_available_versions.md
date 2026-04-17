# MongoDB：查询集群可升级版本列表（list_available_versions）

> **同步说明**：本文与代码实现保持一致，可整篇复制到腾讯内网 iwiki（如 [4019761720](https://iwiki.woa.com/p/4019761720)）进行发布；需具备该页面编辑权限。

## 概述

- **用途**：根据一个或多个集群 ID，查询在平台已启用安装包中，各集群可升级到的 MongoDB 版本；按 **主次版本线**（`x.y`，如 `5.0`）分组返回每条线上的**全部**可选完整版本号。
- **单集群**：对当前集群所在线，返回**高于当前完整版本**的同线补丁包；对在升级链中位于当前线**之后**的每条线，返回介质中该线**全部**可用完整版本。
- **多集群**：对每个主次版本线分别计算可升级版本集合，再对多个集群做**按线交集**（仅保留每条线在**所有**集群上都可选的版本号）；若某条线在某个集群上无候选（或交集为空），该线不出现在 `data` 中。
- **升级链**：主次版本顺序见代码常量 `MONGODB_MAJOR_MINOR_UPGRADE_CHAIN`（[`mongodb_upgrade_version.py`](../../dbm-ui/backend/flow/engine/bamboo/scene/mongodb/mongodb_upgrade_version.py)）。
- **代码位置**：
  - 视图：[`dbm-ui/backend/db_services/mongodb/toolbox/views.py`](../../dbm-ui/backend/db_services/mongodb/toolbox/views.py)（`ToolboxViewSet.list_available_versions`）
  - 入参：[`dbm-ui/backend/db_services/mongodb/toolbox/serializers.py`](../../dbm-ui/backend/db_services/mongodb/toolbox/serializers.py)（`ListAvailableVersionSerializer`）
  - 逻辑：[`dbm-ui/backend/db_services/mongodb/toolbox/handlers.py`](../../dbm-ui/backend/db_services/mongodb/toolbox/handlers.py)（`ToolboxHandler.list_available_versions`）

## 接口说明

| 项目 | 说明 |
|------|------|
| Method | `GET` |
| Path | `/apis/mongodb/bizs/{bk_biz_id}/toolbox/list_available_versions/` |
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

- ViewSet 默认使用 `DBManagePermission`（需具备对应 DB 管理类权限；以实际 IAM / 登录态为准）。
- 本 action **未** 配置 `action_permission_map` 中的额外 MongoDB 集群动作（与 `execute_cluster_tcp_cmd` 等不同），以 `DBManagePermission` 为准。

### 业务校验与错误

- 任一 `cluster_id` 在元数据中不存在：校验失败，返回业务错误（常见为 `result: false` 及参数/校验信息）。
- 当前集群主次版本不在主版本升级链或未支持：可能抛出「不支持的当前版本」类校验错误。
- 无可升级版本时：**成功**返回，**`data` 为空数组** `[]`。

## 响应说明

外层结构以项目统一封装为准，常见字段包括：

| 字段 | 类型 | 说明 |
|------|------|------|
| `result` | boolean | 是否成功 |
| `code` | int | 业务码，`0` 通常表示成功 |
| `message` | string | 提示信息 |
| `data` | array | 成功时为对象数组，见下表；顺序按升级链中主次版本线先后排列 |

### `data` 数组元素结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `major` | string | 主次版本线标识，格式 `mongodb-{x.y}`（如 `mongodb-5.0`） |
| `full_list` | string[] | 该线上可选的完整版本号列表（已 `normalize_mongodb_full_version`），按版本号升序 |

#### 示例（`data` 片段）

```json
[
  {"major": "mongodb-5.0", "full_list": ["mongodb-5.0.9", "mongodb-5.0.14"]},
  {"major": "mongodb-6.0", "full_list": ["mongodb-6.0.9"]}
]
```

## 请求示例

### cURL（多集群，按线交集）

```bash
curl -sS -G "https://{host}/apis/mongodb/bizs/2/toolbox/list_available_versions/" \
  --data-urlencode "cluster_ids=100" \
  --data-urlencode "cluster_ids=101"
```

### cURL（单集群）

```bash
curl -sS -G "https://{host}/apis/mongodb/bizs/2/toolbox/list_available_versions/" \
  --data-urlencode "cluster_ids=100"
```

### Postman

- Method：`GET`
- URL：`https://{host}/apis/mongodb/bizs/{bk_biz_id}/toolbox/list_available_versions/`
- **Params**：新增多行同名键 `cluster_ids`，值为各集群 ID。

## 响应示例

### 成功（有可选版本）

```json
{
  "result": true,
  "code": 0,
  "data": [
    {"major": "mongodb-5.0", "full_list": ["mongodb-5.0.14"]},
    {"major": "mongodb-6.0", "full_list": ["mongodb-6.0.9"]},
    {"major": "mongodb-7.0", "full_list": ["mongodb-7.0.3"]}
  ],
  "message": "ok"
}
```

### 成功（无可升级版本）

```json
{
  "result": true,
  "code": 0,
  "data": [],
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

- 可用版本来自 **`Package` 表** 中 `pkg_type` 为 MongoDB、`db_type` 为 MongoDB、且 `enable=True` 的安装包。
- 多集群时若任一线交集为空，该线不出现在 `data` 中；若全部线均无交集，返回 **`data: []`**（除非在单集群计算时已因版本不支持而校验失败）。
- **已移除**查询参数 `upgrade_type`；行为为上述「同线补丁 + 链上更高线全量」的统一逻辑。

## 变更说明（与历史文档对比）

- 请求：不再支持 `upgrade_type`（`major` / `minor`）。
- 响应：`data` 由「字符串数组」改为「`{ major, full_list }` 对象数组」，并按升级链顺序输出各线。
