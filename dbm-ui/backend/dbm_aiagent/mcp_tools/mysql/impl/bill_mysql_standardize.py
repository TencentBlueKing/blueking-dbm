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
import copy
from typing import List

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpClusterNotFoundException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_mysql_standardize(
    username: str,
    bk_biz_id: int,
    cluster_domains: List[str],
    with_instance_standardize: bool,
    with_cc_standardize: bool,
    with_deploy_binary: bool,
    with_push_config: bool,
) -> List[Ticket]:
    mysql_clusters = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(
        bk_biz_id=bk_biz_id,
        cluster_type__in=[ClusterType.TenDBSingle, ClusterType.TenDBHA],
        immute_domain__in=cluster_domains,
    )
    tendbcluster_clusters = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(
        bk_biz_id=bk_biz_id, cluster_type=ClusterType.TenDBCluster, immute_domain__in=cluster_domains
    )

    if not mysql_clusters.exists() and not tendbcluster_clusters.exists():
        raise DBMMcpClusterNotFoundException(msg=f"{cluster_domains}")

    ticket_param_common = {
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "cluster_ids": None,
            "bk_biz_id": bk_biz_id,
            "with_deploy_binary": with_deploy_binary,
            "with_push_config": with_push_config,
            "with_cc_standardize": with_cc_standardize,
            "with_instance_standardize": with_instance_standardize,
        },
    }

    res = []

    if mysql_clusters.exists():
        ticket_param = copy.deepcopy(ticket_param_common)
        ticket_param["ticket_type"] = TicketType.MYSQL_CLUSTER_STANDARDIZE
        ticket_param["remark"] = TicketType.MYSQL_CLUSTER_STANDARDIZE
        ticket_param["details"]["cluster_ids"] = list(mysql_clusters.values_list("pk", flat=True).distinct())
        tk = Ticket.create_ticket(**ticket_param)
        res.append(tk)

    if tendbcluster_clusters.exists():
        ticket_param = copy.deepcopy(ticket_param_common)
        ticket_param["ticket_type"] = TicketType.TENDBCLUSTER_CLUSTER_STANDARDIZE
        ticket_param["remark"] = TicketType.TENDBCLUSTER_CLUSTER_STANDARDIZE
        ticket_param["details"]["cluster_ids"] = list(tendbcluster_clusters.values_list("pk", flat=True).distinct())
        tk = Ticket.create_ticket(**ticket_param)
        res.append(tk)

    return res
