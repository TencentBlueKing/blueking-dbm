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
from typing import Dict, List

from django.db import transaction

from backend.db_meta.api import common
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def add_slaves(cluster: Cluster, slaves: List[Dict]):
    """
    理论上来说, 只能添加 slave
    与 master 的同步关系要调用 storage_instance_tuple.create
    """

    master_obj = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER)

    slave_objs = common.filter_out_instance_obj(
        slaves,
        StorageInstance.objects.filter(
            instance_inner_role=InstanceInnerRole.SLAVE,
            cluster_type=ClusterType.TenDBHA,
            as_receiver__ejector=master_obj,
        ),
    )

    _t = common.not_exists(slaves, slave_objs)
    if _t:
        raise Exception("{} not match".format(_t))

    _t = common.in_another_cluster(slave_objs)
    if _t:
        raise Exception("{} in another cluster".format(_t))

    cluster.storageinstance_set.add(*slave_objs)

    for ins in slave_objs:
        m = ins.machine
        ins.db_module_id = master_obj.db_module_id
        m.db_module_id = master_obj.db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])
        # ToDo 移动到对应的 bk module


@transaction.atomic
def delete_slaves(cluster: Cluster, slaves: List[Dict]):
    """
    理论上来说, 只能删除 slave
    """

    slave_objs = common.filter_out_instance_obj(slaves, cluster.storageinstance_set)

    _t = common.not_exists(slaves, slave_objs)
    if _t:
        raise Exception("{} not match".format(_t))

    # ToDo 这个删除应该在哪里做?
    # StorageInstanceTuple.objects.filter(receiver__in=slave_objs).delete()
    cluster.storageinstance_set.remove(*slave_objs)
