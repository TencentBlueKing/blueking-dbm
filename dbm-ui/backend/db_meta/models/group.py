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

from backend.bk_web.models import AuditedModel


class Group(AuditedModel):
    """
    分组表
    """

    bk_biz_id = models.IntegerField(help_text=_("业务ID"))
    name = models.CharField(_("分组名"), max_length=64)

    class Meta:
        verbose_name = _("分组表(Group)")
        verbose_name_plural = _("分组表(Group)")
        unique_together = ("bk_biz_id", "name")


class GroupInstance(AuditedModel):
    """分组和实例关系绑定表"""

    group_id = models.BigIntegerField(help_text=_("分组ID"))
    instance_id = models.BigIntegerField(help_text=_("实例ID"))

    class Meta:
        verbose_name = _("分组和实例关系绑定表")
        verbose_name_plural = _("分组和实例关系绑定表")
