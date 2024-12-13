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
from typing import Union

from django.db.models.signals import pre_delete

from backend.db_meta.enums import ClusterStatus, ClusterType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.consts import OperateCollectorActionEnum
from backend.flow.utils.cc_manage import trigger_operate_collector

logger = logging.getLogger("root")


def update_cluster_status(sender, instance: Union[StorageInstance, ProxyInstance, Cluster], **kwargs):
    """
    更新存储实例状态的同时更新集群状态
    """
    logger.info("[signals] receive update_cluster_status signal, sender: %s, instance: %s", sender, instance)
    if kwargs.get("created"):
        return
    if kwargs.get("signal") == pre_delete and not isinstance(instance, Cluster):
        # 提前删除实例与cluster的关联关系
        cluster = instance.cluster.first()
        if cluster:
            trigger_operate_collector(
                ClusterType.cluster_type_to_db_type(cluster.cluster_type),
                instance.machine_type,
                bk_instance_ids=[instance.bk_instance_id],
                action=OperateCollectorActionEnum.INSTALL.value,
            )
            if sender == StorageInstance:
                cluster.storageinstance_set.remove(instance)
            elif sender == ProxyInstance:
                cluster.proxyinstance_set.remove(instance)

    # 仅在实例状态变更时，同步更新集群状态
    if isinstance(instance, Cluster):
        clusters = [instance]
    else:
        clusters = instance.cluster.all()

    for cluster in clusters:
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
            logger.info("[signals] update cluster status, origin: %s, target: %s", origin_status, target_status)
            cluster.save(update_fields=["status"])
