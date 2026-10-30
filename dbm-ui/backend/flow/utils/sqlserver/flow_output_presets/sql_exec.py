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

SQLServer SQL 执行 / 变更类摘要预设。

职责：
  - 描述"每个集群一行"的 SQL 文件导入执行信息（SQL 变更单据、以及后续可复用的 DTS /
    建库建表等 SQL 执行类语义单据）。
  - 通过 table_primary_key = "cluster_domain_and_port" 保证节点重试对同一集群的重复上报走覆盖合并。

数据源 / 调用通道：
  - 由 SQLServer SQL 执行类流程节点（SQL 变更 `sqlserver_sql_execute`、数据导出
    `sqlserver_data_export`）在每个集群子流程末尾，经通用组件
    :class:`SqlserverFlowOutputSummaryComponent`（preset="sql_exec"）写入：
    `FlowOutputHandler(SqlserverSqlExecSummarySerializer).insert_data(root_id, data)`。
  - 集群域名 / 执行实例由流程节点从 db_meta（cluster / master_instance）直接装配。

边界：
  - instance 字段走 BaseFlowOutputSerializer.InstanceField，格式必须为 IP:Port。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class SqlserverSqlExecSummarySerializer(BaseFlowOutputSerializer):
    """SQLServer SQL 执行信息摘要（每集群一行）。

    功能说明：
      - 描述集群级 SQL 文件导入执行信息，供前端在单据执行摘要 tab 中展示。
      - 通过 `table_primary_key = "cluster_domain_and_port"` 让 FlowOutputHandler.insert_data
        对同一集群的重复写入走"后写覆盖前写"分支，天然幂等。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain_and_port (str, 必填, 非空): 集群主访问入口 `"domain:port"`，作为主键
      - instance (str, 必填, IP:Port): 执行 SQL 导入的实例标识（master/orphan），
        格式由 InstanceField 强校验
      - extra (str, 可空, 默认 ""): 单据私有展示文本兜底（如"变更完成" / "导出成功"），前端按纯文本渲染

    输出：
      - 写入 FlowSummary.summary 中 table_name = "sqlserver_sql_exec" 的表 values。

    边界：
      - cluster_domain_and_port / instance 缺失或空串 -> is_valid 抛 ValidationError。
      - instance 非 IP:Port 格式 -> InstanceField.run_validators 抛校验异常。
      - 重复主键写入 -> 依赖 insert_data 主键合并分支覆盖旧行，行数不变。
    """

    #: 表名（sqlserver 命名空间下唯一，前缀 sqlserver_）；与 mysql_sql_exec_result 分表存放
    table_name: str = "sqlserver_sql_exec"
    #: 前端表格展示名
    table_display_name: str = _("SQLServer SQL执行信息")
    #: 表主键：每集群一行，重复写入按 cluster_domain_and_port 覆盖合并
    table_primary_key: str = "cluster_domain_and_port"

    cluster_domain_and_port = serializers.CharField(
        help_text=_("集群主入口(domain:port)"), required=True, allow_blank=False
    )
    instance = BaseFlowOutputSerializer.InstanceField(help_text=_("执行实例(IP:Port)"), required=True, allow_blank=False)
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
