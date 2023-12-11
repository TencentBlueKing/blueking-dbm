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
from typing import Union

from backend.db_meta.enums import ClusterStatus
from backend.db_meta.models import ProxyInstance, StorageInstance


def update_cluster_status(sender, instance: Union[StorageInstance, ProxyInstance], **kwargs):
    """
    更新存储实例状态的同时更新集群状态
    """
    if kwargs.get("created"):
        return
    # 仅在实例状态变更时，同步更新集群状态
    for cluster in instance.cluster.all():
        # 忽略临时集群
        if cluster.status == ClusterStatus.TEMPORARY.value:
            return
        origin_status = cluster.status
        if cluster.status_flag:
            target_status = ClusterStatus.ABNORMAL.value
        else:
            target_status = ClusterStatus.NORMAL.value
        if origin_status != target_status:
            cluster.status = target_status
            cluster.save(update_fields=["status"])
