# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel


class McpCalleePlanStatus(models.TextChoices):
    REJECTED = "rejected", _("已拒绝")
    APPROVED = "approved", _("已批准")
    EXPIRED = "expired", _("已过期")


class McpCalleePlan(AuditedModel):
    """
    MCP 计划
    """

    username = models.CharField(max_length=255, help_text=_("发起用户名"))
    callee_mcp_id = models.CharField(max_length=255, help_text=_("被调用 mcp id"))
    params = models.JSONField(default=dict, help_text=_("调用参数"))
    time_window_start = models.DateTimeField(help_text=_("计划生效起始时间"))
    time_window_end = models.DateTimeField(help_text=_("计划生效截止时间"))
    max_call_count = models.PositiveIntegerField(help_text=_("最大调用次数"))
    current_call_count = models.PositiveIntegerField(default=0, help_text=_("已调用次数"))
    status = models.CharField(
        max_length=32,
        choices=McpCalleePlanStatus.choices,
        default=McpCalleePlanStatus.REJECTED,
        help_text=_("审批状态"),
    )
