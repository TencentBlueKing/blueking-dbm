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
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.db_meta.models import Cluster, StorageInstance
from backend.ticket.models import Ticket
from backend.utils.basic import get_target_items_from_details


class TicketHandler:
    @classmethod
    def add_related_object(cls, ticket_data: List[Dict]) -> List[Dict]:
        """
        补充单据的关联对象
        - 针对集群操作，则补充集群域名
        - 针对实例操作，则补充集群 IP:PORT
        - ...
        """
        ticket_ids = [ticket["id"] for ticket in ticket_data]
        # 这批单据所操作的集群列表
        cluster_ids = []
        # 这批单据所操作的实例列表
        instance_ids = []
        # 单据关联对象映射表
        ticket_id_obj_ids_map: Dict[int, Dict[str, List[int]]] = {}

        # 查询单据对应的集群列表、实例列表等
        for ticket in Ticket.objects.filter(id__in=ticket_ids):
            _cluster_ids = get_target_items_from_details(ticket.details, match_keys=["cluster_id", "cluster_ids"])
            _instance_ids = get_target_items_from_details(ticket.details, match_keys=["instance_id", "instance_ids"])
            cluster_ids.extend(_cluster_ids)
            instance_ids.extend(_instance_ids)
            ticket_id_obj_ids_map[ticket.id] = {"cluster_ids": _cluster_ids, "instance_ids": _instance_ids}
        cluster_id_immute_domain_map = Cluster.get_cluster_id_immute_domain_map(cluster_ids)
        instance_id_ip_port_map = StorageInstance.get_instance_id_ip_port_map(instance_ids)

        # 补充关联对象信息
        for item in ticket_data:
            ticket_cluster_ids = ticket_id_obj_ids_map[item["id"]]["cluster_ids"]
            if ticket_cluster_ids:
                item["related_object"] = {
                    "title": _("集群"),
                    "objects": [
                        cluster_id_immute_domain_map.get(cluster_id)
                        for cluster_id in ticket_cluster_ids
                        if cluster_id_immute_domain_map.get(cluster_id)
                    ],
                }

            ticket_instance_ids = ticket_id_obj_ids_map[item["id"]]["instance_ids"]
            if ticket_instance_ids:
                item["related_object"] = {
                    "title": _("实例"),
                    "objects": [
                        instance_id_ip_port_map.get(instance_id)
                        for instance_id in ticket_instance_ids
                        if instance_id_ip_port_map.get(instance_id)
                    ],
                }
        return ticket_data
