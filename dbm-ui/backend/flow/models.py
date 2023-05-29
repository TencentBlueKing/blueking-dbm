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
from django.utils.translation import ugettext_lazy as _

from backend.flow.consts import StateType
from backend.ticket.constants import TicketType


class FlowTree(models.Model):
    bk_biz_id = models.IntegerField(_("业务ID"))
    uid = models.CharField(_("单据ID"), max_length=127, db_index=True, blank=True, null=True)
    ticket_type = models.CharField(_("单据类型"), choices=TicketType.get_choices(), max_length=64)
    root_id = models.CharField(_("流程ID"), max_length=33, primary_key=True)
    tree = models.JSONField(_("流程树"), null=True, blank=True)
    status = models.CharField(
        _("流程状态"), default=StateType.CREATED.value, choices=StateType.get_choices(), max_length=20
    )
    created_by = models.CharField(_("流程创建人"), max_length=20, null=True)
    created_at = models.DateTimeField(_("启动时间"), auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(_("流程结束时间"), auto_now=True, blank=True)

    class Meta:
        db_table = "flow_tree"
        ordering = ("-created_at",)


class FlowNode(models.Model):
    uid = models.CharField(_("单据ID"), max_length=127, blank=True, null=True)
    root_id = models.CharField(_("流程ID"), max_length=33)
    node_id = models.CharField(_("节点ID"), max_length=33)
    version_id = models.CharField(_("当前版本ID"), max_length=33, blank=True)
    status = models.CharField(
        _("节点状态"), default=StateType.CREATED.value, choices=StateType.get_choices(), max_length=20
    )
    hosts = models.JSONField(_("节点运行时IP"), blank=True, null=True, default=list)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True, blank=True)
    started_at = models.DateTimeField(_("开始执行时间"), blank=True, null=True)
    updated_at = models.DateTimeField(_("更新时间"), auto_now=True, blank=True)

    class Meta:
        unique_together = ["root_id", "node_id", "version_id"]
        db_table = "flow_node"
