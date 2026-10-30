# SQLServer 单据流程输出预设接入指引

> 目录路径：`backend/flow/utils/sqlserver/flow_output_presets/`
> 面向读者：dbm-ui 后端开发者（尤其是新接入 sqlserver 单据的同学）
> 目标：**30 分钟内完成一个新 SQLServer 单据的"执行摘要"输出接入**，且不再新建单据专属 Serializer 子类。

---

## 1. 这是什么

`flow_output_presets` 是一组按 **"输出语义"** 归类的共享 `BaseFlowOutputSerializer` 子类，供 SQLServer 全量单据在流程节点摘要中复用（`FlowSummary.summary`）。

**核心约束（务必先看）：**

- **SQLServer 预设按 SQLServer 自身字段契约定义**：直接继承 `BaseFlowOutputSerializer` 自定义字段（SQLServer 无 CLB、一台新机可挂多集群等契约差异较多）；仅当字段契约与 MySQL 对应预设**完全一致**时才直接继承 MySQL 预设并仅覆盖 `table_name / table_display_name`。
- **禁止在单据侧新建一次性 Serializer 子类**。若现有预设无法覆盖需求，请先在本目录扩展一个新的语义预设，再供本单据使用。
- 本目录**不修改** `backend/flow/utils/base/flow_output.py` 内 `BaseFlowOutputSerializer` / `FlowOutputHandler` 的任何逻辑。
- 幂等（重试不重复写入）依赖 `insert_data` 现有的主键合并分支——即"声明 `table_primary_key` → 重复写入按主键覆盖"，Handler 本身没有做任何改动。

---

## 2. 预设一览表

| 语义类别 | 类名 | `table_name` | `table_primary_key` | 典型使用单据 |
| --- | --- | --- | --- | --- |
| 集群交付信息 | `SqlserverClusterApplySummarySerializer` | `sqlserver_cluster_apply` | `cluster_domain_and_port` | `sqlserver_single_apply` / `sqlserver_ha_apply` |
| SQL执行信息 | `SqlserverSqlExecSummarySerializer` | `sqlserver_sql_exec` | `cluster_domain_and_port` | `sqlserver_sql_file_execute`（变更SQL执行）/ `sqlserver_data_export`（数据导出，复用本预设） |
| 集群生命周期信息 | `SqlserverClusterLifecycleSummarySerializer` | `sqlserver_cluster_lifecycle` | `cluster_domain_and_port` | `sqlserver_cluster_destroy` / `sqlserver_cluster_disable` / `sqlserver_cluster_enable` / `sqlserver_cluster_reset` |
| 实例变更明细 | `SqlserverInstanceChangeSummarySerializer` | `sqlserver_instance_change` | `cluster_domain_and_port` | `sqlserver_add_slave` / `sqlserver_slave_rebuild`（原地+新机）/ `sqlserver_ha_switch` / `sqlserver_ha_fail_over` / `sqlserver_cluster_migrate`（整机+集群迁移） |
| 库操作信息 | `SqlserverDbOperationSummarySerializer` | `sqlserver_db_operation` | `cluster_domain_and_port` | `sqlserver_clean_dbs` / `sqlserver_rename_dbs`（含迁移/回滚内部重命名流程）/ `sqlserver_build_db_sync` / `sqlserver_backup_dbs`（含 SQL 导入前备份 / 回滚前备份，action=backup） |
| 数据传输信息 | `SqlserverDataTransferSummarySerializer` | `sqlserver_data_transfer` | `cluster_domain_and_port`（目标集群） | `sqlserver_rollback` / `sqlserver_rollback_local`（定点构造/原地回档）/ `sqlserver_full_migrate` / `sqlserver_incr_migrate`（DTS） |

> SQLServer 场景无 CLB，`cluster_apply` 预设**不设** `clb_ip / clb_domain` 字段；`readonly_domain_and_port` 用于承载 SqlserverHA 的 `"slave_domain:port"`；SqlserverSingle 场景 `readonly_domain_and_port` 留空。
>
> 动作 / 模式类字段（`action` / `mode`）由就近共存的枚举强约束：`SqlserverClusterLifecycleAction` / `SqlserverInstanceChangeAction` / `SqlserverDbOperationAction` / `SqlserverDataTransferMode`（均从 `flow_output_presets` 统一入口 import）。
> `sqlserver_instance_change` 与 mysql 侧 `mysql_instance_change` 的关键差异：SQLServer 一台新机可挂多集群，`instance` 不跨集群唯一，故主键改用 `cluster_domain_and_port`，变更后实例由 `new_instance` 承载，被顶替的旧实例由 `peer_old_instance` 承载。

---

## 3. 分层策略（为什么继承而不是重写）

```
SQLServer 单据的某个摘要语义 → 字段契约与 MySQL 对应预设是否完全一致？
├── 完全一致
│   └── 继承 MySQL 预设，仅覆盖 table_name / table_display_name
├── 字段契约有差异（多数场景：SQLServer 无 CLB、多集群共机等）
│   └── 继承 BaseFlowOutputSerializer，按 SQLServer 契约自定义全部字段    ✅ 现状主流
└── 全新语义
    └── 同上：继承 BaseFlowOutputSerializer 自定义（配套就近共存的枚举）
```

好处：
- MySQL / SQLServer 跨 DB 字段语义天然对齐，前端表格复用模板；
- MySQL 预设字段升级时 SQLServer 继承侧自动受益；
- SQLServer 侧代码量最小，评审成本最低。

---

## 4. `table_primary_key` 幂等原理

与 MySQL 侧相同，`FlowOutputHandler.insert_data` 对声明了 `table_primary_key` 的预设自动走"后写覆盖前写"合并分支，无需额外处理。

详见 `backend/flow/utils/mysql/flow_output_presets/README.md` §4。

**决策建议：**

| 场景 | 主键推荐 | 理由 |
| --- | --- | --- |
| 每个集群一行的输出（部署 / 校验 / 授权） | `cluster_domain_and_port` 或 `cluster_domain` | 集群维度唯一 |
| 每个实例一行的输出（切换 / 扩缩容 / 重装） | `instance`（`IP:Port`） | 实例维度唯一 |
| 追加型流水 / 消息 | *不设置* | 允许重复；复用 MySQL 的 `MessageSummarySerializer` |

---

## 5. 端到端最小接入示例

```python
# -*- coding: utf-8 -*-
"""sqlserver 集群部署摘要节点使用示例（构建期装配 + 通用组件）。"""

from backend.flow.plugins.components.collections.sqlserver.flow_output_summary import (
    SqlserverFlowOutputSummaryComponent,
)

# items 在 flow 构建期从单据参数装配（域名 / 端口 / slave 域名均来自 self.data，
# port 由 calc_install_ports 在构建期写回 cluster dict，无需反查 db_meta）
pipeline.add_act(
    act_name=_("写入集群交付摘要"),
    act_component_code=SqlserverFlowOutputSummaryComponent.code,
    kwargs={
        "preset": "cluster_apply",
        "items": [
            {
                "cluster_domain_and_port": "c1.sqlserver.example.db:1433",
                "readonly_domain_and_port": "c1-slave.sqlserver.example.db:1433",
            },
        ],
    },
)
```

**接入要点：**
1. 摘要节点排在流程末尾（或对应子流程末尾）；节点执行到即代表前置步骤成功，构建期装配的数据即为最终交付结果。
2. 装配数据取自 `self.data` 单据参数；仅当字段**运行期才产生**（如 mysql 的 CLB IP）时才需要运行期反查方案。
3. 同一 `cluster_domain_and_port` 的重复写入会被主键合并分支覆盖，天然幂等。
4. 走统一入口 import：`from backend.flow.utils.sqlserver.flow_output_presets import SqlserverClusterApplySummarySerializer`；**禁止深路径 import**。

---

## 6. 现有预设不覆盖，怎么办？

1. 先确认是否**真的**无法归入现有语义。90% 的场景可通过 `extra` 文本字段兜底解决。
2. 若确需新语义，请在本目录新增一个 `.py` 文件，**优先继承 MySQL 对应预设**，仅在字段契约有差异时才自定义字段：
   - License 头 + 编码声明 + 模块级 docstring；
   - 类 docstring 四要素（功能 / 输入 / 输出 / 边界）；
   - 所有字段带 `help_text=_("...")` 国际化；
   - `table_name` 以 `sqlserver_` 前缀开头，命名空间内唯一；
   - 若有主键：字段声明为 `required=True, allow_blank=False`；
   - 附带一条"重复主键写入被合并"的单元测试。
3. 在 `__init__.py` 补一行导出。
4. 在本 README 的一览表中登记。
5. 如需同时在 `SqlserverFlowOutputSummaryService` 通过 preset 短名调用，还需在
   `backend/flow/plugins/components/collections/sqlserver/flow_output_summary.py`
   的 `_SQLSERVER_PRESET_REGISTRY` 中登记一行。

**再次强调：禁止在单据侧的 `plugins/components/collections/sqlserver/` 目录里新建一次性 Serializer 子类。**
