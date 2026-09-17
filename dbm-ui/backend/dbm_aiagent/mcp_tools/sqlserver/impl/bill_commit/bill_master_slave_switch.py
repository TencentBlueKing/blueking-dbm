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
from typing import List

from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Machine, StorageInstance, StorageInstanceTuple
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.helper import (
    check_master_clusters_consistency,
    validate_sqlserver_ha_clusters,
)
from backend.ticket.builders.sqlserver.sqlserver_master_slave_switch import SQLServerMasterSlaveSwitchDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_sqlserver_master_slave_switch(username: str, cluster_domains: List[str], ips: List[str]):
    """创建 SQLServer 主从互切单据，ips 仅支持单个 master ip。"""
    if len(ips) != 1:
        raise DBMMcpBaseException(msg=_("期望恰好 1 个 master ip, 实际: {}").format(ips))

    ip = ips[0]
    cluster_objs, bk_biz_id, bk_cloud_id = validate_sqlserver_ha_clusters(cluster_domains)

    master_objs = StorageInstance.objects.filter(
        machine__ip=ip, machine__bk_cloud_id=bk_cloud_id, instance_inner_role=InstanceInnerRole.MASTER.value
    )
    check_master_clusters_consistency(cluster_objs, ip, master_objs)

    slave_ips = set()
    for ele in StorageInstanceTuple.objects.filter(ejector__in=master_objs):
        slave_ips.add(ele.receiver.machine.ip)

    if len(slave_ips) != 1:
        raise DBMMcpBaseException(msg=_("master {} 应只有一个 slave ip, 实际: {}").format(ip, sorted(slave_ips)))

    master_machine = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=ip)
    slave_machine = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=list(slave_ips)[0])

    ticket_param = {
        "ticket_type": TicketType.SQLSERVER_MASTER_SLAVE_SWITCH,
        "remark": TicketType.SQLSERVER_MASTER_SLAVE_SWITCH,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "infos": [
                {
                    "master": {
                        "ip": master_machine.ip,
                        "bk_cloud_id": bk_cloud_id,
                        "bk_host_id": master_machine.bk_host_id,
                    },
                    "slave": {
                        "ip": slave_machine.ip,
                        "bk_cloud_id": bk_cloud_id,
                        "bk_host_id": slave_machine.bk_host_id,
                    },
                    "cluster_ids": list(cluster_objs.values_list("pk", flat=True)),
                }
            ]
        },
    }

    slz = SQLServerMasterSlaveSwitchDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.SQLSERVER_MASTER_SLAVE_SWITCH
    slz.context["bk_biz_id"] = bk_biz_id
    slz.is_valid(raise_exception=True)

    def _fingerprint(infos):
        return tuple(
            sorted(
                (
                    tuple(sorted(info["cluster_ids"])),
                    info["master"]["ip"],
                    info["slave"]["ip"],
                )
                for info in infos
            )
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.SQLSERVER_MASTER_SLAVE_SWITCH,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(ticket_param["details"]["infos"]),
        fingerprint_of=lambda tk: _fingerprint(tk.details.get("infos", [])),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
