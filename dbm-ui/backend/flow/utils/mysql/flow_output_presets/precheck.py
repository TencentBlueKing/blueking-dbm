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

mysql/spider 校验（precheck）结果类摘要预设。

职责：
  - 描述"每个集群一行"的前置校验结果（schema 兼容 / 连接 / 版本兼容 / 磁盘水位等）。
  - 通过 table_primary_key = "cluster_domain" 保证节点重试对同一集群的二次校验结果走覆盖合并。

数据源 / 调用通道：
  - 由 mysql / spider 变更前的 precheck 类流程节点调用：
    `FlowOutputHandler(PrecheckResultSummarySerializer).insert_data(root_id, data)`。

边界：
  - check_type 语义由业务侧约定字符串（如 "schema" / "connection" / "version"），不做枚举强约束。
  - 若单个集群存在多类 precheck（schema + connection 各出一条），当前预设按"最后一次结果"覆盖；
    如需分别展示，应改用 (cluster_domain, check_type) 组合场景（此时应新建组合主键的预设或走
    dynamic_key 机制），不属于本预设的常规使用范畴。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class PrecheckResultSummarySerializer(BaseFlowOutputSerializer):
    """mysql / spider 前置校验结果摘要（每集群一行）。

    功能说明：
      - 描述变更前置校验的执行结果，供前端在单据执行摘要 tab 中展示。
      - 通过 `table_primary_key = "cluster_domain"` 让 FlowOutputHandler.insert_data 对同集群的
        重复写入走"后写覆盖前写"分支，天然幂等。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain (str, 必填, 非空): 集群不可变域名，作为主键
      - check_type (str, 必填, 非空): 校验类型（如 "schema" / "connection" / "version"）
      - status (str, 必填, 非空): 校验结果（pass / fail / warning）
      - detail (str, 可空, 默认 ""): 详细描述 / 失败原因
      - extra (str, 可空, 默认 ""): 单据私有展示文本兜底；前端按纯文本渲染

    输出：
      - 写入 FlowSummary.summary 中 table_name = "mysql_precheck_result" 的表 values。

    边界：
      - cluster_domain / check_type / status 缺失或空串 -> is_valid 抛 ValidationError。
      - 同集群多类校验 -> 后写覆盖前写；如需并存请另行设计组合主键场景。
    """

    #: 表名（mysql/spider 命名空间下唯一，前缀 mysql_）
    table_name: str = "mysql_precheck_result"
    #: 前端表格展示名
    table_display_name: str = _("前置校验结果")
    #: 表主键：每集群一行，重复写入按 cluster_domain 覆盖合并
    table_primary_key: str = "cluster_domain"

    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=True, allow_blank=False)
    check_type = serializers.CharField(help_text=_("校验类型"), required=True, allow_blank=False)
    status = serializers.CharField(help_text=_("校验结果"), required=True, allow_blank=False)
    detail = serializers.CharField(help_text=_("详情"), allow_blank=True, default="")
    #: 单据私有展示文本兜底；前端按纯文本渲染，禁止塞 dict / list 结构化数据
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
