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

SQLServer 集群交付类摘要预设。

模块职责：
  - 为 SQLServer 部署单据（SqlserverSingleApplyFlow / SqlserverHAApplyFlow）提供"每套集群一行"
    的集群交付摘要字段契约。

设计要点（为何不继承 mysql 的 ClusterApplySummarySerializer）：
  - mysql 预设携带 clb_ip / clb_domain（mysql 部署时 CLB 实例运行时分配，必须运行期反查）；
    SQLServer 产品无 CLB，直接裁掉这两个字段，避免前端渲染两列恒空列。
  - SQLServer 部署摘要的全部字段（域名 / 端口 / slave 域名）在 flow 构建期即可从单据参数
    （self.data["infos"][].clusters[]，port 由 calc_install_ports 构建期写回）获得，
    因此部署单据同样走"通用组件 + 构建期装配"，无需专用反查组件。

数据源 / 调用通道：
  - 部署 flow 在主流程末尾 add_act 通用组件 :class:`SqlserverFlowOutputSummaryComponent`
    （preset="cluster_apply"）写入；items 由
    :meth:`SqlserverSingleApplyFlow.build_cluster_apply_summary_items` 构建期装配。

边界：
  - readonly_domain_and_port 在 SqlserverHA 场景为 "slave_domain:port"（主从端口对齐）；
    SqlserverSingle 场景无只读入口，留空。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class SqlserverClusterApplySummarySerializer(BaseFlowOutputSerializer):
    """SQLServer 集群交付摘要（每集群主入口一行）。

    功能说明：
      - 描述部署交付的集群访问入口信息，供前端在单据执行摘要 tab 中展示。
      - 通过 `table_primary_key = "cluster_domain_and_port"` 让 FlowOutputHandler.insert_data 在遇到
        相同集群的重复写入时走"后写覆盖前写"分支，天然幂等。
      - 字段顺序即前端表头顺序；SQLServer 无 CLB，不设 clb 字段。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain_and_port (str, 必填, 非空): 集群主访问入口 `"domain:port"`，作为主键
      - readonly_domain_and_port (str, 可空, 默认 ""): SqlserverHA 的只读入口 `"slave_domain:port"`；
        SqlserverSingle 场景留空
      - extra (str, 可空, 默认 ""): 单据私有展示文本兜底；前端按纯文本渲染

    输出：
      - 写入 FlowSummary.summary 中 table_name = "sqlserver_cluster_apply" 的表 values。

    边界：
      - cluster_domain_and_port 缺失或空串 -> is_valid 抛 ValidationError。
      - 重复主键写入 -> 依赖 insert_data 主键合并分支覆盖旧行，行数不变。
    """

    #: 表名（sqlserver 命名空间下唯一，前缀 sqlserver_）；与 mysql_cluster_apply 分表存放
    table_name: str = "sqlserver_cluster_apply"
    #: 前端表格展示名
    table_display_name: str = _("SQLServer 集群交付信息")
    #: 表主键：每集群一行，重复写入按 cluster_domain_and_port 覆盖合并
    table_primary_key: str = "cluster_domain_and_port"

    cluster_domain_and_port = serializers.CharField(
        help_text=_("集群主入口(domain:port)"), required=True, allow_blank=False
    )
    readonly_domain_and_port = serializers.CharField(
        help_text=_("只读入口(domain:port)"), required=False, allow_blank=True, default=""
    )
    #: 单据私有展示文本兜底；前端按纯文本渲染，禁止塞 dict / list 结构化数据
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
