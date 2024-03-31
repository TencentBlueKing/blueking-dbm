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
from blueapps.account.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_NORMAL
from backend.bk_web.exceptions import ExternalUserNotExistException


class AuditedModel(models.Model):
    AUDITED_FIELDS = ("creator", "create_at", "updater", "update_at")

    creator = models.CharField(_("创建人"), max_length=LEN_NORMAL)
    create_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    updater = models.CharField(_("修改人"), max_length=LEN_NORMAL)
    update_at = models.DateTimeField(_("更新时间"), auto_now=True)

    class Meta:
        abstract = True


class ExternalUserMapping(models.Model):
    """内外部用户名映射表"""

    external_username = models.CharField(_("外部用户名"), max_length=LEN_NORMAL, unique=True)
    internal_username = models.CharField(_("内部用户名"), max_length=LEN_NORMAL)

    @classmethod
    def get_internal_user(cls, external_user) -> User:
        try:
            user_mapping = cls.objects.get(external_username=external_user)
        except cls.DoesNotExist:
            # 如果没有内部用户与之映射，则提示错误
            raise ExternalUserNotExistException(_("外部用户{}没有注册到DBM平台，请联系管理员注册").format(external_user))
        else:
            internal_user = User(username=user_mapping.internal_username)
            return internal_user
