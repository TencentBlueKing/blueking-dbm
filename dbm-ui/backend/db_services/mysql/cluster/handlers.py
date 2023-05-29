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
from typing import Any, Dict, List, Set

from django.db.models import Prefetch, Q
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import AccessLayer, ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import InstanceNotExistException
from backend.db_meta.models import Cluster, DBModule, ProxyInstance, StorageInstance
from backend.db_meta.models.machine import Machine
from backend.db_services.mysql.dataclass import ClusterFilter, DBInstance


class ClusterServiceHandler:
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    def find_related_clusters_by_cluster_ids(
        self,
        cluster_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """
        查询集群同机关联的集群，取 master 所在的实例进一步进行查询
        HostA: cluster1.master, cluster2.master, cluster3.master
        HostB: cluster1.slave, cluster2.slave, cluster3.slave
        HostC: cluster2.slave, cluster3.slave （在 cluster2, cluster3 上单独添加从库，一主多从）
        HostD: cluster1.proxy1, cluster2.proxy1, cluster3.proxy1
        HostE: cluster1.proxy2, cluster2.proxy2, cluster3.proxy2
        HostF: cluster1.proxy3 （在 cluster1 上单独添加 Proxy）

        input: cluster_ids=[1]
        output: [cluster1, cluster2, cluster3]

        input: cluster_ids=[2, 3]
        output: [cluster1, cluster2, cluster3]
        """
        masters = StorageInstance.objects.select_related("machine").filter(
            cluster__id__in=cluster_ids, instance_inner_role=InstanceInnerRole.MASTER.value
        )
        if not masters.exists():
            raise InstanceNotExistException(_("无法找到集群{}所包含实例，请检查集群相关信息").format(cluster_ids))

        related_clusters = self.find_related_clusters_by_instances(
            [DBInstance.from_inst_obj(master) for master in masters]
        )
        cluster_id_related_clusters_map = {data["cluster_info"]["id"]: data for data in related_clusters}
        return [
            {
                "cluster_id": cluster_id,
                "cluster_info": cluster_id_related_clusters_map[cluster_id]["cluster_info"],
                "related_clusters": cluster_id_related_clusters_map[cluster_id]["related_clusters"],
            }
            for cluster_id in cluster_ids
        ]

    def find_related_clusters_by_instances(self, instances: List[DBInstance]) -> List[Dict[str, Any]]:
        """
        查询集群同机关联的集群
        HostA: cluster1.master1, cluster2.master1, cluster3.master1
        HostB: cluster1.slave1, cluster2.slave1, cluster3.slave1
        HostC: cluster2.slave2, cluster3.slave2 （在 cluster2, cluster3 上单独添加从库，一主多从）
        HostD: cluster1.proxy1, cluster2.proxy1, cluster3.proxy1
        HostE: cluster1.proxy2, cluster2.proxy2, cluster3.proxy2
        HostF: cluster1.proxy3 （在 cluster1 上单独添加 Proxy）

        input: instances=[cluster1.master1]
        output: [cluster1, cluster2, cluster3]

        input: instances=[cluster2.slave1]
        output: [cluster1, cluster2, cluster3]

        input: instances=[cluster2.slave2]
        output: [cluster2, cluster3]

        input: instances=[cluster1.proxy3]
        output: [cluster3]
        """
        inst_cluster_map = {}
        host_id_related_cluster = defaultdict(list)
        # 基于 存储实例 和 Proxy 不会混部 的原则
        bk_host_ids = [instance.bk_host_id for instance in instances]
        instance_objs = [
            *list(
                StorageInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id__in=bk_host_ids)
            ),
            *list(
                ProxyInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id__in=bk_host_ids)
            ),
        ]
        for inst_obj in instance_objs:
            inst_data = DBInstance.from_inst_obj(inst_obj)
            inst_cluster_map[str(inst_data)] = model_to_dict(inst_obj.cluster.first())
            host_id_related_cluster[inst_obj.machine.bk_host_id].extend(inst_obj.cluster.all())

        return [
            {
                "instance_address": f"{instance.ip}:{instance.port}",
                "bk_host_id": instance.bk_host_id,
                "cluster_info": self._format_cluster_field(inst_cluster_map[str(instance)]),
                "related_clusters": [
                    self._format_cluster_field(model_to_dict(cluster))
                    for cluster in host_id_related_cluster[instance.bk_host_id]
                    if cluster.id != inst_cluster_map[str(instance)]["id"]
                ],
            }
            for instance in instances
        ]

    def query_clusters(self, cluster_filters: List[ClusterFilter]) -> List[Dict[str, Any]]:
        """
        根据过滤条件查询集群，默认是精确匹配
        """

        filter_conditions = Q()
        for cluster_filter in cluster_filters:
            filter_conditions |= Q(**cluster_filter.export_filter_conditions())

        clusters = Cluster.objects.prefetch_related("storageinstance_set", "proxyinstance_set").filter(
            filter_conditions
        )
        cluster_db_module_ids = [cluster.db_module_id for cluster in clusters]
        db_module_names = {
            module.db_module_id: module.db_module_name
            for module in DBModule.objects.filter(db_module_id__in=cluster_db_module_ids)
        }

        filter_cluster_list = []
        for cluster in clusters:
            cluster_info = self._format_cluster_field(model_to_dict(cluster))
            cluster_info["db_module_name"] = db_module_names.get(cluster_info["db_module_id"], "")

            # 添加实例信息
            cluster_info["instance_count"] = (
                cluster.storageinstance_set.all().count() + cluster.proxyinstance_set.all().count()
            )
            cluster_info["masters"] = []
            cluster_info["slaves"] = []
            cluster_info["repeaters"] = []
            # 录入proxy instance的信息和storage instance的信息
            cluster_info["proxies"] = [inst.simple_desc for inst in cluster.proxyinstance_set.all()]
            for inst in cluster.storageinstance_set.all():
                role = "masters" if cluster.cluster_type == ClusterType.TenDBSingle else f"{inst.instance_inner_role}s"
                cluster_info[role].append(inst.simple_desc)

            filter_cluster_list.append(cluster_info)

        return filter_cluster_list

    def get_intersected_machines_from_clusters(self, cluster_ids: List[int], role: str):
        """
        获取关联集群特定实例角色的交集
        cluster1: slave1, slave2, slave3
        cluster2: slave1, slave2
        cluster3： slave1, slave3

        input: cluster_ids: [1,2,3]
        output: [slave1]
        --------------------------
        :param cluster_ids: 集群id列表
        :param role: 实例角色
        """
        if role == AccessLayer.PROXY.value:
            lookup_field = "proxyinstance_set"
            instances = ProxyInstance.objects.select_related("machine").filter(
                cluster__id__in=cluster_ids, access_layer=role
            )
        else:
            lookup_field = "storageinstance_set"
            instances = StorageInstance.objects.select_related("machine").filter(
                cluster__id__in=cluster_ids, instance_inner_role=role
            )

        clusters: List[Cluster] = Cluster.objects.prefetch_related(
            Prefetch(lookup_field, queryset=instances, to_attr="instances")
        ).filter(bk_biz_id=self.bk_biz_id, id__in=cluster_ids)

        intersected_machines: Set[Machine] = set.intersection(
            *[set([inst.machine for inst in cluster.instances]) for cluster in clusters]
        )

        intersected_machines_info: List[Dict[str, Any]] = [
            {
                "ip": machine.ip,
                "bk_cloud_id": machine.bk_cloud_id,
                "bk_host_id": machine.bk_host_id,
                "bk_biz_id": machine.bk_biz_id,
            }
            for machine in intersected_machines
        ]

        return intersected_machines_info

    def _format_cluster_field(self, cluster_info: Dict[str, Any]):
        cluster_info["cluster_name"] = cluster_info.pop("name")
        cluster_info["master_domain"] = cluster_info.pop("immute_domain")

        return cluster_info
