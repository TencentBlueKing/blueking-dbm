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

from .distribution import Distribution


class VersionSeries(AuditedModel):
    """
    目前版本系列没有独立属性
    但是不知道版本系列后续会不会有
    所以现在就直接拆开吧, 毕竟在 ui 交互上已经有 新建系列 这样的动作了
    """

    distribution = models.ForeignKey(Distribution, on_delete=models.PROTECT, blank=True, null=True)
    name = models.CharField(max_length=128, default="", help_text=_("版本系列"))

    class Meta:
        app_label = "db_meta"
        unique_together = [("distribution", "name")]
