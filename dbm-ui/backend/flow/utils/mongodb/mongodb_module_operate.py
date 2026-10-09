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
from typing import Dict, List, Union

from backend.components import CCApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterType
from backend.db_meta.models import Cluster, ClusterMonitorTopo, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_services.cmdb.biz import get_or_create_resource_module
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator
from backend.flow.utils.cc_manage import CcManage, trigger_operate_collector


class MongoDBCCTopoOperator(CCTopoOperator):
    db_type = DBType.MongoDB.value

    def __init__(self, cluster: Union[Cluster, List[Cluster]], ticket_data: dict = None):
        super().__init__(cluster, ticket_data)
        # cluster.id -> {instance_id -> shard_name}
        self._shard_name_cache: Dict[int, Dict[int, str]] = {}

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
                    self._transfer_host_module_if_needed(
                        cluster_type=cluster_type,
                        bk_host_ids=[bk_host_id],
                        target_module_ids=bk_module_ids,
                        is_increment=is_increment,
                    )
                all_bk_instance_ids.extend(self.init_instances_service(machine_type, host_ins_list))

            if all_bk_instance_ids:
                trigger_operate_collector(self.db_type, machine_type, all_bk_instance_ids)

    def transfer_instances_to_cluster_module(
        self, instances: Union[List[StorageInstance], List[ProxyInstance], None], is_increment=False
    ):
        """
        转移实例到对应的集群模块下，并添加服务实例。
        主机已在目标模块时跳过转移接口。
        """
        if not self.is_bk_module_created:
            self.create_bk_module()

        cluster_ids = [cluster.id for cluster in self.clusters]
        cluster_types = Cluster.objects.filter(id__in=cluster_ids).values_list("cluster_type", flat=True).distinct()
        cluster_types_list = list(cluster_types)
        machine_type_instances_map: Dict[str, List[Union[StorageInstance, ProxyInstance]]] = defaultdict(list)
        for ins in instances:
            machine_type_instances_map[ins.machine_type].append(ins)

        for machine_type, ins_list in machine_type_instances_map.items():
            bk_host_ids = list(set([ins.machine.bk_host_id for ins in ins_list]))

            bk_module_ids = list(
                ClusterMonitorTopo.objects.filter(cluster_id__in=cluster_ids, machine_type=machine_type).values_list(
                    "bk_module_id", flat=True
                )
            )
            for cluster_type in cluster_types_list:
                self._transfer_host_module_if_needed(
                    cluster_type=cluster_type,
                    bk_host_ids=bk_host_ids,
                    target_module_ids=bk_module_ids,
                    is_increment=is_increment,
                )
            bk_instance_ids = self.init_instances_service(machine_type, ins_list)
            trigger_operate_collector(self.db_type, machine_type, bk_instance_ids)

    def _transfer_host_module_if_needed(
        self,
        cluster_type: str,
        bk_host_ids: List[int],
        target_module_ids: List[int],
        is_increment: bool = False,
    ):
        """主机已在全部目标模块时跳过 transfer_host_module。"""
        if not bk_host_ids or not target_module_ids:
            return

        pending_host_ids = []
        target_module_id_set = set(target_module_ids)
        relations = CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids}, use_admin=True) or []
        host_modules: Dict[int, set] = defaultdict(set)
        for relation in relations:
            host_modules[relation["bk_host_id"]].add(relation.get("bk_module_id"))

        for bk_host_id in bk_host_ids:
            if target_module_id_set.issubset(host_modules.get(bk_host_id, set())):
                continue
            pending_host_ids.append(bk_host_id)

        if not pending_host_ids:
            return

        CcManage(self.bk_biz_id, cluster_type).transfer_host_module(pending_host_ids, target_module_ids, is_increment)

    def generate_custom_labels(self, ins: Union[StorageInstance, ProxyInstance], cluster: Cluster) -> dict:
        """
        生成 MongoDB 集群分片名称
        MongoReplicaSet 的值为 cluster.name
        MongoShardedCluster 的值为 primary 的 nosqlstoragesetdtl_set.seg_range
        """
        if cluster.cluster_type == ClusterType.MongoReplicaSet.value:
            return {"shard": cluster.name}
        elif (
            cluster.cluster_type == ClusterType.MongoShardedCluster.value
            and ins.instance_role != AccessLayer.PROXY.value
        ):
            return {"shard": self.get_mongo_shard(cluster, ins)}
        return {}

    def _build_shard_name_map(self, cluster: Cluster) -> Dict[int, str]:
        """一次性加载集群实例到分片名称的映射。先遇到的分片名称优先。"""
        shard_name_map: Dict[int, str] = {}
        shard_details = list(cluster.nosqlstoragesetdtl_set.order_by("id").all())
        primary_ids = []
        for detail in shard_details:
            primary_ids.append(detail.instance_id)
            if detail.instance_id not in shard_name_map:
                shard_name_map[detail.instance_id] = detail.seg_range

        if not primary_ids:
            return shard_name_map

        tuples = StorageInstanceTuple.objects.filter(ejector_id__in=primary_ids).order_by("id")
        receivers_by_primary: Dict[int, List[int]] = defaultdict(list)
        for tpl in tuples:
            receivers_by_primary[tpl.ejector_id].append(tpl.receiver_id)

        # 与 primary 使用同一张先遇到优先的映射，避免 secondary 取到后写入的 seg_range
        for primary_id, shard_name in list(shard_name_map.items()):
            for receiver_id in receivers_by_primary.get(primary_id, []):
                if receiver_id not in shard_name_map:
                    shard_name_map[receiver_id] = shard_name

        return shard_name_map

    def get_mongo_shard(self, cluster: Cluster, ins: StorageInstance) -> str:
        """
        获取实例的分片名称。同一 operator 内按 cluster.id 缓存，避免逐实例扫描。
        """
        shard_name_map = self._shard_name_cache.get(cluster.id)
        if shard_name_map is None:
            shard_name_map = self._build_shard_name_map(cluster)
            self._shard_name_cache[cluster.id] = shard_name_map
        return shard_name_map.get(ins.id, "unknown")
