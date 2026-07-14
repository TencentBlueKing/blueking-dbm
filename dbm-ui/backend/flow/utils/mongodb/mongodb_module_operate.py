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

from collections import defaultdict
from typing import List, Union

from backend.components import CCApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterType
from backend.db_meta.models import Cluster, ClusterMonitorTopo, ProxyInstance, StorageInstance
from backend.db_services.cmdb.biz import get_or_create_resource_module
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator
from backend.flow.utils.cc_manage import CcManage, trigger_operate_collector


class MongoDBCCTopoOperator(CCTopoOperator):
    db_type = DBType.MongoDB.value

    @staticmethod
    def resolve_replicaset_deploy_is_increment(bk_host_id: int, resource_module_id: int) -> bool:
        """
        副本集部署转模块策略：
        - 主机当前在 resource.idle.module：覆盖转移（is_increment=False）
        - 否则：增量挂模块（is_increment=True）
        """
        relations = CCApi.find_host_biz_relations({"bk_host_id": [bk_host_id]}, use_admin=True)
        if not relations:
            return True
        current_module_id = relations[0].get("bk_module_id")
        if current_module_id == resource_module_id:
            return False
        return True

    def transfer_replicaset_deploy_instances_to_cluster_module(
        self, instances: Union[List[StorageInstance], List[ProxyInstance]]
    ):
        """
        副本集部署上架：按主机串行转模块，并依据是否在资源池模块决定 is_increment。
        """
        if not self.is_bk_module_created:
            self.create_bk_module()

        cluster_ids = [cluster.id for cluster in self.clusters]
        cluster_types_list = list(
            Cluster.objects.filter(id__in=cluster_ids).values_list("cluster_type", flat=True).distinct()
        )
        machine_type_instances_map = defaultdict(list)
        for ins in instances:
            machine_type_instances_map[ins.machine_type].append(ins)

        resource_module_id = get_or_create_resource_module()

        for machine_type, ins_list in machine_type_instances_map.items():
            bk_module_ids = list(
                ClusterMonitorTopo.objects.filter(cluster_id__in=cluster_ids, machine_type=machine_type).values_list(
                    "bk_module_id", flat=True
                )
            )
            host_instances_map = defaultdict(list)
            for ins in ins_list:
                host_instances_map[ins.machine.bk_host_id].append(ins)

            all_bk_instance_ids = []
            for bk_host_id in sorted(host_instances_map.keys()):
                is_increment = self.resolve_replicaset_deploy_is_increment(bk_host_id, resource_module_id)
                host_ins_list = host_instances_map[bk_host_id]
                for cluster_type in cluster_types_list:
                    CcManage(self.bk_biz_id, cluster_type).transfer_host_module(
                        [bk_host_id], bk_module_ids, is_increment
                    )
                all_bk_instance_ids.extend(self.init_instances_service(machine_type, host_ins_list))

            if all_bk_instance_ids:
                trigger_operate_collector(self.db_type, machine_type, all_bk_instance_ids)

    def generate_custom_labels(self, ins: Union[StorageInstance, ProxyInstance], cluster: Cluster) -> dict:
        """
        生成 MongoDB 集群分片标签
        MongoReplicaSet 的值为cluster.name
        MongoShardedCluster 的值为 primary的nosqlstoragesetdtl_set.seg_range
        """
        try:
            if cluster.cluster_type == ClusterType.MongoReplicaSet.value:
                return {"shard": cluster.name}
            elif (
                cluster.cluster_type == ClusterType.MongoShardedCluster.value
                and ins.instance_role != AccessLayer.PROXY.value
            ):
                return {"shard": self.get_mongo_shard(cluster, ins)}
            return {}
        except Exception as e:
            raise e

    @staticmethod
    def get_mongo_shard(cluster: Cluster, ins: StorageInstance) -> str:
        """
        获取 ins的分片信息
        """

        for m in cluster.nosqlstoragesetdtl_set.all():
            if m.instance == ins:
                return m.seg_range
            for e in m.instance.as_ejector.all():
                if e.receiver == ins:
                    return m.seg_range
        return "unknown"
