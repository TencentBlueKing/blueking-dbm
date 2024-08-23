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
from dataclasses import asdict
from typing import Any, Dict, List, Union

from django.db.models import F, Q
from django.db.models.functions import Coalesce

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.instance_role import ADMIN_ROLE_CASE
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.db_services.dbbase.cluster.handlers import get_cluster_service_handler
from backend.db_services.dbbase.dataclass import DBInstance
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper


class InstanceHandler:
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    def check_instances(
        self, query_instances: List[Union[str, Dict]], cluster_ids: List[int] = None, db_type: str = None
    ) -> List[dict]:
        """
        查询实例的详细信息(包括实例本身信息+主机信息+关联集群信息)
        @param query_instances: ["0:127.0.0.1:10000", "127.0.0.1", "127.0.0.1:20000"]或者[{....}, [....}]
        @param cluster_ids: 实例所属的集群ID
        @param db_type: 组件类型
        :return
        """

        if not query_instances:
            return []

        # 如果传来的inst是字典类型，默认它是已经查询出的实例，只需补充信息
        # 否则需要先查询实例，再补充相关信息
        if isinstance(query_instances[0], Dict):
            storages_proxies_instances = query_instances
        else:
            query_filter = Q()
            for address in query_instances:
                spilt_addr = address.split(IP_PORT_DIVIDER)
                # 兼容ip, ip:port和cloud:ip:port三种格式
                if len(spilt_addr) == 1:
                    query_filter |= Q(machine__ip=spilt_addr[0])
                elif len(spilt_addr) == 2:
                    query_filter |= Q(machine__ip=spilt_addr[0], inst_port=spilt_addr[1])
                else:
                    query_filter |= Q(
                        cluster__bk_cloud_id=spilt_addr[0], machine__ip=spilt_addr[1], inst_port=spilt_addr[2]
                    )

            query_filter &= Q(bk_biz_id=self.bk_biz_id)
            if cluster_ids:
                query_filter &= Q(cluster__id__in=cluster_ids)

            # 由于不知道输入的是什么实例，因此把存储实例和 proxy 实例同时查询出来
            storages = (
                StorageInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .annotate(role=F("instance_inner_role"), inst_port=F("port"))
                .filter(query_filter)
            )
            proxies = (
                # 优先以spider角色为准
                ProxyInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .annotate(
                    role=Coalesce(F("tendbclusterspiderext__spider_role"), F("access_layer")), inst_port=F("port")
                )
                .filter(query_filter)
            )
            admin_proxies = (
                ProxyInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .annotate(role=ADMIN_ROLE_CASE, inst_port=F("admin_port"))
                .filter(query_filter)
                .exclude(role=None)
            )

            storages_proxies_instances = [*storages, *proxies, *admin_proxies]

            # 如果无法查询实例，则直接返回
            if not storages_proxies_instances:
                return []
            # 把inst_port替换成port
            for inst in storages_proxies_instances:
                inst.port = inst.inst_port

        bk_host_ids: List[int] = []
        db_instances: List[DBInstance] = []
        host_id_instance_map: Dict[str, Dict] = {}

        # 应该根据dbtype来选择handler更合理，如果没传dbtype则从实例中查询
        if not db_type:
            inst = storages_proxies_instances[0]
            cluster_type = inst["cluster_type"] if isinstance(inst, Dict) else inst.cluster_type
            db_type = ClusterType.cluster_type_to_db_type(cluster_type)
        cluster_handler = get_cluster_service_handler(self.bk_biz_id, db_type)

        # 查询实例关联的集群信息
        instance_related_clusters: List[Dict[str, Any]] = cluster_handler.find_related_clusters_by_instances(
            instances=[DBInstance.from_inst_obj(inst) for inst in storages_proxies_instances]
        )
        inst_address__related_clusters_map: Dict[str, Dict[str, Any]] = {
            info["instance_address"]: info for info in instance_related_clusters
        }

        # 补充实例的基本信息，关联集群信息和主机信息
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        for inst in storages_proxies_instances:
            db_inst = DBInstance.from_inst_obj(inst)
            db_inst_address = f"{db_inst.ip}:{db_inst.port}"
            db_inst_related_cluster = inst_address__related_clusters_map[db_inst_address]
            host_id_instance_map[str(db_inst)] = {
                **asdict(db_inst),
                "bk_cloud_name": cloud_info[str(db_inst.bk_cloud_id)]["bk_cloud_name"],
                "instance_address": f"{db_inst.ip}{IP_PORT_DIVIDER}{db_inst.port}",
                "cluster_id": db_inst_related_cluster["cluster_info"]["id"],
                "cluster_name": db_inst_related_cluster["cluster_info"]["cluster_name"],
                "master_domain": db_inst_related_cluster["cluster_info"]["master_domain"],
                "cluster_type": db_inst_related_cluster["cluster_info"]["cluster_type"],
                "db_module_id": db_inst_related_cluster["cluster_info"]["db_module_id"],
                # 实例的关联集群把本身集群和集群的关联集群合并到一起
                "related_clusters": [
                    *db_inst_related_cluster["related_clusters"],
                    db_inst_related_cluster["cluster_info"],
                ],
                # 目前的设计，instance_role 才能更好区分不通集群类型中机器的角色
                "create_at": inst["create_at"] if isinstance(inst, Dict) else inst.create_at,
                "role": inst["role"] if isinstance(inst, Dict) else inst.role,
                "status": inst["status"] if isinstance(inst, Dict) else inst.status,
            }
            bk_host_ids.append(inst["bk_host_id"] if isinstance(inst, Dict) else inst.machine.bk_host_id)
            db_instances.append(db_inst)

        # 查询补充主机信息
        host_infos = HostHandler.check(scope_list=[], ip_list=[], ipv6_list=[], key_list=bk_host_ids)
        host_id_info_map = {host_info["host_id"]: host_info for host_info in host_infos}
        instance_infos = [
            {**host_id_instance_map[str(db_inst)], **{"host_info": host_id_info_map.get(db_inst.bk_host_id, {})}}
            for db_inst in db_instances
        ]
        return instance_infos

    def get_machine_by_instances(self, query_instances: List[str]) -> Dict[str, Machine]:
        """根据ip:port查询实例的机器信息"""

        storage_instances = StorageInstance.find_insts_by_addresses(query_instances).filter(bk_biz_id=self.bk_biz_id)
        proxy_instances = ProxyInstance.find_insts_by_addresses(query_instances).filter(bk_biz_id=self.bk_biz_id)

        address__machine_map: Dict[str, Machine] = {}
        for instances in [storage_instances, proxy_instances]:
            address__machine_map.update({inst.ip_port: inst.machine for inst in instances})

        return address__machine_map
