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

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import Ticket


class DumperHandler:
    @classmethod
    def patch_dumper_list_info(cls, dumper_results: List[Dict], bk_biz_id: int = 0, need_status: bool = False):
        """
        补充获取dumper的实例信息
        @param dumper_results: dumper集群信息(ExtraProcessInstance模型信息)
        @param bk_biz_id: 与need_status一起用，过业务单据
        @param need_status: 是否需要dumper正在迁移的信息
        """

        if not dumper_results:
            return

        # 查询集群相关信息
        cluster_ids = [data["cluster_id"] for data in dumper_results]
        id__cluster = {
            cluster.id: cluster
            for cluster in Cluster.objects.prefetch_related("storageinstance_set").filter(id__in=cluster_ids)
        }

        # 补充订阅实例的信息
        for data in dumper_results:
            extra_config = data.pop("extra_config")
            # 补充订阅集群相关信息
            if data["cluster_id"] in id__cluster:
                # dumper是否已经不在集群master主机上 ---> 需要迁移
                source_cluster = id__cluster[data["cluster_id"]]
                master = source_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
                data["need_transfer"] = data["ip"] != master.machine.ip
                # 补充集群信息和集群的master信息
                data["source_cluster"] = source_cluster.simple_desc
                data["source_cluster"]["master_ip"] = master.machine.ip
                data["source_cluster"]["master_port"] = master.port
            # 补充订阅配置信息
            dumper_config_fields = ["dumper_id", "protocol_type", "target_address", "target_port", "add_type"]
            for field in dumper_config_fields:
                data[field] = extra_config.get(field)

        # 无需补充实例状态信息就提前退出
        if not need_status:
            return

        # 查询dumper实例的状态(效率考虑，仅支持查单个业务下的), 因为dumper实例没有record表，因此直接查询正在运行的相关单据
        dumper_ticket_types = TicketType.get_ticket_type_by_db("tbinlogdumper")
        dumper_ticket_types.remove(TicketType.TBINLOGDUMPER_INSTALL)
        dumper_ticket_types.extend([TicketType.MYSQL_MASTER_SLAVE_SWITCH, TicketType.MYSQL_MASTER_FAIL_OVER])
        active_tickets = Ticket.objects.filter(
            bk_biz_id=bk_biz_id, status=TicketStatus.RUNNING, ticket_type__in=dumper_ticket_types
        )
        # 获取每个dumper单据状态与id的映射
        dumper_inst_id__ticket: Dict[int, str] = {}
        for ticket_type in dumper_ticket_types:
            ticket_infos = active_tickets.filter(ticket_type=ticket_type).values_list(
                "details__dumper_instance_ids", "id"
            )
            for ticket_info in ticket_infos:
                info = list(ticket_info)
                # 如果变更类dumper单据没有dumper_instance_ids，则认为空列表
                info[0] = info[0] or []
                dumper_inst_id__ticket.update({d: (ticket_type, info[1]) for d in info[0]})

        # 对每个dumper实例填充正在运行的状态，一个dumper只会处于一种变更状态
        for data in dumper_results:
            if data["id"] not in dumper_inst_id__ticket:
                data["operation"] = {}
            else:
                data["operation"] = {
                    "ticket_type": dumper_inst_id__ticket[data["id"]][0],
                    "ticket_id": dumper_inst_id__ticket[data["id"]][1],
                }
