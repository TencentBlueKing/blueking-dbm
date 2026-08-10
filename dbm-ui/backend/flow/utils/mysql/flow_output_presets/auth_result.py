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

mysql/spider 授权 / 权限变更结果类摘要预设。

职责：
  - 描述"每个集群一行"的授权 / 权限变更执行结果（授权 / 回收 / 变更）。
  - 通过 table_primary_key = "cluster_domain" 保证节点重试对同一集群的二次写入走覆盖合并。

数据源 / 调用通道：
  - 由 mysql / spider 授权类流程节点（authorize_rules / authorize_rules_v2 / revoke 等）在授权 RPC
    完成后调用：`FlowOutputHandler(AuthResultSummarySerializer).insert_data(root_id, data)`。

边界：
  - 与仓内既有 `AuthResultSerializer`（authorize_rules.py 内的单据专属版本）职责相似，但本预设作为
    mysql/spider 全量单据的共享入口存在；旧代码不强制迁移。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class AuthResultSummarySerializer(BaseFlowOutputSerializer):
    """mysql / spider 授权结果摘要（每集群一行）。

    功能说明：
      - 描述授权 / 回收 / 权限变更的执行结果，供前端在单据执行摘要 tab 中展示。
      - 通过 `table_primary_key = "cluster_domain"` 让 FlowOutputHandler.insert_data 对同集群的
        重复写入走"后写覆盖前写"分支，天然幂等。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain (str, 必填, 非空): 集群不可变域名，作为主键
      - account (str, 必填, 非空): 被授权 / 回收的账号
      - privileges (str, 必填, 允许空串): 权限描述文本（如 "SELECT, INSERT"）
      - status (str, 必填, 非空): 执行状态（success / failed / skipped）
      - message (str, 可空, 默认 ""): 详细消息 / 错误原因
      - extra (str, 可空, 默认 ""): 单据私有展示文本兜底；前端按纯文本渲染

    输出：
      - 写入 FlowSummary.summary 中 table_name = "mysql_auth_result" 的表 values。

    边界：
      - cluster_domain / account / status 缺失或空串 -> is_valid 抛 ValidationError。
      - privileges 允许空串（例如仅回收操作时可传空）。
      - 重复主键写入 -> 依赖 insert_data 主键合并分支覆盖旧行，行数不变。
    """

    #: 表名（mysql/spider 命名空间下唯一，前缀 mysql_）
    table_name: str = "mysql_auth_result"
    #: 前端表格展示名
    table_display_name: str = _("授权变更结果")
    #: 表主键：每集群一行，重复写入按 cluster_domain 覆盖合并
    table_primary_key: str = "cluster_domain"

    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=True, allow_blank=False)
    account = serializers.CharField(help_text=_("账号"), required=True, allow_blank=False)
    privileges = serializers.CharField(help_text=_("权限"), required=True, allow_blank=True)
    status = serializers.CharField(help_text=_("结果状态"), required=True, allow_blank=False)
    message = serializers.CharField(help_text=_("详细消息"), allow_blank=True, default="")
    #: 单据私有展示文本兜底；前端按纯文本渲染，禁止塞 dict / list 结构化数据
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
