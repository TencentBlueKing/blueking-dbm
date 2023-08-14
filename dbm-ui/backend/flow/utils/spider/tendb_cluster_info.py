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
import copy

from backend.db_meta.models import Cluster, StorageInstance


def get_remotedb_info(ip: str, bk_cloud_id: int) -> list:
    nodes = []
    storage_instances = StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)
    for one in storage_instances:
        # storage = one.__dict__
        storage = {
            "version": one.version,
            "port": one.port,
            "bk_biz_id": one.bk_biz_id,
            "status": one.status,
            "instance_role": one.instance_role,
            "phase": one.phase,
            "bk_instance_id": one.bk_instance_id,
            "db_module_id": one.db_module_id,
            "ip": ip,
            "bk_cloud_id": bk_cloud_id,
        }
        nodes.append(storage)
    return nodes


def get_rollback_clusters_info(
    source_cluster_id: int,
    target_cluster_id: int,
):
    ip_list = []
    cluster_info = {"shards": {}, "source_spiders": [], "target_spiders": []}
    source_obj = Cluster.objects.get(id=source_cluster_id)
    target_obj = Cluster.objects.get(id=target_cluster_id)
    source_spiders = source_obj.proxyinstance_set.filter()
    target_spiders = target_obj.proxyinstance_set.filter()
    for spider in source_spiders:
        cluster_info["source_spiders"].append(spider.simple_desc)
    for spider in target_spiders:
        cluster_info["target_spiders"].append(spider.simple_desc)
        ip_list.append(spider.machine.ip)

    cluster_info["source"] = source_obj.to_dict()
    cluster_info["target"] = target_obj.to_dict()
    shards = source_obj.tendbclusterstorageset_set.filter()
    new_shards = target_obj.tendbclusterstorageset_set.filter()
    if len(shards) != len(new_shards):
        return None
    for shard in shards:
        master_obj = StorageInstance.objects.get(id=shard.storage_instance_tuple.ejector_id)
        slave_obj = StorageInstance.objects.get(id=shard.storage_instance_tuple.receiver_id)
        shards_info = {"master": master_obj.simple_desc, "slave": slave_obj.simple_desc}
        cluster_info["shards"][shard.shard_id] = shards_info

    for shard in new_shards:
        master_obj = StorageInstance.objects.get(id=shard.storage_instance_tuple.ejector_id)
        slave_obj = StorageInstance.objects.get(id=shard.storage_instance_tuple.receiver_id)
        shards_info = {"new_master": master_obj.simple_desc, "new_slave": slave_obj.simple_desc}
        ip_list.append(master_obj.machine.ip)
        ip_list.append(slave_obj.machine.ip)
        if shard.shard_id in cluster_info["shards"]:
            cluster_info["shards"][shard.shard_id].update(shards_info)
        else:
            return None
    ip_list = list(set(ip_list))
    cluster_info["ip_list"] = ip_list
    return cluster_info


def get_cluster_info(cluster_id: int):
    """
    获取集群相关信息
    """
    cluster_info = {
        "shards": {},
        "spiders": [],
        "shard_ids": [],
        "masters": [],
        "slaves": [],
        "master_slave_map": {},
    }
    source_obj = Cluster.objects.get(id=cluster_id)
    source_spiders = source_obj.proxyinstance_set.filter()
    for spider in source_spiders:
        cluster_info["spiders"].append(spider.simple_desc)
    cluster_info["cluster"] = source_obj.to_dict()
    cluster_info["cluster"]["cluster_id"] = source_obj.id
    cluster_info["cluster_id"] = source_obj.id
    cluster_info["bk_cloud_id"] = source_obj.bk_cloud_id
    cluster_info["bk_biz_id"] = source_obj.bk_biz_id
    cluster_info["db_module_id"] = source_obj.db_module_id
    cluster_info["cluster_type"] = source_obj.cluster_type
    shards = source_obj.tendbclusterstorageset_set.filter()
    for shard in shards:
        master_obj = StorageInstance.objects.get(id=shard.storage_instance_tuple.ejector_id)
        slave_obj = StorageInstance.objects.get(id=shard.storage_instance_tuple.receiver_id)
        shards_info = {"master": master_obj.simple_desc, "slave": slave_obj.simple_desc}
        cluster_info["shards"][shard.shard_id] = shards_info
        cluster_info["shard_ids"].append(shard.shard_id)
        cluster_info["masters"].append(master_obj.machine.ip)
        cluster_info["slaves"].append(slave_obj.machine.ip)
        cluster_info["master_slave_map"][master_obj.machine.ip] = slave_obj.machine.ip
    cluster_info["shard_ids"].sort()
    cluster_info["masters"] = list(set(copy.deepcopy(cluster_info["masters"])))
    cluster_info["slaves"] = list(set(copy.deepcopy(cluster_info["slaves"])))
    cluster_info["masters"].sort()
    cluster_info["slaves"].sort()
    return cluster_info
