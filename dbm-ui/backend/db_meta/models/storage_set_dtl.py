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
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple


class ClusterStorageSetABS(AuditedModel):
    cluster = models.ForeignKey(Cluster, on_delete=models.PROTECT)

    class Meta:
        abstract = True


class StorageSetDtl(AuditedModel):
    """
    # No Use (废掉鸭! 重命名/删掉也不行提交不通过_-_)
    """


class NosqlStorageSetDtl(AuditedModel):
    bk_biz_id = models.IntegerField(default=0)

    instance = models.ForeignKey(
        StorageInstance,
        db_column="instance",
        on_delete=models.CASCADE,
    )
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    seg_range = models.CharField(max_length=150, blank=False, default="")

    class Meta:
        unique_together = ("instance", "cluster", "bk_biz_id")

    def __str__(self):
        return "{}:{} {}".format(self.instance.machine.ip, self.instance.port, self.seg_range)


class TenDBClusterStorageSet(ClusterStorageSetABS):
    storage_instance_tuple = models.OneToOneField(
        StorageInstanceTuple,
        on_delete=models.PROTECT,
    )
    # ss = models.OneToOneField(StorageInstance, on_delete=models.PROTECT)
    shard_id = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("cluster", "shard_id"), ("cluster", "storage_instance_tuple")]

    def __str__(self):
        return "{}: {}".format(self.shard_id, self.storage_instance_tuple)
