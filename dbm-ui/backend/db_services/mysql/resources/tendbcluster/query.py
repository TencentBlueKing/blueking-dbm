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

from typing import Any, Dict, List

from django.db.models import F, Q, QuerySet, Value
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.api.cluster.tendbcluster.detail import scan_cluster
from backend.db_meta.enums import InstanceInnerRole, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.comm import SystemTagEnum
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import AppCache, Machine, Spec
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_services.dbbase.resources import query
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.mysql.resources.tendbha.query import ListRetrieveResource as DBHAListRetrieveResource
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord
from backend.utils.time import datetime2str


class ListRetrieveResource(DBHAListRetrieveResource):
    """查看 mysql dbha 架构的资源"""

    cluster_type = ClusterType.TenDBCluster

    fields = [
        {"name": _("集群名"), "key": "cluster_name"},
        {"name": _("主域名"), "key": "master_domain"},
        {"name": _("从域名"), "key": "slave_domain"},
        {"name": "Spider Master", "key": "spider_master"},
        {"name": "Spider Slave", "key": "spider_slave"},
        {"name": "Remote DB", "key": "remote_db"},
        {"name": "Remote DR", "key": "remote_dr"},
        {"name": _("运维节点"), "key": "spider_mnt"},
        {"name": _("所属db模块"), "key": "db_module_name"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建时间"), "key": "create_at"},
    ]

    @classmethod
    def _list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        return super()._list_clusters(bk_biz_id, query_params, limit, offset)

    @classmethod
    def _list(
        cls,
        cluster_qset: QuerySet,
        proxy_inst_qset: QuerySet,
        storage_inst_qset: QuerySet,
        db_module_names: Dict[int, str],
        limit: int,
        offset: int,
    ) -> query.ResourceList:
        return super()._list(cluster_qset, proxy_inst_qset, storage_inst_qset, db_module_names, limit, offset)

    @classmethod
    def _to_cluster_representation(
        cls, cluster: Cluster, db_module_names: Dict[int, str], cluster_entry_map: Dict[int, Dict[str, str]]
    ) -> Dict[str, Any]:
        """将集群对象转为可序列化的 dict 结构"""

        def get_remote_infos(insts: List[StorageInstance]):
            """获取remote信息，并补充分片信息"""
            remote_infos = {InstanceInnerRole.MASTER.value: [], InstanceInnerRole.SLAVE.value: []}
            for inst in insts:
                try:
                    related = "as_ejector" if inst.instance_inner_role == InstanceInnerRole.MASTER else "as_receiver"
                    shard_id = getattr(inst, related).first().tendbclusterstorageset.shard_id
                except Exception:
                    # 如果无法找到shard_id，则默认为-1。有可能实例处于restoring状态(比如集群容量变更时)
                    shard_id = -1

                remote_infos[inst.instance_inner_role].append({**inst.simple_desc, "shard_id": shard_id})

            remote_infos[InstanceInnerRole.MASTER.value].sort(key=lambda x: x.get("shard_id", -1))
            remote_infos[InstanceInnerRole.SLAVE.value].sort(key=lambda x: x.get("shard_id", -1))
            return remote_infos[InstanceInnerRole.MASTER.value], remote_infos[InstanceInnerRole.SLAVE.value]

        spider = {
            role: [inst.simple_desc for inst in cluster.proxies if inst.tendbclusterspiderext.spider_role == role]
            for role in TenDBClusterSpiderRole.get_values()
        }
        remote_db, remote_dr = get_remote_infos(cluster.storages)

        machine_list = list(set([inst["bk_host_id"] for inst in [*remote_db, *remote_dr]]))
        machine_pair_cnt = len(machine_list) / 2

        spec_id = Machine.objects.get(bk_host_id=machine_list[0]).spec_id
        cluster_spec = Spec.objects.get(spec_id=spec_id)
        cluster_entry = cluster_entry_map.get(cluster.id, {})
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)

        return {
            "id": cluster.id,
            "phase": cluster.phase,
            "status": cluster.status,
            "operations": ClusterOperateRecord.objects.get_cluster_operations(cluster.id),
            "cluster_name": cluster.name,
            "cluster_type": cluster.cluster_type,
            "cluster_spec": model_to_dict(cluster_spec),
            "cluster_capacity": cluster_spec.capacity * machine_pair_cnt,
            "major_version": cluster.major_version,
            "region": cluster.region,
            "master_domain": cluster_entry.get("master_domain", ""),
            "slave_domain": cluster_entry.get("slave_domain", ""),
            "bk_biz_id": cluster.bk_biz_id,
            "bk_biz_name": AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).bk_biz_name,
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_cloud_name": cloud_info[str(cluster.bk_cloud_id)]["bk_cloud_name"],
            "spider_master": spider[TenDBClusterSpiderRole.SPIDER_MASTER],
            "spider_slave": spider[TenDBClusterSpiderRole.SPIDER_SLAVE],
            "spider_mnt": spider[TenDBClusterSpiderRole.SPIDER_MNT],
            # TODO: 待补充当前集群使用容量，需要监控采集的支持
            "cluster_shard_num": len(remote_db),
            "remote_shard_num": len(remote_db) / machine_pair_cnt,
            "machine_pair_cnt": machine_pair_cnt,
            "remote_db": remote_db,
            "remote_dr": remote_dr,
            "db_module_id": cluster.db_module_id,
            "db_module_name": db_module_names.get(cluster.db_module_id, ""),
            "creator": cluster.creator,
            "create_at": datetime2str(cluster.create_at),
            "temporary_info": cls._fill_temporary_cluster_info(cluster),
        }

    @staticmethod
    def _fill_temporary_cluster_info(cluster):
        # 如果当前集群是临时集群，则补充临时集群相关信息
        if not cluster.tag_set.filter(name=SystemTagEnum.TEMPORARY.value).exists():
            return {}

        ticket = (
            ClusterOperateRecord.objects.filter(
                cluster_id=cluster.id, ticket__ticket_type=TicketType.TENDBCLUSTER_ROLLBACK_CLUSTER
            )
            .first()
            .ticket
        )
        temporary_info = {
            "source_cluster": Cluster.objects.get(id=ticket.details["cluster_id"]).name,
            "ticket_id": ticket.id,
        }
        return temporary_info

    @classmethod
    def _to_cluster_representation_with_instances(
        cls, cluster: Cluster, db_module_names: Dict[int, str], cluster_entry_map: Dict[int, Dict[str, str]]
    ) -> Dict[str, Any]:
        """添加实例的相关信息"""
        cluster_info = super()._to_cluster_representation_with_instances(cluster, db_module_names, cluster_entry_map)
        # 补充中控节点信息，异常则返回空
        try:
            cluster_info["spider_ctl_primary"] = cluster.tendbcluster_ctl_primary_address()
        except DBMetaException:
            cluster_info["spider_ctl_primary"] = ""
        return cluster_info

    @staticmethod
    def _filter_instance_qs(query_conditions, query_params):
        fields = [
            "id",
            "cluster__id",
            "cluster__major_version",
            "cluster__cluster_type",
            "cluster__db_module_id",
            "cluster__name",
            "role",
            "machine__ip",
            "machine__bk_cloud_id",
            "inst_port",
            "status",
            "create_at",
            "machine__bk_host_id",
            "machine__spec_config",
        ]

        # 获取remote实例的查询集
        remote_insts = StorageInstance.objects.annotate(role=F("instance_role"), inst_port=F("port")).filter(
            query_conditions
        )
        # 获取spider实例的查询集
        spider_insts = ProxyInstance.objects.annotate(
            role=F("tendbclusterspiderext__spider_role"), inst_port=F("port")
        ).filter(query_conditions)

        # 涉及spider_controller的查询
        if query_params.get("spider_ctl"):
            # 额外获取spider master混部的中控节点的查询集 这里有一点: 通过value和annotate来将admin_port覆写port，达到过滤效果
            controller_insts = (
                ProxyInstance.objects.values("admin_port")
                .annotate(port=F("admin_port"))
                .values(role=Value("spider_ctl"), inst_port=F("admin_port"))
                .filter(
                    query_conditions & Q(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value)
                )
            )
            # ⚠️这里的union不要用链式union(eg: s1.union(s2).union(s3))，否则django解析sql语句会生成额外的扩号导致mysql语法错误。
            instances = remote_insts.union(spider_insts, controller_insts).values(*fields).order_by("-create_at")
        else:
            instances = remote_insts.union(spider_insts).values(*fields).order_by("-create_at")

        return instances

    @classmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        return super().list_instances(bk_biz_id, query_params, limit, offset)

    @classmethod
    def retrieve_instance(cls, bk_biz_id: int, cluster_id: int, ip: str, port: int) -> dict:
        instances = cls.list_instances(bk_biz_id, {"ip": ip, "port": port, "spider_ctl": True}, limit=1, offset=0)
        instance = instances.data[0]
        return cls._fill_instance_info(instance, cluster_id)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph
