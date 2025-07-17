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
from typing import Any, Callable, Dict, List, Set

from django.db.models import F, Prefetch, Q
from django.utils.translation import ugettext_lazy as _
from rest_framework.response import Response

from backend.components import DRSApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException, InstanceNotExistException
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_meta.models.machine import Machine
from backend.db_services.dbbase.dataclass import DBInstance
from backend.db_services.mysql.sql_import.constants import SQLCharset
from backend.db_services.mysql.sqlparse.handlers import SQLParseHandler
from backend.utils.basic import remove_duplicated_dict
from backend.utils.time import get_local_charset


class ClusterServiceHandler:
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    def check_cluster_databases(self, cluster_id: int, db_list: List[int], user_id: int = 0) -> Dict:
        """
        校验集群的库名是否存在，支持各个类型的集群
        注意：这个方法是通用查询库表是否存在，子类需要单独实现check_cluster_database,而不是覆写该方法
        @param cluster_id: 集群ID
        @param db_list: 库名列表
        @param user_id: 用户ID 访问mongodb rpc专用
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

        if cluster.cluster_type in [ClusterType.MongoReplicaSet, ClusterType.MongoShardedCluster]:
            from backend.db_services.mongodb.cluster.handlers import ClusterServiceHandler as MongoDB

            return MongoDB(self.bk_biz_id).check_cluster_database(cluster_id, db_list, user_id)
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
        self, cluster_ids: List[int], role: str = InstanceInnerRole.MASTER
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
        storages = StorageInstance.objects.select_related("machine").filter(
            cluster__id__in=cluster_ids, instance_inner_role=role
        )
        proxies = ProxyInstance.objects.select_related("machine").filter(
            cluster__id__in=cluster_ids, access_layer=role
        )
        instances = list(storages) + list(proxies)

        if not instances:
            raise InstanceNotExistException(_("无法找到集群{}所包含实例，请检查集群相关信息").format(cluster_ids))

        # 获取实例的关联集群信息
        related_clusters = self.find_related_clusters_by_instances(
            [DBInstance.from_inst_obj(inst) for inst in instances]
        )

        # 聚合集群的关联集群信息
        cluster_id__info_map = {}
        cluster_id__related_clusters_map = defaultdict(list)
        for info in related_clusters:
            cluster_id__info_map[info["cluster_info"]["id"]] = info["cluster_info"]
            cluster_id__related_clusters_map[info["cluster_info"]["id"]].extend(info["related_clusters"])

        cluster_related_infos: List[Dict[str, Any]] = []
        for cluster_id in cluster_ids:
            # 对关联集群去重
            related_clusters = cluster_id__related_clusters_map[cluster_id]
            related_clusters = list({c["id"]: c for c in related_clusters}.values())
            cluster_related_infos.append(
                {
                    "cluster_id": cluster_id,
                    "cluster_info": cluster_id__info_map[cluster_id],
                    "related_clusters": related_clusters,
                }
            )
        return cluster_related_infos

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
            inst_cluster_map[inst_data] = cluster.to_dict()
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
                self._format_cluster_field(cluster.to_dict())
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

    @staticmethod
    def console_rpc(
        instances: list, cmd: str, db_query: bool, rpc_function: Callable, is_check: bool = True, **kwargs
    ):
        """
        通用的RPC命令执行器，只支持select语句
        @param instances: 实例信息
        @param cmd: 执行命令
        @param db_query: 是否只允许查询系统库 -- DB自助查询
        @param rpc_function: 用于执行RPC请求的函数
        @param is_check: 校验select语句
        """
        # 校验select语句
        if is_check:
            SQLParseHandler().parse_select_statement(sql=cmd, db_query=db_query)

        # 按云区域对instance分组
        bk_cloud__instances_map: Dict[int, List] = defaultdict(list)
        for info in instances:
            bk_cloud__instances_map[info["bk_cloud_id"]].append(info["instance"])

        # 获取rpc结果
        instance_rpc_results: List = []

        if ClusterServiceHandler.__check_special_sql(cmd):
            instance_rpc_results = ClusterServiceHandler.__dbconsole_special_query(
                bk_cloud__instances_map, cmd, **kwargs
            )
        else:
            for bk_cloud_id, addresses in bk_cloud__instances_map.items():
                params = {
                    "bk_cloud_id": bk_cloud_id,
                    "addresses": addresses,
                    "cmds": [cmd],
                    "charset": kwargs.get("options", {}).get("charset", SQLCharset.DEFAULT.value),
                    "timezone": kwargs.get("options", {}).get("timezone", get_local_charset()),
                }
                # 使用传入的rpc_function进行rpc调用
                rpc_results = rpc_function(params)

                cmd_results = [
                    {
                        "instance": res["address"],
                        "table_data": res["cmd_results"][0]["table_data"] if not res["error_msg"] else None,
                        "error_msg": res["error_msg"],
                    }
                    for res in rpc_results
                ]
                instance_rpc_results.extend(cmd_results)

        return instance_rpc_results

    @classmethod
    def __dbconsole_special_query(cls, bk_cloud__instances_map, cmd, **kwargs):
        """
        用于dbaconsole的特殊查询，目前复用webconsole，因此不支持单次多条查询
        webconsole账户也不支持查询主从同步信息
        当前这个函数主要用于处理：
        1. mysql配置信息查询（多条查询合并）
        2. mysql主从同步信息查询

        @param bk_cloud__instances_map:
        @param cmd:
        @return:
        """
        special_sql = {
            "show mysql configurations": [
                "show variables like 'version';",
                "show variables like 'character_set_server';",
                "show variables like 'character_set_database';",
                "show variables like 'max_connections';",
                "show variables like 'spider_max_connections';",
                "show variables like 'log_bin';",
                "show variables like 'binlog_format';",
                "show variables like 'long_query_time';",
                "show variables like 'lower_case_table_names';",
                "show variables like 'slave_parallel_threads';",
                "show variables like 'innodb_buffer_pool_size';",
                "show variables like 'innodb_data_file_path';",
            ],
            "show slave status": ["show slave status;"],
        }
        standard_cmd = " ".join(cmd.split()).lower()
        cmds = []
        for special in special_sql:
            if standard_cmd.startswith(special):
                cmds = special_sql[special]

        instance_rpc_results: List = []
        for bk_cloud_id, addresses in bk_cloud__instances_map.items():
            params = {
                "bk_cloud_id": bk_cloud_id,
                "addresses": addresses,
                "cmds": cmds,
                "charset": kwargs.get("options", {}).get("charset", SQLCharset.DEFAULT.value),
                "timezone": kwargs.get("options", {}).get("timezone", get_local_charset()),
            }
            rpc_results = DRSApi.rpc(params)
            cmd_results = [
                {
                    "instance": res["address"],
                    "table_data": cls.__merge_drs_result(res, standard_cmd) if not res["error_msg"] else None,
                    "error_msg": res["error_msg"],
                }
                for res in rpc_results
            ]
            instance_rpc_results.extend(cmd_results)

        return instance_rpc_results

    @classmethod
    def __check_special_sql(cls, cmd):
        """
        检查是否是特殊sql查询
        @param cmd:
        @return:
        """
        special_sql = ["show mysql configurations", "show slave status"]

        for special in special_sql:
            if " ".join(cmd.split()).lower().startswith(special):
                return True

        return False

    @classmethod
    def __merge_drs_result(cls, res, cmd):
        """
        用于合并单个实例查询多条sql的结果合并
        指定主从信息
        @param res:
        @return:

        """
        table_data = []
        merge_data = {}
        if cmd.startswith("show mysql configurations"):
            for cmd_result in res["cmd_results"]:
                # 有的子查询没有结果或者报错，一律跳过 只记录有值的
                if not cmd_result["error_msg"] and len(cmd_result["table_data"]) > 0:
                    merge_data.update(
                        {cmd_result["table_data"][0]["Variable_name"]: cmd_result["table_data"][0]["Value"]}
                    )
            table_data.append(merge_data)
        elif cmd.startswith("show slave status"):
            k_list = [
                "Master_Host",
                "Master_Port",
                "Master_User",
                "Slave_IO_State",
                "Slave_IO_Running",
                "Slave_SQL_Running",
                "Seconds_Behind_Master",
                "Connect_Retry",
                "Master_File",
                "Master_Position",
                "Master_Log_File",
                "Read_Master_Log_Pos",
                "Relay_Master_Log_File",
                "Exec_Master_Log_Pos",
                "Replicate_Do_DB",
                "Replicate_Ignore_DB",
                "Last_Errno",
                "Last_Error",
            ]
            td = res["cmd_results"][0]["table_data"]
            merge_data.update({k: td[0][k] for k in k_list if len(td) > 0 and k in td[0]})
            table_data.append(merge_data)
        else:
            for cmd_result in res["cmd_results"]:
                table_data.extend(cmd_result["table_data"] if not cmd_result["error_msg"] else None)

        return table_data


def get_cluster_service_handler(bk_biz_id: int, db_type: str = "dbbase"):
    """根据集群类型获取对应的集群查询handler"""
    if db_type == DBType.TenDBCluster.value:
        db_type = DBType.MySQL.value
    handler_import_path = f"backend.db_services.{db_type}.cluster.handlers"
    try:
        handler_class = getattr(importlib.import_module(handler_import_path), "ClusterServiceHandler")
        handler = handler_class(bk_biz_id)
    except (ModuleNotFoundError, AttributeError):
        handler = ClusterServiceHandler(bk_biz_id)

    return handler


def retrieve_resources(self, request, serializer_class, resource_method_name):
    """
    通用方法来处理不同资源类型的请求。
    """
    from backend.db_services.dbbase.resources import register

    query_params = self.params_validate(serializer_class)
    bk_biz_id = query_params.pop("bk_biz_id", None)
    db_type = query_params.get("db_type")
    cluster_type_param = query_params.get("cluster_type")

    # 检查数据库类型是否为 Redis
    if db_type == DBType.Redis.value:
        # 如果是 Redis，选取任意集群类型获取redis资源类
        RetrieveResource = register.cluster_type__resource_class.get(ClusterType.TendisPredixyRedisCluster.value)
    elif cluster_type_param:
        # 如果提供了集群类型，则进行处理
        cluster_types = cluster_type_param.split(",")
        RetrieveResource = register.cluster_type__resource_class.get(cluster_types[0])
    else:
        return Response({})

    # 动态调用资源方法获取数据
    resource_method = getattr(RetrieveResource, resource_method_name)
    data = self.paginator.paginate_list(request, bk_biz_id, resource_method, query_params)

    return self.get_paginated_response(data)
