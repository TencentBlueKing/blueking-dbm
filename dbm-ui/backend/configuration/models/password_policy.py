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

from typing import Optional

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_SHORT
from backend.configuration.constants import INIT_PASSWORD_POLICY
from backend.db_services.dbpermission.constants import AccountType


class PasswordPolicy(models.Model):
    account_type = models.CharField(
        _("账号类型"), choices=AccountType.get_choices(), max_length=LEN_SHORT, primary_key=True
    )
    policy = models.JSONField(_("密码安全策略"))

    class Meta:
        verbose_name = verbose_name_plural = _("密码安全策略(PasswordPolicy)")

    @classmethod
    def safe_get(cls, account_type: str) -> Optional["PasswordPolicy"]:
        """
        安全的获取密码策略
        :param account_type: 账号类型
        """

        try:
            policy = cls.objects.get(account_type=account_type)
        except cls.DoesNotExist:
            # 如果不存在，则创建一个初始化的规则
            policy = cls.objects.create(account_type=account_type, policy=INIT_PASSWORD_POLICY)

        return policy
