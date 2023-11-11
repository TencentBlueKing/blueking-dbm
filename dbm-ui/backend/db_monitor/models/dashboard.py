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

from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType

__all__ = ["Dashboard"]


class Dashboard(AuditedModel):
    """仪表盘"""

    name = models.CharField(verbose_name=_("名称"), max_length=LEN_MIDDLE, default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")

    details = models.JSONField(verbose_name=_("详情"), default=dict)
    variables = models.JSONField(verbose_name=_("变量"), default=dict)

    # grafana相关
    org_id = models.BigIntegerField(verbose_name=_("grafana-org_id"))
    org_name = models.CharField(verbose_name=_("grafana-org_name"), max_length=LEN_NORMAL)
    uid = models.CharField(verbose_name=_("grafana-uid"), max_length=LEN_NORMAL)
    url = models.CharField(verbose_name=_("grafana-url"), max_length=LEN_LONG)

    class Meta:
        verbose_name = _("仪表盘")
