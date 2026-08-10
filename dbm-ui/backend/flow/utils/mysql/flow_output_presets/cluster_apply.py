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

mysql/spider 集群交付类摘要预设。

职责：
  - 描述"每套集群一行"的部署 / 交付类输出：主访问入口(域名:port) / 只读入口(域名:port) / CLB 信息 / 扩展。
  - 通过 table_primary_key = "cluster_domain_and_port" 保证节点重试对同一"域名:端口"入口的二次
    写入走覆盖而非追加，从而在不修改 FlowOutputHandler 逻辑的前提下实现天然幂等。

数据源 / 调用通道：
  - 由 mysql / spider apply 类流程节点在集群元数据 / 域名 / 只读入口 / CLB 全部就绪后调用：
    `FlowOutputHandler(ClusterApplySummarySerializer).insert_data(root_id, data)`。

边界：
  - cluster_domain_and_port 缺失 / 为空 -> Serializer.is_valid(raise_exception=True) 抛校验异常。
  - readonly_domain_and_port / clb_ip / clb_domain 允许缺失或空字符串
    （无只读入口 / 未启用 CLB 时留空）。
  - extra 用作单据私有展示文本兜底，类型为字符串，前端按纯文本渲染；不参与主键 / 表头语义。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class ClusterApplySummarySerializer(BaseFlowOutputSerializer):
    """mysql / spider 集群交付摘要（每集群主入口一行）。

    功能说明：
      - 描述集群部署 / 交付结果的一行摘要，字段顺序即前端表头顺序，
        第一个字段 `cluster_domain_and_port`（形如 "c1.mysql.example.db:3306"）
        同时作为行主键。
      - 通过 `table_primary_key = "cluster_domain_and_port"` 让 FlowOutputHandler.insert_data
        在遇到相同"域名:端口"入口的重复写入时走"后写覆盖前写"分支，天然幂等。
      - 主入口与只读入口以"域名:端口"字符串一体化承载，避免出参再次拆分端口字段，
        便于前端直接复制粘贴访问串。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain_and_port (str, 必填, 非空): 集群主访问入口，格式 "domain:port"，作为主键
      - readonly_domain_and_port (str, 可空, 默认 ""): 只读访问入口，格式 "domain:port"；无只读入口留空
      - clb_ip (str, 可空, 默认 ""): 集群 CLB IP；未启用 CLB 时留空
      - clb_domain (str, 可空, 默认 ""): 集群 CLB 域名；未启用 CLB 时留空
      - extra (str, 可空, 默认 ""): 单据私有展示文本兜底；前端按纯文本渲染，不参与主键去重

    输出：
      - 写入 FlowSummary.summary 中 table_name = "mysql_cluster_apply" 的表 values；
        每次调用产出的 dict 会按主键合并进该表 values 数组。

    边界：
      - cluster_domain_and_port 为空 / 缺失 -> is_valid 抛 ValidationError。
      - 相同 cluster_domain_and_port 的重复写入 -> 依赖 insert_data 主键合并分支覆盖旧行，
        `values` 长度不变（重试幂等）。
      - readonly / clb 字段格式本预设不做强校验，由调用方保证；如需严格 IP:Port 校验请改用
        BaseFlowOutputSerializer.InstanceField。
    """

    #: 表名（mysql/spider 命名空间下唯一，前缀 mysql_）
    table_name: str = "mysql_cluster_apply"
    #: 前端表格展示名
    table_display_name: str = _("集群交付信息")
    #: 表主键：每集群主入口(域名:端口)一行，重复写入按该键覆盖合并
    table_primary_key: str = "cluster_domain_and_port"

    cluster_domain_and_port = serializers.CharField(help_text=_("集群域名:port"), required=True, allow_blank=False)
    readonly_domain_and_port = serializers.CharField(help_text=_("只读域名:port"), allow_blank=True, default="")
    clb_ip = serializers.CharField(help_text=_("CLB IP"), allow_blank=True, default="")
    clb_domain = serializers.CharField(help_text=_("CLB域名"), allow_blank=True, default="")
    #: 扩展信息：一列可选的展示文本；前端表格按字符串直接渲染，禁止塞 dict / list 结构化数据
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
