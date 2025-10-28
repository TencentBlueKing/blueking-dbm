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

from django.db.models import Q

from backend.db_meta.enums import ClusterType, MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models import Cluster, NosqlStorageSetDtl
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource


class ToolboxHandler(ClusterServiceHandler):
    """mongodb工具箱查询接口封装"""

    def __init__(self, bk_biz_id: int):
        super().__init__(bk_biz_id)

    @classmethod
    def get_execute_net_tcp_cluster_hosts(cls, cluster):
        cluster_type = cluster.cluster_type
        host_ids = []
        # 有可能连后端Master/slave, 也有可能连接Proxy的
        if cluster_type in [ClusterType.MongoReplicaSet]:
            host_ids = list(cluster.storageinstance_set.values_list("machine__bk_host_id", flat=True))
            host_ids.extend(list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True)))
        # 只连接Proxy的
        elif cluster_type in [ClusterType.MongoShardedCluster]:
            host_ids = list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True))

        return host_ids

    @classmethod
    def get_mongo_shard(cls, bk_biz_id, data):
        cluster_ids = []
        if data.get("cluster_id"):
            cluster_ids.append(data["cluster_id"])
        if data.get("shard_names"):
            cluster_ids.append(
                NosqlStorageSetDtl.objects.filter(seg_range__in=data["shard_names"]).values_list(
                    "cluster__id", flat=True
                )
            )

        cluster_ids = list(set(cluster_ids))
        if cluster_ids:
            clusters = Cluster.objects.filter(id__in=cluster_ids).all()
        else:
            clusters = Cluster.objects.filter(
                bk_biz_id=bk_biz_id, cluster_type=ClusterType.MongoShardedCluster.value
            ).all()
        shard_data = []
        for cluster in clusters:
            mongodb_insts = [
                m for m in cluster.storageinstance_set.all() if m.machine.machine_type == MachineType.MONGODB
            ]
            mongodb = [m.simple_desc for m in mongodb_insts]
            shard_num = cluster.nosqlstoragesetdtl_set.filter(
                instance__machine__machine_type=MachineType.MONGODB
            ).count()
            shard_node_count = len(mongodb) / shard_num
            # 获取各个分片的节点组
            inst_filter = Q(
                instance_role__in=[role for role in MachineTypeInstanceRoleMap[MachineType.MONGODB]],
                cluster=cluster,
                machine_type=MachineType.MONGODB,
            )
            insts, inst_id__shard = MongoDBListRetrieveResource.query_storage_shard(inst_filter)
            shard_name_instance_map = {}
            for inst in insts:
                shard_name = inst_id__shard[inst.id]
                if shard_name in shard_name_instance_map:
                    shard_name_instance_map[shard_name].append(inst)
                else:
                    shard_name_instance_map[shard_name] = [inst]
            shard_data.extend(
                [
                    {
                        "shard_name": shard_name,
                        "related_instance": [inst.simple_desc for inst in shard_name_instance_map[shard_name]],
                        "cluster_id": cluster.id,
                        "master_domain": cluster.immute_domain,
                        "region": cluster.region,
                        "major_version": cluster.major_version,
                        "disaster_tolerance_level": cluster.disaster_tolerance_level,
                        "shard_node_count": shard_node_count,
                    }
                    for shard_name in shard_name_instance_map
                ]
            )
        return shard_data

    @classmethod
    def get_shard_others_instance(cls, storage, cluster):
        inst_filter = Q(
            instance_role__in=[role for role in MachineTypeInstanceRoleMap[MachineType.MONGODB]],
            cluster=cluster,
            machine_type=MachineType.MONGODB,
        )
        insts, inst_id__shard = MongoDBListRetrieveResource.query_storage_shard(inst_filter)
        others_instance = []
        current_shard_name = inst_id__shard[storage.id]
        for inst in insts:
            shard_name = inst_id__shard[inst.id]
            if shard_name == current_shard_name and inst.id != storage.id:
                others_instance.append(inst)
        return others_instance
