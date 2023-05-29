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


# 1. 提供机器城市到逻辑城市的映射, 如机器的城市属性是扬州的, 实际当作南京看待
# 2. 两类城市需要预先人工注册
class LogicalCity(AuditedModel):
    """
    逻辑上的城市
    """

    name = models.CharField(max_length=128, unique=True, default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = verbose_name_plural = _("逻辑城市表(LogicalCity)")


class BKCity(AuditedModel):
    """
    机器实际的城市
    """

    bk_idc_city_id = models.IntegerField(primary_key=True, default=0)
    bk_idc_city_name = models.CharField(max_length=128, unique=True, default="", help_text=_("IDC 城市名"))
    logical_city = models.ForeignKey(LogicalCity, on_delete=models.PROTECT)

    def __str__(self):
        return self.bk_idc_city_name

    class Meta:
        verbose_name = verbose_name_plural = _("蓝鲸城市表(BKCity)")
