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
from backend.configuration.constants import PLAT_BIZ_ID
from backend.db_meta.enums.comm import TagType


class Tag(AuditedModel):
    bk_biz_id = models.IntegerField(help_text=_("业务 ID"), default=0)
    key = models.CharField(help_text=_("标签键"), default="", max_length=64)
    value = models.CharField(help_text=_("标签值"), default="", max_length=255)

    type = models.CharField(help_text=_("tag类型"), max_length=64, choices=TagType.get_choices())
    is_builtin = models.BooleanField(help_text=_("是否内置"), default=False)

    tenant_id = models.CharField(help_text=_("租户ID"), max_length=128, default="default")

    class Meta:
        unique_together = ["bk_biz_id", "key", "value"]

    @property
    def system(self):
        """如果是内置标签，且为平台标签，说明是系统标签"""
        return self.is_builtin and self.bk_biz_id == 0

    @property
    def desc(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "is_builtin": self.is_builtin,
            "system": self.system,
        }

    @classmethod
    def get_builtin_tag(cls, key, value, type):
        """获取内置tag，如果不存在则创建"""
        tag, created = cls.objects.get_or_create(
            key=key,
            value=value,
            type=type,
            is_builtin=True,
            defaults={"bk_biz_id": PLAT_BIZ_ID},
        )
        return tag, created
