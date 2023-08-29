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

from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import PLAT_BIZ_ID, DBType

__all__ = [
    "CollectTemplate",
    "CollectInstance",
]


class CollectTemplateBase(AuditedModel):
    """采集策略模板"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)
    plugin_id = models.CharField(verbose_name=_("插件ID"), max_length=LEN_MIDDLE, unique=True)
    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )
    details = models.JSONField(verbose_name=_("详情"), default=dict)

    class Meta:
        abstract = True
        verbose_name = _("采集策略模板")


class CollectTemplate(CollectTemplateBase):
    class Meta:
        verbose_name = _("采集策略模板")


class CollectInstance(CollectTemplateBase):
    """采集策略实例"""

    template_id = models.IntegerField(help_text=_("监控插件模板ID"), default=0)
    collect_id = models.IntegerField(help_text=_("监控采集策略ID"))

    class Meta:
        verbose_name = _("采集策略实例")
