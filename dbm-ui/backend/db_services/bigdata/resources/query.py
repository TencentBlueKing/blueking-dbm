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
from typing import Any, Dict, List

from django.db.models import Count, F
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.instance import StorageInstance
from backend.db_proxy.models import ClusterExtension
from backend.db_services.dbbase.resources import query
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.ticket.constants import TicketFlowStatus, TicketType
from backend.ticket.models import InstanceOperateRecord
from backend.utils.time import datetime2str


class BigDataBaseListRetrieveResource(query.ListRetrieveResource):
    """
    大数据相关组件资详情基类
    es/kafka/hdfs 分别继承实现各自的资源详情类
    """

    cluster_types = []
    instance_roles = []
    fields = [
        {"name": _("集群名"), "key": "cluster_name"},
        {"name": _("集群别名"), "key": "cluster_alias"},
        {"name": _("集群类型"), "key": "cluster_type"},
        {"name": _("集群类型名"), "key": "cluster_type_name"},
        {"name": _("域名"), "key": "domain"},
        {"name": _("版本"), "key": "major_version"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建时间"), "key": "create_at"},
        {"name": _("更新人"), "key": "updater"},
        {"name": _("更新时间"), "key": "update_at"},
    ]

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        raise NotImplementedError()

    @classmethod
    def _filter_instance_hook(cls, bk_biz_id, query_params, instances, **kwargs):
        instance_ids = [instance["id"] for instance in instances]

        # 获取实例的重启操作的映射
        restart_records = InstanceOperateRecord.objects.filter(
            instance_id__in=instance_ids,
            ticket__ticket_type__in=[
                TicketType.ES_REBOOT,
                TicketType.HDFS_REBOOT,
                TicketType.KAFKA_REBOOT,
                TicketType.PULSAR_REBOOT,
            ],
        ).order_by("create_at")
        restart_map = {record.instance_id: record.create_at for record in restart_records}

        # 获取实例的操作与实例记录
        records = InstanceOperateRecord.objects.filter(
            instance_id__in=instance_ids, ticket__status=TicketFlowStatus.RUNNING
        )
        instance_operate_records_map: Dict[int, List] = defaultdict(list)
        for record in records:
            instance_operate_records_map[int(record.instance_id)].append(record.summary)

        return super()._filter_instance_hook(
            bk_biz_id,
            query_params,
            instances,
            restart_map=restart_map,
            instance_operate_records_map=instance_operate_records_map,
            **kwargs,
        )

    @classmethod
    def _to_cluster_representation(
        cls,
        cluster: Cluster,
        db_module_names_map: Dict[int, str],
        cluster_entry_map: Dict[int, Dict[str, str]],
        cluster_operate_records_map: Dict[int, List],
        **kwargs,
    ) -> Dict[str, Any]:
        """集群序列化"""

        # 获取集群基本信息
        cluster_info = super()._to_cluster_representation(
            cluster, db_module_names_map, cluster_entry_map, cluster_operate_records_map, **kwargs
        )
        cluster_info["domain"] = cluster_info["master_domain"]

        # 获取集群访问url
        cluster_info.update(access_url=ClusterExtension.get_cluster_service_url(cluster))

        # 获取集群角色信息
        for role in cls.instance_roles:
            inst_role_infos = [inst.simple_desc for inst in cluster.storages if inst.instance_role == role]
            cluster_info.update({role: inst_role_infos})

        return cluster_info

    @classmethod
    def _to_instance_representation(cls, instance: dict, cluster_entry_map: dict, **kwargs) -> Dict[str, Any]:
        """实例序列化"""
        instance_info = super()._to_instance_representation(instance, cluster_entry_map, **kwargs)
        # 补充重启时间和操作记录
        restart_at = kwargs["restart_map"].get(instance["id"])
        instance_info.update(
            restart_at=datetime2str(restart_at) if restart_at else "",
            operations=kwargs["instance_operate_records_map"].get(instance["id"], []),
        )
        return instance_info

    @classmethod
    def list_nodes(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        cluster_id = query_params["cluster_id"]
        fields = ["machine__ip", "machine__bk_host_id", "machine__bk_cloud_id", "node_count", "role", "create_at"]

        # 聚合实例角色和ip，统计同一ip下同一角色的数量
        # 注意这里一定要用order by覆盖meta中的order by，否则会导致聚合错误
        storage_queryset = (
            StorageInstance.objects.filter(cluster__id=cluster_id, bk_biz_id=bk_biz_id)
            .values("instance_role", "machine__ip")
            .annotate(node_count=Count("id"), role=F("instance_role"))
            .values(*fields)
            .order_by("node_count")
        )

        node_list = list(storage_queryset)
        return cls._to_nodes_list(bk_biz_id=bk_biz_id, node_list=node_list, limit=limit, offset=offset)

    @classmethod
    def get_nodes(cls, bk_biz_id: int, cluster_id: int, role: str, keyword: str = None) -> list:
        # 由子类来具体实现node节点的筛选逻辑
        raise NotImplementedError()

    @classmethod
    def _to_nodes_list(
        cls, bk_biz_id: int, node_list: List[Dict[str, Any]], limit: int, offset: int
    ) -> query.ResourceList:
        """节点列表序列化"""

        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        host_id__node_list_map = {node["machine__bk_host_id"]: node for node in node_list}
        host_info_map = ResourceQueryHelper.search_cc_hosts(
            env.DBA_APP_BK_BIZ_ID, list(host_id__node_list_map.keys()), keyword=None
        )
        host_id__host_info_map = {host_info["bk_host_id"]: host_info for host_info in host_info_map}
        for host_id, node in host_id__node_list_map.items():
            node["bk_host_id"] = node.pop("machine__bk_host_id")
            node["bk_cloud_id"] = node.pop("machine__bk_cloud_id")
            node["bk_cloud_name"] = cloud_info[str(node["bk_cloud_id"])]["bk_cloud_name"]
            node["ip"] = node.pop("machine__ip")

            # 更新主机cc信息
            host_info = host_id__host_info_map.get(host_id)
            if host_info:
                node.update(
                    {
                        # TODO: 磁盘使用率信息暂时没有
                        "status": host_info.get("status"),
                        "cpu": host_info.get("bk_cpu"),
                        "mem": host_info.get("bk_mem"),
                        "disk": host_info.get("bk_disk"),
                        "machine_type": host_info.get("machine_type"),
                        "bk_host_name": host_info.get("bk_host_name"),
                    }
                )

        group_list = list(host_id__node_list_map.values())
        count = len(group_list)
        paginated_group_list = group_list if limit == -1 else group_list[offset : limit + offset]
        # 按照角色进行排序
        paginated_group_list.sort(key=lambda x: x.get("role") or x.get("role_set"))

        return query.ResourceList(count=count, data=paginated_group_list)
