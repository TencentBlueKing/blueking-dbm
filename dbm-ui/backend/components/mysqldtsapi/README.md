# MySQLDTSApi

MySQL DTS OpenAPI 客户端，经 **ProxyAPI**（按云区域 nginx）转发到 DRS，再由 DRS 代理到 DTS Master。

## 使用

```python
from backend.components import MySQLDTSApi

dts_addr = "dts-master.example.com:18301"  # DTS Master 地址 host:port
bk_cloud_id = 0  # DTS Master 所在云区域（ProxyAPI 必填）

sources = MySQLDTSApi.list_sources(dts_addr, bk_cloud_id=bk_cloud_id)
task = MySQLDTSApi.get_task(dts_addr, "task-1", bk_cloud_id=bk_cloud_id)
```

调用链：`DBM` → `ProxyAPI`（按 `bk_cloud_id` 选云区域代理）→ `DRS`（`POST /v2/mysql-dts/rpc`）→ `DTS Master`（`/api/v1/...`）

- SSL 与 `DRSApi` 同源，受 `env.DRS_SKIP_SSL` 控制。
- 全部 public 方法均要求 keyword-only 参数 `bk_cloud_id`。

请求/响应类型定义见 `types.py`。

## 异常处理

### 推荐写法

业务代码统一按下面方式捕获，与项目内其他组件（`DRSApi`、`DBPartitionApi` 等）一致：

```python
from backend.components import MySQLDTSApi
from backend.exceptions import ApiRequestError, ApiResultError

try:
    source = MySQLDTSApi.get_source(dts_addr, "mysql-1", bk_cloud_id=0)
except ApiResultError as e:
    # DRS 网关返回 result=false（HTTP 200），网关层业务校验失败
    logger.error("DTS 网关业务失败: %s", e)
except ApiRequestError as e:
    # 最常见：DTS 业务错误、Master 不可达、DRS 转发失败、网络超时
    logger.error("DTS 请求失败: %s", e)
```

若不需要区分两类错误，可捕获父类 `ApiError`（`backend.exceptions.ApiError`）。

### 抛哪些异常

| 异常 | 来源 | 典型场景 |
|------|------|----------|
| `ApiRequestError` | `backend.exceptions` | **绝大多数失败走这个**。资源不存在（source/task/template）、参数非法、DTS Master 不可达、DRS 转发失败（502）、网络超时 |
| `ApiResultError` | `backend.exceptions` | DRS 网关 `result=false` 且 HTTP 200，网关层鉴权/校验失败（本客户端较少见） |
| `pydantic.ValidationError` | `pydantic` | DTS 返回结构与 `types.py` 定义不一致，属于封装 bug，应修复而非业务捕获 |

说明：

- DTS Master 的业务错误（如 `error_code: 20051`、404、400）**不会**有单独异常类型，经 DRS 包装后统一为 `ApiRequestError`。
- 错误详情在 `str(e)` / `e.message` 中，通常包含 DTS 原始 `error_msg`。
- 异常对象还有 `e.code`（DBM 错误码）、`e.data`（部分场景有附加数据）。

### 不会抛异常的情况

以下属于正常空结果，返回 `total=0, data=[]`，**不是错误**：

- `list_sources(enable_relay=True)` 无 relay source
- `list_tasks(source_name_list=[...])` 过滤无匹配 task
- `get_task_migrate_targets(..., schema_pattern=...)` 过滤无匹配（client 已将 DTS 的 `data: null` 转为 `[]`）

### 示例：按错误类型处理

```python
from backend.components import MySQLDTSApi
from backend.exceptions import ApiRequestError, ApiResultError

def get_source_safe(dts_addr: str, source_name: str, *, bk_cloud_id: int = 0):
    try:
        return MySQLDTSApi.get_source(dts_addr, source_name, bk_cloud_id=bk_cloud_id)
    except ApiResultError as e:
        # 网关层失败，可记录后向上抛或转业务异常
        raise MyBusinessError(f"DTS 网关错误: {e}") from e
    except ApiRequestError as e:
        # 资源不存在、Master 挂了等
        if "does not exist" in str(e) or "404" in str(e):
            return None
        raise
```

## API 列表

| 分类 | 方法 |
|------|------|
| Source | `create_source` `list_sources` `get_source` `delete_source` `update_source` `get_source_status` `enable_source` `disable_source` `transfer_source` `enable_relay` `disable_relay` `purge_relay` `get_source_schemas` `get_source_schema_tables` |
| Task | `create_task` `list_tasks` `get_task` `delete_task` `update_task` `get_task_status` `start_task` `stop_task` `get_task_migrate_targets` `get_task_schemas` `get_task_schema_tables` `get_task_table_structure` `operate_task_schema` `delete_task_schema` |
| Template | `create_template` `list_templates` `get_template` `update_template` `delete_template` `import_templates` |
| 其他 | `convert_task` `get_cluster_info` `update_cluster_info` `list_masters` `offline_master` `list_workers` `offline_worker` |

各方法 HTTP 路径与参数见 `client.py` 内 docstring。
