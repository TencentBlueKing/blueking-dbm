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


class TendisDtsServer(models.Model):
    bk_cloud_id = models.BigIntegerField(default=0, verbose_name=_("云区域ID"))
    ip = models.CharField(max_length=128, default="", verbose_name=_("DTS_Server IP"))
    city_id = models.IntegerField(default=0, verbose_name=_("城市ID"))
    city_name = models.CharField(max_length=128, default="", verbose_name=_("城市名"))
    status = models.IntegerField(default=0, verbose_name=_("状态"))
    heartbeat_time = models.DateTimeField(default="1997-01-01 00:00:00", verbose_name=_("最近心跳时间"))
    update_time = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    class Meta:
        db_table = "tb_tendis_dts_server"
        indexes = [
            models.Index(fields=["update_time"], name="index_update_time"),
        ]
        constraints = [models.UniqueConstraint(fields=["bk_cloud_id", "ip"], name="unique_tendis_dts_server")]
