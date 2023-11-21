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

from backend.bk_web.constants import LEN_MIDDLE, LEN_SHORT


class Profile(models.Model):
    username = models.CharField(_("用户名"), max_length=LEN_MIDDLE)
    label = models.CharField(_("标签"), max_length=LEN_SHORT)
    values = models.JSONField(_("配置值"))

    class Meta:
        verbose_name = verbose_name_plural = _("个人偏好(Profile)")
        unique_together = ("username", "label")
