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
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import ProxyInstance
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import (
    check_clusters_consistency,
    validate_clusters,
)
from backend.ticket.builders.mysql.mysql_proxy_switch import MysqlProxySwitchDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_proxy_replace(cluster_domains: List[str], ips: List[str]):
    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBHA)

    proxy_objs = ProxyInstance.objects.using(MYSQL_MCP_DB_READ).filter(
        machine__ip__in=ips, machine__bk_cloud_id=bk_cloud_id
    )
    check_clusters_consistency(cluster_objs, ips, proxy_objs)

    dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.MySQL)

    proxy_infos = []
    spec_ids = set()
    for pi in proxy_objs:
        proxy_infos.append(
            {
                "bk_cloud_id": bk_cloud_id,
                "ip": pi.machine.ip,
                "bk_host_id": pi.machine.bk_host_id,
                "bk_biz_id": bk_biz_id,
                "port": 0,
            }
        )
        spec_ids.add(pi.machine.spec_id)
    proxy_infos = list({pi["bk_host_id"]: pi for pi in proxy_infos}.values())

    if len(spec_ids) > 1:
        raise

    resource_spec = {"spec_id": list(spec_ids)[0], "count": len(ips)}

    ticket_param = {
        "ticket_type": TicketType.MYSQL_PROXY_SWITCH,
        "remark": TicketType.MYSQL_PROXY_SWITCH,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "details": {
            "is_safe": False,
            "ip_source": IpSource.RESOURCE_POOL,
            "infos": [
                {
                    "cluster_ids": list(set(cluster_objs.values_list("id", flat=True))),
                    "origin_proxies": proxy_infos,
                    "old_nodes": {
                        "proxy": proxy_infos,
                    },
                    "resource_spec": {"target_proxies": resource_spec},
                }
            ],
            "disable_manual_confirm": False,
        },
        "bk_biz_id": int(bk_biz_id),
    }

    slz = MysqlProxySwitchDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.MYSQL_PROXY_SWITCH
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    tk = Ticket.create_ticket(**ticket_param)
    return tk
