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


class TbTendisDtsDistributeLock(models.Model):
    id = models.BigAutoField(primary_key=True)
    lock_key = models.CharField(max_length=255, unique=True, verbose_name=_("锁的唯一标识"))
    holder = models.CharField(max_length=128, verbose_name=_("锁的持有者"))
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))
    lock_expire_time = models.DateTimeField(auto_now=False, verbose_name=_("锁的过期时间"))

    class Meta:
        db_table = "tb_tendis_dts_distribute_lock"
        indexes = [
            models.Index(fields=["lock_key"]),
        ]
