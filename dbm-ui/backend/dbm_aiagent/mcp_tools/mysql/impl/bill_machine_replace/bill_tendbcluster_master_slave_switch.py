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
from backend.ticket.builders.tendbcluster.tendb_master_slave_switch import TendbMasterSlaveSwitchDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_tendbcluster_master_slave_switch(cluster_domain: str, ips: List[str]):
    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters([cluster_domain], ClusterType.TenDBCluster)

    remote_master_objs = StorageInstance.objects.using(MYSQL_MCP_DB_READ).filter(
        machine__ip__in=ips, machine__bk_cloud_id=bk_cloud_id, instance_inner_role=InstanceInnerRole.MASTER
    )

    check_clusters_consistency(cluster_objs, ips, remote_master_objs)

    slave_ips = set()
    tps = StorageInstanceTuple.objects.using(MYSQL_MCP_DB_READ).filter(ejector__in=remote_master_objs)
    for ele in tps:
        slave_ips.add(ele.receiver.machine.ip)

    if not len(slave_ips) == len(ips):
        raise Exception(
            "expected {} slave ips matching master ips {}, but found: {}".format(
                len(ips), sorted(ips), sorted(slave_ips)
            )
        )

    infos = []
    for ele in tps.values_list("ejector__machine__ip", "receiver__machine__ip").distinct():
        master = Machine.objects.using(MYSQL_MCP_DB_READ).get(bk_cloud_id=bk_cloud_id, ip=ele[0])
        slave = Machine.objects.using(MYSQL_MCP_DB_READ).get(bk_cloud_id=bk_cloud_id, ip=ele[1])
        infos.append(
            {
                "cluster_id": cluster_objs[0].pk,
                "switch_tuples": [
                    {
                        "master": {
                            "ip": master.ip,
                            "bk_cloud_id": bk_cloud_id,
                            "bk_biz_id": bk_biz_id,
                            "bk_host_id": master.bk_host_id,
                        },
                        "slave": {
                            "ip": slave.ip,
                            "bk_cloud_id": bk_cloud_id,
                            "bk_biz_id": bk_biz_id,
                            "bk_host_id": slave.bk_host_id,
                        },
                    }
                ],
            }
        )

    dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.MySQL)

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_MASTER_SLAVE_SWITCH,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "bk_biz_id": bk_biz_id,
        "remark": TicketType.TENDBCLUSTER_MASTER_SLAVE_SWITCH,
        "details": {
            "bk_cloud_id": bk_cloud_id,
            "bk_biz_id": bk_biz_id,
            "is_check_process": True,
            "is_check_delay": True,
            "is_verify_checksum": True,
            "infos": infos,
            "force": False,
        },
    }

    slz = TendbMasterSlaveSwitchDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_MASTER_SLAVE_SWITCH
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
