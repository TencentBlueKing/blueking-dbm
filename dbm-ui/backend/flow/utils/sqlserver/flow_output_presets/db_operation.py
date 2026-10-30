# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

------------------------------------------------------------------------------

SQLServer 库操作类摘要预设。

职责：
  - 描述"每个集群一行"的库级操作结果（清档 / 库重命名 / 建立同步 / 备份）。
  - 通过 table_primary_key = "cluster_domain_and_port" 保证节点重试对同一集群的重复上报走覆盖合并。
  - 本模块同时承载配套的动作枚举 :class:`SqlserverDbOperationAction`（就近共存，便于阅读维护）。

数据源 / 调用通道：
  - 由 SQLServer 库操作类流程节点（clean_dbs / rename_dbs / build_database_sync / backup_dbs）在动作完成后，
    经通用组件 :class:`SqlserverFlowOutputSummaryComponent`（preset="db_operation"）写入。
  - 集群域名 / 主实例由 :meth:`BaseFlow.resolve_cluster_summary_info` 反查 db_meta 装配。
  - rename_dbs 会被迁移 / 回滚单据作为内部流程复用（ticket_type 固定为 SQLSERVER_DBRENAME）；
    backup_dbs 会被 SQL 导入前备份 / 回滚前备份复用——同一 preset 天然兼容，无需为复用场景单独立表。

边界：
  - instance 字段走 BaseFlowOutputSerializer.InstanceField，格式必须为 IP:Port。
  - action 由枚举 :class:`SqlserverDbOperationAction` 强约束，非法值直接被 ChoiceField 拒绝。
  - databases 为列表 / 映射时由调用方拼接为纯文本，禁止塞结构化数据。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class SqlserverDbOperationAction(StrStructuredEnum):
    """SQLServer 库操作动作枚举（对齐 :class:`SqlserverDbOperationSummarySerializer.action` 字段）。

    功能说明：
      - 描述"一次集群内库级操作"对应的动作类型；供前端在执行摘要 tab 展示"这一行到底做了什么"，
        并支持按 action 分组 / 过滤。
      - 值为短字符串（写入 FlowSummary），label 经 ``gettext`` 即时求值为 str，符合摘要 JSON 落盘约束。

    取值：
      - CLEAN      ("clean")      -> 清档：清空 / 删除目标库数据
      - RENAME     ("rename")     -> 库重命名：db_name 改为 target_db_name
      - BUILD_SYNC ("build_sync") -> 建立同步：HA 集群 slave 与 master 建立库级同步
      - BACKUP     ("backup")     -> 备份：对目标库执行全量 / 日志备份

    边界：
      - 非枚举值 -> :class:`serializers.ChoiceField` 校验失败，节点显式失败，便于排障；
      - 未来若出现新的库级操作语义，直接在此追加新的枚举项即可。
    """

    CLEAN = EnumField("clean", _("清档"))
    RENAME = EnumField("rename", _("库重命名"))
    BUILD_SYNC = EnumField("build_sync", _("建立同步"))
    BACKUP = EnumField("backup", _("备份"))


class SqlserverDbOperationSummarySerializer(BaseFlowOutputSerializer):
    """SQLServer 库操作摘要（每集群一行）。

    功能说明：
      - 描述集群维度的库级操作执行信息（清档 / 重命名 / 建立同步 / 备份），供前端在单据执行摘要 tab 中展示。
      - 通过 `table_primary_key = "cluster_domain_and_port"` 让 FlowOutputHandler.insert_data 在遇到
        相同集群的重复写入时走"后写覆盖前写"分支，天然幂等。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain_and_port (str, 必填, 非空): 集群主访问入口 `"domain:port"`，作为主键
      - instance (str, 必填, IP:Port): 执行操作的实例标识（master/orphan），格式由 InstanceField 强校验
      - action (str, 必填): 库操作动作，取值必须在 :class:`SqlserverDbOperationAction` 枚举内
      - databases (str, 必填, 非空): 目标库纯文本——清档 / 同步 / 备份为库列表（逗号分隔，如 "db1,db2"）；
        重命名为映射（如 "db1 -> db1_new; db2 -> db2_new"）
      - extra (str, 可空, 默认 ""): 操作附加信息兜底文本；前端按纯文本渲染。约定：
        clean 承载 clean_mode（清档类型），build_sync 承载同步的 slave 实例列表，
        backup 承载备份类型（full_backup / log_backup）等备份附加属性

    输出：
      - 写入 FlowSummary.summary 中 table_name = "sqlserver_db_operation" 的表 values。

    边界：
      - cluster_domain_and_port / instance / action / databases 缺失或空串
        -> is_valid 抛 ValidationError。
      - instance 非 IP:Port 格式 -> InstanceField.run_validators 抛校验异常。
      - action 非枚举值 -> ChoiceField 抛校验异常。
      - 重复主键写入 -> 依赖 insert_data 主键合并分支覆盖旧行，行数不变。
    """

    #: 表名（sqlserver 命名空间下唯一，前缀 sqlserver_）
    table_name: str = "sqlserver_db_operation"
    #: 前端表格展示名
    table_display_name: str = _("SQLServer 库操作信息")
    #: 表主键：每集群一行，重复写入按 cluster_domain_and_port 覆盖合并
    table_primary_key: str = "cluster_domain_and_port"

    cluster_domain_and_port = serializers.CharField(
        help_text=_("集群主入口(domain:port)"), required=True, allow_blank=False
    )
    instance = BaseFlowOutputSerializer.InstanceField(help_text=_("执行实例(IP:Port)"), required=True, allow_blank=False)
    action = serializers.ChoiceField(
        help_text=_("库操作动作"), choices=SqlserverDbOperationAction.get_choices(), required=True
    )
    databases = serializers.CharField(help_text=_("目标库列表或映射"), required=True, allow_blank=False)
    #: 操作附加信息兜底；前端按纯文本渲染，禁止塞 dict / list 结构化数据
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
