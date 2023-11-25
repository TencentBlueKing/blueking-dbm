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

from backend import env
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.ticket.constants import FlowTypeConfig, TicketType
from backend.ticket.models import Ticket, TicketFlowConfig
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

    @classmethod
    def fast_create_cloud_component_method(cls, bk_biz_id, bk_cloud_id, ips, user="admin"):
        def _get_base_info(host):
            return {
                "bk_host_id": host["host_id"],
                "ip": host["ip"],
                "bk_cloud_id": host["cloud_id"],
            }

        # 查询的机器的信息
        host_list = [{"cloud_id": bk_cloud_id, "ip": ip} for ip in ips]
        host_infos = HostHandler.details(scope_list=[{"bk_biz_id": bk_biz_id}], host_list=host_list)

        # 构造nginx部署信息
        nginx_host_infos = [
            {
                "bk_outer_ip": host_infos[1].get("bk_host_outerip") or host_infos[1]["ip"],
                **_get_base_info(host_infos[1]),
            }
        ]
        # 构造dns的部署信息
        dns_host_infos = [{**_get_base_info(host_infos[0])}, {**_get_base_info(host_infos[1])}]
        # 构造drs的部署信息
        drs_host_infos = [
            {**_get_base_info(host_infos[0]), "drs_port": env.DRS_PORT},
            {**_get_base_info(host_infos[1]), "drs_port": env.DRS_PORT},
        ]
        # 构造agent的部署信息
        agent_host_infos = [
            {
                **_get_base_info(host_infos[0]),
                "bk_city_code": host_infos[0].get("bk_idc_id") or 0,
                "bk_city_name": host_infos[0].get("bk_idc_name", ""),
            }
        ]
        # 构造gm的部署信息
        gm_host_infos = [
            agent_host_infos[0],  # 允许将一个gm和agent部署在同一台机器
            {
                **_get_base_info(host_infos[1]),
                "bk_city_code": host_infos[1].get("bk_idc_id") or 1,
                "bk_city_name": host_infos[1].get("bk_idc_name", ""),
            },
        ]

        # 创建单据进行部署
        details = {
            "bk_cloud_id": bk_cloud_id,
            "dns": {"host_infos": dns_host_infos},
            "nginx": {"host_infos": nginx_host_infos},
            "drs": {"host_infos": drs_host_infos},
            "dbha": {"gm": gm_host_infos, "agent": agent_host_infos},
        }
        Ticket.create_ticket(
            ticket_type=TicketType.CLOUD_SERVICE_APPLY,
            creator=user,
            bk_biz_id=bk_biz_id,
            remark=_("云区域组件快速部署单据"),
            details=details,
        )

    @classmethod
    def ticket_flow_config_init(cls):
        """初始化单据配置"""
        from backend.ticket.builders import BuilderFactory

        exist_ticket_types = list(TicketFlowConfig.objects.all().values_list("ticket_type", flat=True))
        created_configs = [
            TicketFlowConfig(
                creator="admin",
                updater="admin",
                ticket_type=ticket_type,
                group=flow_class.group,
                editable=flow_class.editable,
                configs={
                    FlowTypeConfig.NEED_MANUAL_CONFIRM: flow_class.default_need_manual_confirm,
                    FlowTypeConfig.NEED_ITSM: flow_class.default_need_itsm,
                },
            )
            for ticket_type, flow_class in BuilderFactory.registry.items()
            if ticket_type not in exist_ticket_types
        ]
        TicketFlowConfig.objects.bulk_create(created_configs)
