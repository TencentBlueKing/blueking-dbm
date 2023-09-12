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
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Q

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, InstanceStatus
from backend.db_meta.models import (
    Cluster,
    ClusterEntry,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
    TenDBClusterStorageSet,
)


@transaction.atomic
def fake_reset_tendbcluster_cluster(
    spider_masters: List[str],
    immute_domain: str,
    storage_sets: List[Dict],
    spider_slaves: Optional[List[str]] = None,
    slave_domain: Optional[str] = None,
):
    """
    storage_sets: [
      {
        "master_instance": "a.b.c.d:20000",
        "slave_instance": "e.f.g.h:20000",
      }
      ...
    ]
    """
    cluster = Cluster.objects.get(immute_domain=immute_domain, cluster_type=ClusterType.TenDBCluster)
    master_entry = ClusterEntry.objects.get(entry=immute_domain, cluster=cluster)
    master_entry.proxyinstance_set.clear()

    TenDBClusterStorageSet.objects.filter(cluster=cluster).delete()

    for idx, storage_set in enumerate(storage_sets):
        [master_ip, master_port] = storage_set["master_instance"].split(IP_PORT_DIVIDER)
        master_obj = StorageInstance.objects.get(machine__ip=master_ip, port=master_port, cluster=cluster)
        master_obj.instance_role = InstanceRole.REMOTE_MASTER.value
        master_obj.instance_inner_role = InstanceInnerRole.MASTER.value
        master_obj.status = InstanceStatus.RUNNING.value
        master_obj.save(update_fields=["instance_role", "instance_inner_role", "status"])

        [slave_ip, slave_port] = storage_set["slave_instance"].split(IP_PORT_DIVIDER)
        slave_obj = StorageInstance.objects.get(machine__ip=slave_ip, port=slave_port, cluster=cluster)
        slave_obj.instance_role = InstanceRole.REMOTE_SLAVE.value
        slave_obj.instance_inner_role = InstanceInnerRole.SLAVE.value
        slave_obj.status = InstanceStatus.RUNNING.value
        slave_obj.save(update_fields=["instance_role", "instance_inner_role", "status"])

        StorageInstanceTuple.objects.filter(
            (Q(ejector=master_obj) & Q(receiver=slave_obj)) | (Q(ejector=slave_obj) & Q(receiver=master_obj))
        ).delete()

        st_obj = StorageInstanceTuple.objects.create(ejector=master_obj, receiver=slave_obj)
        TenDBClusterStorageSet.objects.create(shard_id=idx, cluster=cluster, storage_instance_tuple=st_obj)

    for spider_master in spider_masters:
        [spider_ip, spider_port] = spider_master.split(IP_PORT_DIVIDER)
        spider_obj = ProxyInstance.objects.get(machine__ip=spider_ip, port=spider_port, cluster=cluster)
        spider_obj.storageinstance.clear()
        spider_obj.storageinstance.add(
            *list(
                StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.REMOTE_MASTER.value).all()
            )
        )
        spider_obj.status = InstanceStatus.RUNNING.value
        spider_obj.save(update_fields=["status"])
        master_entry.proxyinstance_set.add(spider_obj)

    if slave_domain and spider_slaves:
        slave_entry = ClusterEntry.objects.get(entry=slave_domain, cluster=cluster)
        slave_entry.storageinstance_set.clear()
        for spider_slave in spider_slaves:
            [spider_ip, spider_port] = spider_slave.split(IP_PORT_DIVIDER)
            spider_obj = ProxyInstance.objects.get(machine__ip=spider_ip, port=spider_port, cluster=cluster)
            spider_obj.storageinstance.clear()
            spider_obj.storageinstance.add(
                *list(
                    StorageInstance.objects.filter(
                        cluster=cluster, instance_role=InstanceRole.REMOTE_SLAVE.value
                    ).all()
                )
            )
            spider_obj.status = InstanceStatus.RUNNING.value
            spider_obj.save(update_fields=["status"])
            slave_entry.proxyinstance_set.add(spider_obj)
