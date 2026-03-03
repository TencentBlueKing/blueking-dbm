# 单据详情 AI 展示接口设计文档

## 1. 背景与目标

当前 DBM 有 331 种单据类型，每种单据的 `details` JSON 结构各不相同。AI 工具（如 MCP）在获取单据信息时面临以下问题：

- `details` 是一个无 schema 的 JSON 字段，AI 无法理解每个字段的含义
- `patch_ticket_detail` 会在创建后向 details 追加 `clusters`、`specs` 等信息，原始 serializer 未声明这些字段
- 使用 `SkipToRepresentationMixin` 的单据（大多数操作类）直接返回原始 dict，字段含义不明确
- 流程进度信息分散在 `Flow` 模型中，需要额外查询

**目标**：设计一个统一的 AI 专用接口，让 AI 能解析并展示任意类型单据的详情和流程进度，无需为 331 种单据逐一适配。

## 2. 现有架构分析

### 2.1 单据 details 的生命周期

```
创建请求 details
    ↓
TicketDetailsSerializer.validate()  — 按 ticket_type 选择对应 serializer 校验
    ↓
Ticket.objects.create(details=...)  — 写入 DB
    ↓
builder.patch_ticket_detail()       — 补充 clusters/specs/db_version 等
    ↓
ticket.save()                       — 更新 DB
    ↓
读取时 TicketDetailsSerializer.to_representation(details)
    ↓
若 SkipToRepresentationMixin → 原样返回 dict（包含 patch 后的所有字段）
若普通 Serializer            → 仅输出声明的字段 + SerializerMethodField
```

### 2.2 关键机制

| 机制 | 位置 | 说明 |
|------|------|------|
| Builder 注册表 | `backend/ticket/builders/__init__.py` | `BuilderFactory.registry` 按 `ticket_type` 注册 Builder 类 |
| Serializer 分发 | `BuilderFactory.get_serializer(ticket_type)` | 返回对应 Builder 的 `serializer` 实例 |
| patch_ticket_detail | `backend/ticket/builders/common/base.py` | 按开关补充 clusters/specs/instances 等 |
| SkipToRepresentationMixin | 同上 | `to_representation` 直接 `return instance` |
| Flow 模型 | `backend/ticket/models/ticket.py` | 存储流程类型、状态、别名、错误信息 |

### 2.3 Serializer 字段元数据

每个 Builder 的 serializer 已经在字段上定义了 `help_text`，例如：

```python
# MysqlSingleApplyDetailSerializer
bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))
cluster_count = serializers.IntegerField(help_text=_("申请数量"))
domains = serializers.ListField(help_text=_("域名列表"))

# RedisDataCopyDetailSerializer
dts_copy_type = serializers.ChoiceField(choices=DtsCopyType.get_choices())
write_mode = serializers.ChoiceField(choices=WriteModeType.get_choices())
infos = serializers.ListField(help_text=_("批量数据复制列表"))
```

这些 `help_text` 就是字段的中文含义，可以通过 DRF 自省能力自动提取。

## 3. 接口设计

### 3.1 接口定义

```
GET /apis/tickets/{ticket_id}/ai_detail/
```

### 3.2 返回结构

```json
{
    "ticket_id": 2100931,
    "ticket_type": "REDIS_CLUSTER_DATA_COPY",
    "ticket_type_display": "Redis 集群数据复制",
    "status": "RUNNING",
    "status_display": "执行中",
    "creator": "vitoxie",
    "create_at": "2026-04-20 17:58:33",
    "bk_biz_id": 5005578,
    "remark": "",
    "fields_schema": [
        {"name": "dts_copy_type", "label": "复制类型", "type": "ChoiceField"},
        {"name": "write_mode", "label": "写入类型", "type": "ChoiceField"},
        {"name": "sync_disconnect_setting", "label": "断开设置", "type": "Serializer"},
        {"name": "infos", "label": "批量数据复制列表", "type": "ListField"},
        {"name": "clusters", "label": "集群信息", "type": "dict"},
        {"name": "specs", "label": "规格信息", "type": "dict"}
    ],
    "details": {
        "dts_copy_type": "one_app_diff_cluster",
        "write_mode": "delete_and_write_to_redis",
        "sync_disconnect_setting": {"type": "keep_sync_with_reminder", "reminder_frequency": "once_daily"},
        "infos": [
            {
                "src_cluster": 123,
                "dst_cluster": 456,
                "key_white_regex": "*",
                "key_black_regex": ""
            }
        ],
        "clusters": {
            "123": {"immute_domain": "ssd013.tokenhktest.itop.db", "cluster_type": "TendisSSD集群", ...},
            "456": {"immute_domain": "ins.tokentest.itop.db", "cluster_type": "TendisSSD集群", ...}
        }
    },
    "flows": [
        {
            "flow_type": "BK_ITSM",
            "flow_type_display": "单据审批",
            "flow_alias": "单据审批",
            "status": "SUCCEEDED",
            "status_display": "成功",
            "err_msg": ""
        },
        {
            "flow_type": "PAUSE",
            "flow_type_display": "人工确认",
            "flow_alias": "确认是否执行 \"Redis 集群数据复制\"",
            "status": "SUCCEEDED",
            "status_display": "成功",
            "err_msg": ""
        },
        {
            "flow_type": "INNER_FLOW",
            "flow_type_display": "生产部署",
            "flow_alias": "Redis 数据复制",
            "status": "RUNNING",
            "status_display": "执行中",
            "err_msg": ""
        }
    ]
}
```

### 3.3 字段说明

| 字段 | 说明 |
|------|------|
| `fields_schema` | 从 serializer 自动提取的字段元数据列表，包含 name（字段名）、label（中文含义）、type（字段类型） |
| `details` | DB 中 patch 后的完整 details JSON，直接使用 `to_representation` 输出 |
| `flows` | 简化的流程进度列表，按创建顺序排列 |

## 4. 核心实现

### 4.1 在 TicketViewSet 新增 action

**文件**：`backend/ticket/views.py`

```python
from rest_framework.serializers import Serializer as EmptySerializer

@common_swagger_auto_schema(
    operation_summary=_("单据AI详情"),
    tags=[TICKET_TAG],
)
@action(detail=True, methods=["GET"], serializer_class=EmptySerializer)
def ai_detail(self, request, pk=None):
    """返回 AI 可读的单据详情，包含字段 schema、patch 后的 details 和流程进度"""
    ticket = self.get_object()

    # 1. 获取对应的 serializer 并提取字段元数据
    slz = BuilderFactory.get_serializer(ticket.ticket_type)
    fields_schema = self._extract_fields_schema(slz, ticket.details)

    # 2. 获取 patch 后的 details
    details = slz.to_representation(ticket.details)

    # 3. 获取流程进度
    flows = self._get_flow_summary(ticket)

    return Response({
        "ticket_id": ticket.id,
        "ticket_type": ticket.ticket_type,
        "ticket_type_display": TicketType.get_choice_label(ticket.ticket_type),
        "status": ticket.status,
        "status_display": TicketStatus.get_choice_label(ticket.status),
        "creator": ticket.creator,
        "create_at": ticket.create_at,
        "bk_biz_id": ticket.bk_biz_id,
        "remark": ticket.remark,
        "fields_schema": fields_schema,
        "details": details,
        "flows": flows,
    })
```

### 4.2 字段元数据提取

**文件**：`backend/ticket/views.py`（TicketViewSet 的方法）

```python
# patch_ticket_detail 写入的通用字段 schema
PATCH_FIELDS_SCHEMA = [
    {"name": "clusters", "label": "集群信息", "type": "dict"},
    {"name": "specs", "label": "规格信息", "type": "dict"},
    {"name": "instances", "label": "实例信息", "type": "dict"},
    {"name": "recycle_hosts", "label": "回收主机", "type": "list"},
    {"name": "machine_infos", "label": "机器信息", "type": "dict"},
]

@staticmethod
def _extract_fields_schema(slz, details):
    """从 serializer 字段定义中提取元数据，供 AI 理解 details 结构"""
    schema = []
    for name, field in slz.fields.items():
        # 跳过 SerializerMethodField —— 这些字段只用于展示转换，details 里不一定有对应的 key
        if isinstance(field, serializers.SerializerMethodField):
            continue

        field_info = {
            "name": name,
            "label": str(field.help_text or name),
            "type": field.__class__.__name__,
        }

        # 对 ChoiceField 提取可选值，帮助 AI 理解枚举含义
        if isinstance(field, serializers.ChoiceField) and field.choices:
            field_info["choices"] = {
                str(k): str(v) for k, v in field.choices.items()
            }

        schema.append(field_info)

    # 追加 patch_ticket_detail 写入的通用字段（仅在 details 中实际存在时）
    for pf in PATCH_FIELDS_SCHEMA:
        if pf["name"] in details:
            schema.append(pf)

    return schema
```

### 4.3 流程进度提取

**文件**：`backend/ticket/views.py`（TicketViewSet 的方法）

```python
@staticmethod
def _get_flow_summary(ticket):
    """获取简化的流程进度列表"""
    flows = Flow.objects.filter(ticket=ticket).order_by("id")
    return [
        {
            "flow_type": flow.flow_type,
            "flow_type_display": str(FlowType.get_choice_label(flow.flow_type)),
            "flow_alias": flow.flow_alias or "",
            "status": flow.status,
            "status_display": str(TicketFlowStatus.get_choice_label(flow.status)),
            "err_msg": flow.err_msg or "",
        }
        for flow in flows
    ]
```

### 4.4 需要导入的模块

在 `views.py` 顶部确认以下 import 已存在（大部分已有）：

```python
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketStatus, TicketType
from backend.ticket.models import Flow
```

## 5. 权限控制

`ai_detail` 应复用与 `retrieve` 相同的权限策略。当前 `TicketViewSet` 的 `_get_custom_permissions` 已有 `retrieve` 的权限配置，`ai_detail` 作为 detail action 默认走 `default_permission_class`，需确认是否满足需求。如需与 `retrieve` 完全一致，可在 `action_permission_map` 中显式配置。

## 6. AI 使用方式

AI（MCP 工具）拿到返回数据后的处理逻辑：

1. **读取基础信息**：`ticket_type_display`、`status_display`、`creator`、`create_at` 直接展示
2. **解析 details**：遍历 `fields_schema`，用 `name` 从 `details` 中取值，用 `label` 作为表头/字段名展示
3. **翻译枚举值**：如果 schema 中包含 `choices`，用 details 中的值查找对应的中文 label
4. **关联集群信息**：如果 details 中有 `src_cluster: 123`，可从 `details.clusters["123"]` 获取集群域名等详情
5. **展示流程进度**：遍历 `flows` 列表，展示每一步的状态

### 6.1 AI 展示示例

基于返回数据，AI 可以生成如下表格：

**需求信息：**

| 字段 | 值 |
|------|-----|
| 源集群 | ssd013.tokenhktest.itop.db（TendisSSD集群） |
| 目标集群 | ins.tokentest.itop.db（TendisSSD集群） |
| 复制类型 | 业务内 |
| 写入类型 | 先删除同名 Key，再写入 |
| 包含 Key | * |
| 排除 Key | -- |
| 断开设置 | 不断开，定时发送断开提醒 |
| 提醒频率 | 一天一次（早上 10:00） |

**实施进度：**

| 步骤 | 状态 | 耗时 |
|------|------|------|
| 单据审批 | 已通过 | 10s |
| 确认是否执行 | 确认执行 | 1m 27s |
| Redis 数据复制 | 执行中 | 1h 29m 23s |

## 7. 后续增强（可选）

### 7.1 自定义 to_ai_representation

对于高频或结构复杂的单据类型，可在 serializer 上定义 `to_ai_representation` 方法，返回更精炼的展示数据：

```python
class RedisDataCopyDetailSerializer(RedisBaseOperateDetailSerializer):
    # ...
    
    def to_ai_representation(self, instance):
        """AI 专用的展示格式，比原始 details 更易读"""
        clusters = instance.get("clusters", {})
        infos = instance.get("infos", [])
        return {
            "复制类型": DtsCopyType.get_choice_label(instance["dts_copy_type"]),
            "写入类型": WriteModeType.get_choice_label(instance["write_mode"]),
            "复制任务": [
                {
                    "源集群": clusters.get(str(info["src_cluster"]), {}).get("immute_domain", info["src_cluster"]),
                    "目标集群": clusters.get(str(info["dst_cluster"]), {}).get("immute_domain", info["dst_cluster"]),
                    "包含Key": info.get("key_white_regex", "*"),
                    "排除Key": info.get("key_black_regex", ""),
                }
                for info in infos
            ],
        }
```

`ai_detail` 中的调用逻辑：

```python
if hasattr(slz, 'to_ai_representation'):
    details = slz.to_ai_representation(ticket.details)
else:
    details = slz.to_representation(ticket.details)
```

### 7.2 枚举值自动翻译

在 `_extract_fields_schema` 中已包含 `choices` 信息。AI 可据此自动将 `"one_app_diff_cluster"` 翻译为 `"业务内"`。

### 7.3 集群 ID 自动翻译

在 `details` 中遇到 `cluster_id` / `src_cluster` / `dst_cluster` 等字段时，如果 `details.clusters` 中有对应的映射，可自动替换为集群域名。这个逻辑建议放在 AI 侧处理，而不是后端。

## 8. 开发工作量评估

| 任务 | 预估代码量 | 说明 |
|------|------------|------|
| `ai_detail` action | ~30 行 | 视图方法 |
| `_extract_fields_schema` | ~25 行 | 字段元数据提取 |
| `_get_flow_summary` | ~15 行 | 流程进度提取 |
| **合计** | **~70 行** | 无需修改任何现有代码 |
