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

from typing import Any, Dict

from django.db.models import F, Q, QuerySet, Value
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.api.cluster.tendbcluster.detail import scan_cluster
from backend.db_meta.enums import InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_services.dbbase.resources import query
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.mysql.resources.tendbha.query import ListRetrieveResource as DBHAListRetrieveResource
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
    def list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        return super().list_clusters(bk_biz_id, query_params, limit, offset)

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

    @staticmethod
    def _to_cluster_representation(
        cluster: Cluster, db_module_names: Dict[int, str], cluster_entry_map: Dict[int, Dict[str, str]]
    ) -> Dict[str, Any]:
        """将集群对象转为可序列化的 dict 结构"""
        spider = {
            role: [inst.simple_desc for inst in cluster.proxies if inst.tendbclusterspiderext.spider_role == role]
            for role in TenDBClusterSpiderRole.get_values()
        }
        remote_db = [m.simple_desc for m in cluster.storages if m.instance_inner_role == InstanceInnerRole.MASTER]
        remote_dr = [m.simple_desc for m in cluster.storages if m.instance_inner_role == InstanceInnerRole.SLAVE]

        cluster_entry = cluster_entry_map.get(cluster.id, {})
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)

        return {
            "id": cluster.id,
            "phase": cluster.phase,
            "status": cluster.status,
            "operations": ClusterOperateRecord.objects.get_cluster_operations(cluster.id),
            "cluster_name": cluster.name,
            "cluster_type": cluster.cluster_type,
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
            "remote_db": remote_db,
            "remote_dr": remote_dr,
            "db_module_name": db_module_names.get(cluster.db_module_id, ""),
            "creator": cluster.creator,
            "create_at": datetime2str(cluster.create_at),
        }

    @staticmethod
    def _filter_instance_qs(query_conditions):
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
        ]
        # 获取remote实例的查询集
        remote_insts = StorageInstance.objects.annotate(role=F("instance_role"), inst_port=F("port")).filter(
            query_conditions
        )
        # 获取spider实例的查询集
        spider_insts = ProxyInstance.objects.annotate(
            role=F("tendbclusterspiderext__spider_role"), inst_port=F("port")
        ).filter(query_conditions)
        # 额外获取spider master混部的中控节点的查询集
        controller_insts = ProxyInstance.objects.annotate(
            role=Value("spider_controller"), inst_port=F("admin_port")
        ).filter(query_conditions & Q(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value))

        # ⚠️这里的union不要用链式union(eg: s1.union(s2).union(s3))，否则django解析sql语句会生成额外的扩号导致mysql语法错误。
        instances = remote_insts.union(spider_insts, controller_insts).values(*fields).order_by("-create_at")
        return instances

    @classmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        return super().list_instances(bk_biz_id, query_params, limit, offset)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph
