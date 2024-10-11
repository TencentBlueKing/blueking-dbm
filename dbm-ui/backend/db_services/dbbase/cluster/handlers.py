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
import importlib
import operator
from collections import defaultdict
from functools import reduce
from typing import Any, Dict, List, Set

from django.db.models import F, Prefetch, Q
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import AccessLayer, ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException, InstanceNotExistException
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_meta.models.machine import Machine
from backend.db_services.dbbase.dataclass import DBInstance
from backend.utils.basic import remove_duplicated_dict


class ClusterServiceHandler:
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    def check_cluster_databases(self, cluster_id: int, db_list: List[int]) -> Dict:
        """
        校验集群的库名是否存在，支持各个类型的集群
        注意：这个方法是通用查询库表是否存在，子类需要单独实现check_cluster_database,而不是覆写该方法
        @param cluster_id: 集群ID
        @param db_list: 库名列表
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(_("集群[]不存在，请检查集群ID").format(cluster_id))

        # mysql校验库存在的模块函数
        if cluster.cluster_type in [ClusterType.TenDBCluster, ClusterType.TenDBHA, ClusterType.TenDBSingle]:
            from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler as MySQL

            check_infos = [{"cluster_id": cluster_id, "db_names": db_list}]
            return MySQL(self.bk_biz_id).check_cluster_database(check_infos)[0]["check_info"]
        # sqlserver校验库存在的模块函数
        if cluster.cluster_type in [ClusterType.SqlserverHA, ClusterType.SqlserverSingle]:
            from backend.db_services.sqlserver.cluster.handlers import ClusterServiceHandler as SQLServer

            return SQLServer(self.bk_biz_id).check_cluster_database(cluster_id, db_list)
        # 对于其他不存在单据校验逻辑的集群类型，直接抛错
        raise NotImplementedError

    def check_cluster_database(self, cluster_id: int, db_list: List[int]):
        """子类可单独实现的校验库表是否存在的逻辑，非必须实现"""
        raise NotImplementedError

    def query_machine_instance_pair(self, query: Dict[str, List[str]]):
        """
        根据主机/实例查询关系对，适用于一主一从关系
         @param query 查询参数，支持查询主机或者实例维度的pair
         eg:
         {
             "machines": ["0:127.0.0.1"],
             "instances": ["127.0.0.1:3306"]
         }
        """
        related_pairs: Dict[str, Dict] = defaultdict(dict)

        def add_pair_instance_info(pair_map, ejector, receiver):
            ejector_key = ejector.ip_port
            pair_map[ejector_key].update(receiver.simple_desc)
            # 填充实例关联的集群
            pair_map[ejector_key]["related_clusters"].append(receiver.cluster.first().simple_desc)

        def add_pair_machine_info(pair_map, ejector, receiver):
            ejector_key = f"{ejector.machine.bk_cloud_id}:{ejector.machine.ip}"
            pair_map[ejector_key].update(receiver.machine.simple_desc)
            # 填充机器关联的集群，自身关联实例和映射关联实例
            pair_map[ejector_key]["related_clusters"].append(receiver.cluster.first().simple_desc)
            pair_map[ejector_key]["related_instances"].append(receiver.simple_desc)
            pair_map[ejector_key]["related_pair_instances"].append(ejector.simple_desc)

        def get_machine_instance_pair_info(tuple_filters, add_func, key):
            # 查询关联实例对
            pairs = (
                StorageInstanceTuple.objects.select_related("ejector__machine", "receiver__machine")
                .prefetch_related("ejector__cluster", "receiver__cluster")
                .filter(tuple_filters)
            )

            if not pairs.exists():
                related_pairs[key] = {}
                return

            pair_map = defaultdict(lambda: defaultdict(list))
            for pair in pairs:
                add_func(pair_map, pair.ejector, pair.receiver)
                add_func(pair_map, pair.receiver, pair.ejector)

            related_pairs[key] = {inst: pair_map[inst] for inst in query[key]}
            # 关联集群和关联实例可能重复，需要去重
            for info in related_pairs[key].values():
                info["related_clusters"] = remove_duplicated_dict(info["related_clusters"], key="id")
                info["related_pair_instances"] = remove_duplicated_dict(
                    info["related_pair_instances"], key="bk_instance_id"
                )

        # 查询关联的实例信息
        if query.get("instances"):
            q_filters = [
                Q(bk_biz_id=self.bk_biz_id, machine__ip=inst.split(":")[0], port=inst.split(":")[1])
                for inst in query["instances"]
            ]
            insts = StorageInstance.objects.filter(reduce(operator.or_, q_filters)).values_list("id", flat=True)
            filters = Q(ejector__in=insts) | Q(receiver__in=insts)
            get_machine_instance_pair_info(filters, add_pair_instance_info, "instances")

        # 查询关联的机器信息
        if query.get("machines"):
            q_filters = [
                Q(bk_biz_id=self.bk_biz_id, bk_cloud_id=machine.split(":")[0], ip=machine.split(":")[1])
                for machine in query["machines"]
            ]
            machines = Machine.objects.filter(reduce(operator.or_, q_filters)).values_list("bk_host_id", flat=True)
            filters = Q(ejector__machine__in=machines) | Q(receiver__machine__in=machines)
            get_machine_instance_pair_info(filters, add_pair_machine_info, "machines")

        return related_pairs

    def query_master_slave_pairs(self, cluster_id: int) -> list:
        """
        查询主从架构集群的关系对，适用于一主一从关系
        @param cluster_id: 集群ID
        """
        try:
            cluster = Cluster.objects.get(pk=cluster_id, bk_biz_id=self.bk_biz_id)
        except Cluster.DoesNotExist:
            return []

        # 获取该集群关联的实例对
        pairs = StorageInstanceTuple.objects.select_related("ejector__machine", "receiver__machine").filter(
            receiver__cluster=cluster, ejector__cluster=cluster
        )
        master_slave_pair_infos = [
            {
                "masters": pair.ejector.simple_desc,
                "slaves": pair.receiver.simple_desc,
            }
            for pair in pairs
        ]
        # 兼容原来redis协议
        for info in master_slave_pair_infos:
            info.update(master_ip=info["masters"]["ip"], slave_ip=info["slaves"]["ip"])
        return master_slave_pair_infos

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

    def find_related_clusters_by_instances(
        self, instances: List[DBInstance], same_role: bool = False
    ) -> List[Dict[str, Any]]:
        """
        @param instances: 查询实例
        @param same_role: 是否需要同级同实例
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
        inst_cluster_map: Dict[str, Dict] = {}
        host_id_related_cluster: Dict[int, List] = defaultdict(list)
        same_role_host_related_cluster: Dict[Dict[int, List]] = defaultdict(lambda: defaultdict(list))

        # 基于 存储实例 和 Proxy 不会混部 的原则
        instance_objs = self._get_instance_objs(instances)
        for inst_obj in instance_objs:
            inst_data = DBInstance.from_inst_obj(inst_obj).__str__()
            cluster = inst_obj.cluster.first()
            inst_cluster_map[inst_data] = model_to_dict(cluster)
            host_id_related_cluster[inst_obj.machine.bk_host_id].append(cluster)
            same_role_host_related_cluster[inst_obj.machine.bk_host_id][inst_obj.role].append(cluster)

        # 获取关联集群信息
        related_cluster_infos: List[Dict] = []
        for inst in instance_objs:
            if not same_role:
                clusters = host_id_related_cluster[inst.machine.bk_host_id]
            else:
                clusters = same_role_host_related_cluster[inst.machine.bk_host_id][inst.role]

            inst_data = DBInstance.from_inst_obj(inst).__str__()
            related_clusters = [
                self._format_cluster_field(model_to_dict(cluster))
                for cluster in clusters
                if cluster.id != inst_cluster_map[inst_data]["id"]
            ]

            info = {
                "instance_address": f"{inst.machine.ip}:{inst.port}",
                "bk_host_id": inst.machine.bk_host_id,
                "cluster_info": self._format_cluster_field(inst_cluster_map[inst_data]),
                "related_clusters": related_clusters,
            }

            related_cluster_infos.append(info)

        return related_cluster_infos

    def get_intersected_machines_from_clusters(self, cluster_ids: List[int], role: str, is_stand_by: bool):
        """
        获取关联集群特定实例角色的交集
        @param cluster_ids: 查询的集群ID列表
        @param role: 角色
        @param is_stand_by: 是否只过滤is_stand_by标志的实例，仅用于slave
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
            if is_stand_by:
                # 如果带有is_stand_by标志，则过滤出可用于切换的slave实例
                instances = instances.filter(is_stand_by=True, status=InstanceStatus.RUNNING)

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
        cluster_info["cluster_name"] = cluster_info["name"]
        cluster_info["master_domain"] = cluster_info["immute_domain"]
        return cluster_info

    def _get_instance_objs(self, instances: List[DBInstance]):
        """
        根据instance(属DBInstance类)查询数据库实例，注意这里要考虑混布的情况(在各自组件继承实现)
        eg: Tendbcluster的中控节点和spider master节点就是混布
        """
        bk_host_ids = [instance.bk_host_id for instance in instances]
        # 获得基本的instance_objs
        instance_objs = [
            *list(
                StorageInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id__in=bk_host_ids)
                .annotate(role=F("instance_role"))
            ),
            *list(
                ProxyInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id__in=bk_host_ids)
                .annotate(role=F("access_layer"))
            ),
        ]
        return instance_objs


def get_cluster_service_handler(bk_biz_id: int, db_type: str = "dbbase"):
    """根据集群类型获取对应的集群查询handler"""
    handler_import_path = f"backend.db_services.{db_type}.cluster.handlers"
    try:
        handler_class = getattr(importlib.import_module(handler_import_path), "ClusterServiceHandler")
        handler = handler_class(bk_biz_id)
    except (ModuleNotFoundError, AttributeError):
        handler = ClusterServiceHandler(bk_biz_id)

    return handler
