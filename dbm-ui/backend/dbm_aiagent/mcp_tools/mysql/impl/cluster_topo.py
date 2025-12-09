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

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstanceTuple


def mysql_cluster_topo(cluster_type: ClusterType, cluster_domain: str) -> Dict:
    if cluster_type == ClusterType.TenDBSingle:
        return __tendbcluster_topo(cluster_domain)
    elif cluster_type == ClusterType.TenDBHA:
        return __tendbha_topo(cluster_domain)
    else:
        return __tendbcluster_topo(cluster_domain)


def __tendbsingle_topo(cluster_domain: str) -> Dict:
    cluster_obj = Cluster.objects.get(immute_domain=cluster_domain, cluster_type=ClusterType.TenDBSingle)
    storage_instance = cluster_obj.storageinstance_set.get()

    return {
        "cluster_type": ClusterType.TenDBSingle.value,
        "cluster_domain": cluster_domain,
        "storage": {"address": storage_instance.ip_port, "status": storage_instance.status},
    }


def __tendbha_topo(cluster_domain: str) -> Dict:
    cluster_obj = Cluster.objects.get(immute_domain=cluster_domain, cluster_type=ClusterType.TenDBHA)

    return {
        "cluster_type": ClusterType.TenDBHA.value,
        "cluster_domain": cluster_domain,
        "proxy_instance": [
            {"address": p.ip_port, "status": p.status, "machine_type": p.machine_type}
            for p in cluster_obj.proxyinstance_set.all()
        ],
        "storage_instances": [
            {
                "address": s.ip_port,
                "status": s.status,
                "instance_role": s.instance_role,
                "machine_type": s.machine_type,
                "is_stand_by": s.is_stand_by,
            }
            for s in cluster_obj.storageinstance_set.all()
        ],
    }


def __tendbcluster_topo(cluster_domain: str) -> Dict:
    cluster_obj = Cluster.objects.get(cluster_type=ClusterType.TenDBCluster, immute_domain=cluster_domain)

    spider_instances = []
    for p in cluster_obj.proxyinstance_set.all():
        po = {
            "address": p.ip_port,
            "status": p.status,
            "spider_role": p.tendbclusterspiderext.spider_role,
            "machine_type": p.machine_type,
        }

        spider_instances.append(po)

    storage_replicate_sets = []
    for inst in cluster_obj.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER):
        storage_set = {
            "shard_id": 0,
            "instances": [
                {
                    "address": inst.ip_port,
                    "status": inst.status,
                    "instance_role": inst.instance_role,
                    "machine_type": inst.machine_type,
                    "is_stand_by": inst.is_stand_by,
                }
            ],
        }

        for tp in StorageInstanceTuple.objects.filter(ejector=inst):
            storage_set["instances"].append(
                {
                    "address": tp.receiver.ip_port,
                    "status": tp.receiver.status,
                    "instance_role": tp.receiver.instance_role,
                    "machine_type": tp.receiver.machine_type,
                    "is_stand_by": tp.receiver.is_stand_by,
                }
            )

            storage_set["shard_id"] = tp.tendbclusterstorageset.shard_id

        storage_replicate_sets.append(storage_set)

    return {
        "cluster_type": ClusterType.TenDBCluster,
        "cluster_domain": cluster_domain,
        "spider_instances": spider_instances,
        "storage_replicate_sets": storage_replicate_sets,
    }
