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
from typing import Dict

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, StorageInstanceTuple


def mysql_cluster_topo(cluster_obj: Cluster) -> Dict:
    if cluster_obj.cluster_type == ClusterType.TenDBSingle:
        return __tendbsingle_topo(cluster_obj)
    elif cluster_obj.cluster_type == ClusterType.TenDBHA:
        return __tendbha_topo(cluster_obj)
    else:
        return __tendbcluster_topo(cluster_obj)


def __tendbsingle_topo(cluster_obj: Cluster) -> Dict:
    storage_instance = cluster_obj.storageinstance_set.get()

    return {
        "cluster_type": ClusterType.TenDBSingle.value,
        # "cluster_domain": cluster_obj.immute_domain,
        "storage_instance_replicate_sets": [
            {
                "master_instance": {
                    "address": storage_instance.ip_port,
                    "status": storage_instance.status,
                    "machine_type": storage_instance.machine_type,
                    "instance_role": storage_instance.instance_role,
                    "instance_inner_role": storage_instance.instance_inner_role,
                    "is_stand_by": storage_instance.is_stand_by,
                }
            }
        ],
    }


def __tendbha_topo(cluster_obj: Cluster) -> Dict:
    storage_instance_replicate_sets = []
    for tp in StorageInstanceTuple.objects.filter(ejector__cluster=cluster_obj):
        storage_instance_replicate_sets.append(
            {
                "master_instance": {
                    "address": tp.ejector.ip_port,
                    "status": tp.ejector.status,
                    "machine_type": tp.ejector.machine_type,
                    "instance_role": tp.ejector.instance_role,
                    "instance_inner_role": tp.ejector.instance_inner_role,
                    "is_stand_by": tp.ejector.is_stand_by,
                },
                "slave_instances": [
                    {
                        "address": tp.receiver.ip_port,
                        "status": tp.receiver.status,
                        "machine_type": tp.receiver.machine_type,
                        "instance_role": tp.receiver.instance_role,
                        "instance_inner_role": tp.receiver.instance_inner_role,
                        "is_stand_by": tp.receiver.is_stand_by,
                    }
                ],
            }
        )

    return {
        "cluster_type": ClusterType.TenDBHA.value,
        # "cluster_domain": cluster_obj.immute_domain,
        "proxy_instances": [
            {"address": p.ip_port, "status": p.status, "machine_type": p.machine_type}
            for p in cluster_obj.proxyinstance_set.all()
        ],
        "storage_instance_replicate_sets": storage_instance_replicate_sets,
    }


def __tendbcluster_topo(cluster_obj: Cluster) -> Dict:
    storage_instance_replicate_sets = []
    for tp in StorageInstanceTuple.objects.filter(ejector__cluster=cluster_obj):
        storage_instance_replicate_sets.append(
            {
                "shard_id": tp.tendbclusterstorageset.shard_id,
                "master_instance": {
                    "address": tp.ejector.ip_port,
                    "status": tp.ejector.status,
                    "machine_type": tp.ejector.machine_type,
                    "instance_role": tp.ejector.instance_role,
                    "instance_inner_role": tp.ejector.instance_inner_role,
                    "is_stand_by": tp.ejector.is_stand_by,
                },
                "slave_instances": [
                    {
                        "address": tp.receiver.ip_port,
                        "status": tp.receiver.status,
                        "machine_type": tp.receiver.machine_type,
                        "instance_role": tp.receiver.instance_role,
                        "instance_inner_role": tp.receiver.instance_inner_role,
                        "is_stand_by": tp.receiver.is_stand_by,
                    }
                ],
            }
        )

    return {
        "cluster_type": ClusterType.TenDBCluster.value,
        # "cluster_domain": cluster_obj.immute_domain,
        "proxy_instances": [
            {"address": p.ip_port, "status": p.status, "machine_type": p.machine_type}
            for p in cluster_obj.proxyinstance_set.all()
        ],
        "storage_instance_replicate_sets": storage_instance_replicate_sets,
    }
