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
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import ProxyInstance
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import (
    check_clusters_consistency,
    validate_clusters,
)
from backend.ticket.builders.tendbcluster.tendb_spider_switch_nodes import SpiderSwitchNodesDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_spider_replace(cluster_domain: str, ips: List[str]):
    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters([cluster_domain], ClusterType.TenDBCluster)

    spider_objs = ProxyInstance.objects.using(MYSQL_MCP_DB_READ).filter(
        machine__ip__in=ips, machine__bk_cloud_id=bk_cloud_id
    )

    check_clusters_consistency(cluster_objs, ips, spider_objs)

    dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.TenDBCluster)

    infos = []
    for spider_role in TenDBClusterSpiderRole.get_values():
        if spider_role == TenDBClusterSpiderRole.SPIDER_CTL.value:
            continue

        this_role_spiders = spider_objs.filter(tendbclusterspiderext__spider_role=spider_role)
        if not this_role_spiders.exists():
            continue

        spec_ids = set()
        spider_old_ip_list = []
        for si in this_role_spiders:
            spider_old_ip_list.append(
                {
                    "bk_cloud_id": bk_cloud_id,
                    "ip": si.machine.ip,
                    "bk_host_id": si.machine.bk_host_id,
                    "bk_biz_id": bk_biz_id,
                    "port": si.port,
                }
            )
            spec_ids.add(si.machine.spec_id)

        if len(spec_ids) > 1:
            raise

        info = {
            "cluster_id": cluster_objs[0].pk,
            "resource_spec": {
                f"{spider_role}": {
                    "spec_id": list(spec_ids)[0],
                    "count": this_role_spiders.values_list("machine__ip", flat=True).count(),
                }
            },
            "spider_old_ip_list": spider_old_ip_list,
            "old_nodes": {"spider_old_ip_list": spider_old_ip_list},
            "switch_spider_role": spider_role,
        }
        infos.append(info)

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_SPIDER_SWITCH_NODES,
        "remark": TicketType.TENDBCLUSTER_SPIDER_SWITCH_NODES,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "details": {
            "is_safe": False,
            "ip_source": IpSource.RESOURCE_POOL,
            "disable_manual_confirm": False,
            "infos": infos,
        },
        "bk_biz_id": bk_biz_id,
    }

    slz = SpiderSwitchNodesDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_SPIDER_SWITCH_NODES
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
