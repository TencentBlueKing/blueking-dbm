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
from backend.core.encrypt.constants import AsymmetricCipherConfigType, AsymmetricCipherKeyType, AsymmetricCipherType


class AsymmetricCipherKey(AuditedModel):
    name = models.CharField(_("密钥名称"), max_length=128, choices=AsymmetricCipherConfigType.get_choices())
    type = models.CharField(_("密钥类型"), max_length=64, choices=AsymmetricCipherKeyType.get_choices())
    algorithm = models.CharField(_("非对称加密算法"), max_length=64, choices=AsymmetricCipherType.get_choices())

    description = models.TextField(_("密钥描述"), default="", null=True)
    content = models.TextField(_("密钥内容"))

    class Meta:
        verbose_name = _("非对称密钥")
        verbose_name_plural = _("非对称密钥")

        # 唯一性校验，name-type
        unique_together = (("name", "type", "algorithm"),)
