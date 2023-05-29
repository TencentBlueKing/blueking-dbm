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

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterEntryType, MachineType


class DBModule(AuditedModel):
    """
    一个 meta_cluster_type 的 db_module 在 cc 上会有 count(meta_type) 个 bk module
    """

    bk_biz_id = models.IntegerField(default=0)
    db_module_name = models.CharField(default="", max_length=200)
    db_module_id = models.BigAutoField(primary_key=True)
    cluster_type = models.CharField(max_length=64, choices=ClusterEntryType.get_choices(), default="")

    class Meta:
        unique_together = [
            ("db_module_id", "bk_biz_id", "cluster_type"),
            ("db_module_name", "bk_biz_id", "cluster_type"),
        ]


class BKModule(AuditedModel):
    bk_module_id = models.IntegerField(primary_key=True)
    db_module_id = models.BigIntegerField(default=0)
    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")
