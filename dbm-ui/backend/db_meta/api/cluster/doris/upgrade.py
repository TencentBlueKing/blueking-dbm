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
import logging

from django.db import transaction

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def upgrade(cluster_id: int, new_major_version: str):
    """
    升级Doris集群元数据：更新集群major_version和所有实例的version

    @param cluster_id: 集群ID（必须为 Doris 类型，非 Doris 集群会抛 Cluster.DoesNotExist）
    @param new_major_version: 新版本号，如 "3.0.4"
    """

    # 限定 cluster_type=Doris，避免上层调用方误传非 Doris 集群 ID 导致非预期更新
    cluster = Cluster.objects.get(id=cluster_id, cluster_type=ClusterType.Doris.value)
    old_version = cluster.major_version
    cluster.major_version = new_major_version
    cluster.save(update_fields=["major_version"])

    # 同步更新集群下所有StorageInstance的version
    updated = StorageInstance.objects.filter(cluster=cluster).update(version=new_major_version)
    logger.info(
        "doris cluster[%s] meta upgraded: %s -> %s, %d storage instances updated",
        cluster_id,
        old_version,
        new_major_version,
        updated,
    )
