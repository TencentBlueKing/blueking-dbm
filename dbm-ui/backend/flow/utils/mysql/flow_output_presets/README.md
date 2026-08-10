# MySQL / Spider 单据流程输出预设接入指引

> 目录路径：`backend/flow/utils/mysql/flow_output_presets/`
> 面向读者：dbm-ui 后端开发者（尤其是新接入 mysql/spider 单据的同学）
> 目标：**30 分钟内完成一个新单据的"执行摘要"输出接入**，且不再新建单据专属 Serializer 子类。

---

## 1. 这是什么

`flow_output_presets` 是一组按 **"输出语义"** 归类的共享 `BaseFlowOutputSerializer` 子类。它们描述了"往 `FlowSummary.summary` 里写一张什么样的表"，供 mysql/spider 全量单据在流程节点摘要中复用。

**核心约束（务必先看）：**

- **禁止在单据侧新建一次性 Serializer 子类**。若现有预设无法覆盖需求，请先在本目录扩展一个新的语义预设，再供本单据使用。
- **本预设建设 未修改 `backend/flow/utils/base/flow_output.py`** 内 `BaseFlowOutputSerializer` / `FlowOutputHandler` 的任何逻辑。
- **幂等（重试不重复写入）依赖 `insert_data` 现有的主键合并分支**——即"声明 `table_primary_key` → 重复写入按主键覆盖"，Handler 本身没有做任何改动。**请勿去改 Handler**。

---

## 2. 预设一览表

| 语义类别 | 类名 | `table_name` | `table_primary_key` | 典型使用单据 |
| --- | --- | --- | --- | --- |
| 集群交付信息 | `ClusterApplySummarySerializer` | `mysql_cluster_apply` | `cluster_domain` | mysql / spider apply 类 |
| 实例变更明细 | `InstanceChangeSummarySerializer` | `mysql_instance_change` | `instance` | 主从切换 / 扩缩容 / 下架 / 重装 |
| 授权 / 权限变更结果 | `AuthResultSummarySerializer` | `mysql_auth_result` | `cluster_domain` | authorize_rules(_v2) / revoke |
| 前置校验结果 | `PrecheckResultSummarySerializer` | `mysql_precheck_result` | `cluster_domain` | schema / 连接 / 版本兼容性检查 |
| SQL 执行结果 | `SqlExecResultSummarySerializer` | `mysql_sql_exec_result` | `instance` | SQL 变更单 / 备份恢复 / DDL |
| 通用消息（追加型） | `MessageSummarySerializer` | `mysql_message` | *（不设置）* | 兜底流水提示，**不做幂等** |

> 主机流转（申请 / 回收 / 失败 / 待回收）语义直接复用现有 `RecycleOutputContext.*`，本目录不重复定义。

---

## 3. 如何选 Serializer（决策树）

```
你要写入的每一条摘要记录对应到？
├── 一个"集群"（一个 cluster_domain 一行）
│   ├── 交付类结果（域名/端口/主从/只读）      → ClusterApplySummarySerializer
│   ├── 授权 / 权限变更结果                     → AuthResultSummarySerializer
│   └── 前置校验结果                            → PrecheckResultSummarySerializer
├── 一个"实例"（一个 IP:Port 一行）
│   ├── 实例变更（主从切换/扩缩容/下架/重装）   → InstanceChangeSummarySerializer
│   └── SQL 执行结果                            → SqlExecResultSummarySerializer
└── 都不是（流水消息 / 提示 / 警告）             → MessageSummarySerializer（不做幂等）
```

若以上均无法覆盖，**先在本目录扩展新预设**，再供单据使用。禁止回退到"每单据一子类"。

---

## 4. `table_primary_key` 幂等原理与用法（重要）

### 4.1 原理

`FlowOutputHandler.insert_data` 内部已有一条现成的分支：

```python
# 有主键则判断冲突/合并覆盖
if primary_key:
    primary_map = {d[primary_key]: d for d in table_data["values"]}
    data_map = {d[primary_key]: d for d in validated_data}
    # 合并数据：同主键新数据覆盖旧数据
    table_data["values"] = list({**primary_map, **data_map}.values())
```

因此**只要预设声明了合适的 `table_primary_key`，且调用方在每次写入时都携带该主键字段的值**，重试写入就会走"后写覆盖前写"分支，摘要不会出现重复行。

### 4.2 决策：选谁做主键

| 场景 | 主键推荐 | 理由 |
| --- | --- | --- |
| 每个集群一行的输出 | `cluster_domain` | 集群维度唯一，重试对同集群天然幂等 |
| 每个实例一行的输出 | `instance`（`IP:Port`） | 实例维度唯一 |
| 追加型流水 / 消息 | *不设置* | 允许重复；使用 `MessageSummarySerializer` |

### 4.3 强制约束

- 声明了 `table_primary_key` 的预设，主键字段 **必须** `required=True, allow_blank=False`（或类型允许的等价约束），防止调用方漏传导致合并键为空。
- **本目录下每个"带主键"预设都必须自带一条单元测试**，断言"同主键写入两次后 `values` 长度不变"。这是幂等能力的唯一保障。

---

## 5. 什么情况下允许不设主键（追加型语义）

只有当业务语义**明确允许重复**（例如"记录一条流水提示，重跑就应该多一条"）时，才使用 `MessageSummarySerializer`（不设主键）。

⚠️ **警告**：追加型语义在节点重试时会产生重复记录，这是预期行为，不视为 bug。若你的场景**不希望重复**，请务必选择带主键的预设，而不是给 `MessageSummarySerializer` 加主键。

---

## 6. 端到端最小接入示例

以下示例展示：在一个 mysql apply 类单据的 flow 节点里，将 N 套集群的交付信息一次性写入执行摘要。

```python
# -*- coding: utf-8 -*-
"""mysql 集群部署摘要节点。"""

import logging
from typing import Dict, List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import FlowOutputHandler
from backend.flow.utils.mysql.flow_output_presets import ClusterApplySummarySerializer
from backend.ticket.models import Flow

logger = logging.getLogger("flow")


class MysqlApplySummaryService(BaseService):
    """将 mysql 集群部署结果写入 FlowSummary（重试幂等）。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs: Dict = data.get_one_of_inputs("kwargs")
        root_id: str = self.runtime_attrs.get("root_pipeline_id")

        # 兜底：无关联 Flow 时跳过（例如 DTS 临时流程）
        if not Flow.objects.filter(flow_obj_id=root_id).exists():
            self.log_info(_("流程[{}]未关联单据Flow，跳过摘要写入").format(root_id))
            return True

        # 组装每套集群一行的记录；同 cluster_domain 重试写入会被主键合并覆盖，不重复
        summary_rows: List[Dict] = []
        for item in kwargs["items"]:
            summary_rows.append(
                {
                    "cluster_domain": item["cluster_domain"],  # 主键：必填非空
                    "port": item["proxy_port"],
                    "master_ip": item.get("master_ip", "") or "",
                    "slave_ip": item.get("slave_ip", "") or "",
                    "readonly_domain": item.get("readonly_domain", "") or "",
                    "extra": item.get("extra", ""),
                }
            )

        # 一次调用完成所有集群的摘要写入；重试重复写入不会产生重复行
        FlowOutputHandler(ClusterApplySummarySerializer).insert_data(root_id, summary_rows)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
        ]


class MysqlApplySummaryComponent(Component):
    name = __name__
    code = "mysql_apply_summary"
    bound_service = MysqlApplySummaryService
```

**接入要点回顾：**

1. `from backend.flow.utils.mysql.flow_output_presets import ClusterApplySummarySerializer`：走统一入口，**禁止深路径**。
2. **不新建**任何 Serializer 子类。
3. **每行都携带主键字段值**（本例中的 `cluster_domain`），这是幂等成立的前提。
4. 节点若可能在无 `Flow` 记录的临时流程中运行，请像示例一样先判存在再写入。

---

## 7. 我的语义现有预设不覆盖，怎么办？

1. 先确认是否**真的**无法归入现有 6 类。90% 的场景可通过 `extra` 文本字段兜底解决（前端按纯文本渲染，禁止塞结构化 dict / list）。
2. 若确实需要新语义，请在本目录**新增一个 `.py` 文件**，遵循规范：
   - License 头 + 编码声明 + 模块级 docstring
   - 类 docstring 四要素（功能 / 输入 / 输出 / 边界）
   - 所有字段带 `help_text=_("...")` 国际化
   - `table_name` 以 `mysql_` 或 `spider_` 前缀开头，命名空间内唯一
   - 若有主键：字段声明为 `required=True, allow_blank=False`
   - 附带一条"重复主键写入被合并"的单元测试
3. 在 `__init__.py` 补一行导出。
4. 在本 README 的一览表中登记。

**再次强调：禁止在单据侧的 `plugins/components/collections/mysql|spider/` 目录里新建一次性 Serializer 子类。**
