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

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.db_meta.models.storage_set_dtl import TenDBClusterStorageSet
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ


def mysql_cluster_topo(cluster_obj: Cluster) -> Dict:
    if cluster_obj.cluster_type == ClusterType.TenDBSingle:
        return __tendbsingle_topo(cluster_obj)
    elif cluster_obj.cluster_type == ClusterType.TenDBHA:
        return __tendbha_topo(cluster_obj)
    else:
        return __tendbcluster_topo(cluster_obj)


def __tendbsingle_topo(cluster_obj: Cluster) -> Dict:
    storage_instance_replicate_sets = []
    all_orphans = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.ORPHAN)
    receiver_ids = set(
        StorageInstanceTuple.objects.using(MYSQL_MCP_DB_READ)
        .filter(ejector__in=all_orphans)
        .values_list("receiver_id", flat=True)
    )

    for master in all_orphans.exclude(id__in=receiver_ids):
        replicate_set = {
            "master_instance": {
                "address": master.ip_port,
                "status": master.status,
                "phase": master.phase,
                "machine_type": master.machine_type,
                "instance_role": master.instance_role,
                "instance_inner_role": master.instance_inner_role,
                "is_stand_by": master.is_stand_by,
                "bk_idc_id": master.machine.bk_idc_id,
                "bk_idc_name": master.machine.bk_idc_name,
                "bk_idc_area_id": master.machine.bk_idc_area_id,
                "bk_idc_area": master.machine.bk_idc_area,
                "bk_sub_zone_id": master.machine.bk_sub_zone_id,
                "bk_sub_zone": master.machine.bk_sub_zone,
            },
        }

        tuples = StorageInstanceTuple.objects.using(MYSQL_MCP_DB_READ).filter(ejector=master)
        if tuples.exists():
            replicate_set["slave_instances"] = [
                {
                    "address": tp.receiver.ip_port,
                    "status": tp.receiver.status,
                    "phase": tp.receiver.phase,
                    "machine_type": tp.receiver.machine_type,
                    "instance_role": tp.receiver.instance_role,
                    "instance_inner_role": tp.receiver.instance_inner_role,
                    "is_stand_by": tp.receiver.is_stand_by,
                    "bk_idc_id": tp.receiver.machine.bk_idc_id,
                    "bk_idc_name": tp.receiver.machine.bk_idc_name,
                    "bk_idc_area_id": tp.receiver.machine.bk_idc_area_id,
                    "bk_idc_area": tp.receiver.machine.bk_idc_area,
                    "bk_sub_zone_id": tp.receiver.machine.bk_sub_zone_id,
                    "bk_sub_zone": tp.receiver.machine.bk_sub_zone,
                }
                for tp in tuples
            ]

        storage_instance_replicate_sets.append(replicate_set)

    return {
        "cluster_type": ClusterType.TenDBSingle.value,
        "storage_instance_replicate_sets": storage_instance_replicate_sets,
    }


def __tendbha_topo(cluster_obj: Cluster) -> Dict:
    storage_instance_replicate_sets = []
    for tp in StorageInstanceTuple.objects.using(MYSQL_MCP_DB_READ).filter(ejector__cluster=cluster_obj):
        storage_instance_replicate_sets.append(
            {
                "master_instance": {
                    "address": tp.ejector.ip_port,
                    "status": tp.ejector.status,
                    "phase": tp.ejector.phase,
                    "machine_type": tp.ejector.machine_type,
                    "instance_role": tp.ejector.instance_role,
                    "instance_inner_role": tp.ejector.instance_inner_role,
                    "is_stand_by": tp.ejector.is_stand_by,
                    # "bk_cloud_id": tp.ejector.machine.bk_cloud_id,
                    "bk_idc_id": tp.ejector.machine.bk_idc_id,
                    "bk_idc_name": tp.ejector.machine.bk_idc_name,
                    "bk_idc_area_id": tp.ejector.machine.bk_idc_area_id,
                    "bk_idc_area": tp.ejector.machine.bk_idc_area,
                    "bk_sub_zone_id": tp.ejector.machine.bk_sub_zone_id,
                    "bk_sub_zone": tp.ejector.machine.bk_sub_zone,
                },
                "slave_instances": [
                    {
                        "address": tp.receiver.ip_port,
                        "status": tp.receiver.status,
                        "phase": tp.receiver.phase,
                        "machine_type": tp.receiver.machine_type,
                        "instance_role": tp.receiver.instance_role,
                        "instance_inner_role": tp.receiver.instance_inner_role,
                        "is_stand_by": tp.receiver.is_stand_by,
                        # "bk_cloud_id": tp.receiver.machine.bk_cloud_id,
                        "bk_idc_id": tp.receiver.machine.bk_idc_id,
                        "bk_idc_name": tp.receiver.machine.bk_idc_name,
                        "bk_idc_area_id": tp.receiver.machine.bk_idc_area_id,
                        "bk_idc_area": tp.receiver.machine.bk_idc_area,
                        "bk_sub_zone_id": tp.receiver.machine.bk_sub_zone_id,
                        "bk_sub_zone": tp.receiver.machine.bk_sub_zone,
                    }
                ],
            }
        )

    return {
        "cluster_type": ClusterType.TenDBHA.value,
        # "cluster_domain": cluster_obj.immute_domain,
        "proxy_instances": [
            {
                "address": p.ip_port,
                "status": p.status,
                "phase": p.phase,
                "machine_type": p.machine_type,
                "role": "",
                # "bk_cloud_id": p.machine.bk_cloud_id,
                "bk_idc_id": p.machine.bk_idc_id,
                "bk_idc_name": p.machine.bk_idc_name,
                "bk_idc_area_id": p.machine.bk_idc_area_id,
                "bk_idc_area": p.machine.bk_idc_area,
                "bk_sub_zone_id": p.machine.bk_sub_zone_id,
                "bk_sub_zone": p.machine.bk_sub_zone,
            }
            for p in cluster_obj.proxyinstance_set.all()
        ],
        "storage_instance_replicate_sets": storage_instance_replicate_sets,
    }


def _get_shard_id(tp: StorageInstanceTuple) -> int:
    """
    获取 StorageInstanceTuple 对应的 shard_id
    迁移期间会存在三类 tuple:
      1. remote_master -> remote_slave (绑定了 TenDBClusterStorageSet, 可直接获取 shard_id)
      2. remote_master -> remote_repeater (未绑定, 通过 ejector 即 remote_master 找到第 1 类 tuple 获取 shard_id)
      3. remote_repeater -> new remote_slave (未绑定, 沿 replication chain 向上找到 remote_master 再获取 shard_id)
    """
    try:
        return tp.tendbclusterstorageset.shard_id
    except TenDBClusterStorageSet.DoesNotExist:
        pass

    if (
        tp.ejector.instance_role == InstanceRole.REMOTE_MASTER
        and tp.receiver.instance_role == InstanceRole.REMOTE_REPEATER
    ):
        bound = (
            TenDBClusterStorageSet.objects.using(MYSQL_MCP_DB_READ)
            .filter(storage_instance_tuple__ejector=tp.ejector)
            .first()
        )
        if bound:
            return bound.shard_id

    elif tp.ejector.instance_role == InstanceRole.REMOTE_REPEATER:
        upstream = (
            StorageInstanceTuple.objects.using(MYSQL_MCP_DB_READ)
            .filter(receiver=tp.ejector, ejector__instance_role=InstanceRole.REMOTE_MASTER)
            .first()
        )
        if upstream:
            bound = (
                TenDBClusterStorageSet.objects.using(MYSQL_MCP_DB_READ)
                .filter(storage_instance_tuple__ejector=upstream.ejector)
                .first()
            )
            if bound:
                return bound.shard_id

    return -1


def __tendbcluster_topo(cluster_obj: Cluster) -> Dict:
    storage_instance_replicate_sets = []
    for tp in StorageInstanceTuple.objects.using(MYSQL_MCP_DB_READ).filter(ejector__cluster=cluster_obj):
        storage_instance_replicate_sets.append(
            {
                "shard_id": _get_shard_id(tp),
                "master_instance": {
                    "address": tp.ejector.ip_port,
                    "status": tp.ejector.status,
                    "phase": tp.ejector.phase,
                    "machine_type": tp.ejector.machine_type,
                    "instance_role": tp.ejector.instance_role,
                    "instance_inner_role": tp.ejector.instance_inner_role,
                    "is_stand_by": tp.ejector.is_stand_by,
                    # "bk_cloud_id": tp.ejector.machine.bk_cloud_id,
                    "bk_idc_id": tp.ejector.machine.bk_idc_id,
                    "bk_idc_name": tp.ejector.machine.bk_idc_name,
                    "bk_idc_area_id": tp.ejector.machine.bk_idc_area_id,
                    "bk_idc_area": tp.ejector.machine.bk_idc_area,
                    "bk_sub_zone_id": tp.ejector.machine.bk_sub_zone_id,
                    "bk_sub_zone": tp.ejector.machine.bk_sub_zone,
                },
                "slave_instances": [
                    {
                        "address": tp.receiver.ip_port,
                        "status": tp.receiver.status,
                        "phase": tp.receiver.phase,
                        "machine_type": tp.receiver.machine_type,
                        "instance_role": tp.receiver.instance_role,
                        "instance_inner_role": tp.receiver.instance_inner_role,
                        "is_stand_by": tp.receiver.is_stand_by,
                        # "bk_cloud_id": tp.receiver.machine.bk_cloud_id,
                        "bk_idc_id": tp.receiver.machine.bk_idc_id,
                        "bk_idc_name": tp.receiver.machine.bk_idc_name,
                        "bk_idc_area_id": tp.receiver.machine.bk_idc_area_id,
                        "bk_idc_area": tp.receiver.machine.bk_idc_area,
                        "bk_sub_zone_id": tp.receiver.machine.bk_sub_zone_id,
                        "bk_sub_zone": tp.receiver.machine.bk_sub_zone,
                    }
                ],
            }
        )

    return {
        "cluster_type": ClusterType.TenDBCluster.value,
        # "cluster_domain": cluster_obj.immute_domain,
        "proxy_instances": [
            {
                "address": p.ip_port,
                "status": p.status,
                "phase": p.phase,
                "machine_type": p.machine_type,
                "role": p.tendbclusterspiderext.spider_role,
                # "bk_cloud_id": p.machine.bk_cloud_id,
                "bk_idc_id": p.machine.bk_idc_id,
                "bk_idc_name": p.machine.bk_idc_name,
                "bk_idc_area_id": p.machine.bk_idc_area_id,
                "bk_idc_area": p.machine.bk_idc_area,
                "bk_sub_zone_id": p.machine.bk_sub_zone_id,
                "bk_sub_zone": p.machine.bk_sub_zone,
            }
            for p in cluster_obj.proxyinstance_set.select_related("tendbclusterspiderext", "machine").all()
        ],
        "storage_instance_replicate_sets": storage_instance_replicate_sets,
    }
