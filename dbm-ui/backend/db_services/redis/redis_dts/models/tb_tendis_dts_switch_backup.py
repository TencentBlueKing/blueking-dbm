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


class TbTendisDtsSwitchBackup(models.Model):
    """
    dts切换备份,便于重试
    """

    id = models.BigAutoField(primary_key=True)
    bill_id = models.BigIntegerField(default=0, db_index=True, verbose_name=_("单据号"))
    src_cluster = models.CharField(max_length=128, default="", verbose_name=_("源集群"))
    dst_cluster = models.CharField(max_length=128, default="", verbose_name=_("目的集群"))
    data_type = models.CharField(max_length=128, default="", verbose_name=_("数据类型"))
    data = models.TextField(default="", verbose_name=_("数据"))

    class Meta:
        db_table = "tb_tendis_dts_switch_backup"
        verbose_name = "Tendis Dts online switch backup"
        verbose_name_plural = "Tendis Dts online switch backup"
        constraints = [
            models.UniqueConstraint(
                fields=["bill_id", "src_cluster", "dst_cluster", "data_type"], name="unique_switch_job_key"
            )
        ]
