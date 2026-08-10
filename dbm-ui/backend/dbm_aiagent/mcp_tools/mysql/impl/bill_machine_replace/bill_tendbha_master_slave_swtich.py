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

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Machine, StorageInstance, StorageInstanceTuple
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import (
    check_clusters_consistency,
    validate_clusters,
)
from backend.ticket.builders.mysql.mysql_master_slave_switch import MysqlMasterSlaveSwitchDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_tendbha_master_slave_switch(cluster_domains: List[str], ips: List[str]):
    if not len(ips) == 1:
        raise Exception("expected exactly 1 ip, but found: {}".format(ips))

    ip = ips[0]

    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBHA)

    master_objs = StorageInstance.objects.using(MYSQL_MCP_DB_READ).filter(
        machine__ip=ip, machine__bk_cloud_id=bk_cloud_id, instance_inner_role=InstanceInnerRole.MASTER
    )
    check_clusters_consistency(cluster_objs, ips, master_objs)

    slave_ips = set()
    for ele in StorageInstanceTuple.objects.using(MYSQL_MCP_DB_READ).filter(ejector__in=master_objs):
        slave_ips.add(ele.receiver.machine.ip)

    if not len(slave_ips) == 1:
        raise Exception(
            "masters on {} should have all slaves on a single ip, but found: {}".format(ip, sorted(slave_ips))
        )

    master_machine_obj = Machine.objects.using(MYSQL_MCP_DB_READ).get(bk_cloud_id=bk_cloud_id, ip=ip)
    slave_machine_obj = Machine.objects.using(MYSQL_MCP_DB_READ).get(bk_cloud_id=bk_cloud_id, ip=list(slave_ips)[0])

    dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.MySQL)

    ticket_param = {
        "ticket_type": TicketType.MYSQL_MASTER_SLAVE_SWITCH,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "bk_biz_id": bk_biz_id,
        "remark": TicketType.MYSQL_MASTER_SLAVE_SWITCH,
        "details": {
            "bk_cloud_id": bk_cloud_id,
            "bk_biz_id": bk_biz_id,
            "is_check_process": True,
            "is_check_delay": True,
            "is_verify_checksum": True,
            "infos": [
                {
                    "master_ip": {
                        "ip": master_machine_obj.ip,
                        "bk_biz_id": bk_biz_id,
                        "bk_cloud_id": bk_cloud_id,
                        "bk_host_id": master_machine_obj.bk_host_id,
                    },
                    "slave_ip": {
                        "ip": slave_machine_obj.ip,
                        "bk_biz_id": bk_biz_id,
                        "bk_cloud_id": bk_cloud_id,
                        "bk_host_id": slave_machine_obj.bk_host_id,
                    },
                    "cluster_ids": list(cluster_objs.values_list("pk", flat=True)),
                }
            ],
        },
    }

    slz = MysqlMasterSlaveSwitchDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.MYSQL_MASTER_SLAVE_SWITCH
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
