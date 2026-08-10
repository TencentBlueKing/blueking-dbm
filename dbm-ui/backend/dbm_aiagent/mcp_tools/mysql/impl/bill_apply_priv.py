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

from django.utils.translation import gettext_lazy as _

from backend.components import DBPrivManagerApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.dbpermission.db_account.handlers import AccountHandler
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpMySQLApplyPrivAccountNotFoundException,
    DBMMcpMySQLApplyPrivDBRuleNotFoundException,
    DBMMcpNotSupportClusterTypeException,
)
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.ticket.builders.mysql.mysql_authorize_rules import MySQLAuthorizeRulesSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_apply_priv(
    request,
    username: str,
    apply_access_dbs: List[str],
    apply_username: str,
    apply_source_ips: List[str],
    cluster_domain: str,
    bk_biz_id: int,
) -> Ticket:
    cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_type = cluster_obj.cluster_type

    if cluster_type == ClusterType.TenDBCluster:
        ticket_type = TicketType.TENDBCLUSTER_AUTHORIZE_RULES
    elif cluster_type in [ClusterType.TenDBHA, ClusterType.TenDBSingle]:
        ticket_type = TicketType.MYSQL_AUTHORIZE_RULES
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)

    auth_data = {
        "access_dbs": apply_access_dbs,
        "user": apply_username,
        "source_ips": apply_source_ips,
        "target_instances": [cluster_domain],
        "cluster_type": cluster_type,
    }

    account_type = ClusterType.cluster_type_to_db_type(cluster_type)

    priv_res = DBPrivManagerApi.get_account(params={"cluster_type": account_type, "bk_biz_id": bk_biz_id})
    user_info_map = {user["user"]: user for user in priv_res["results"]}
    if apply_username not in user_info_map:
        raise DBMMcpMySQLApplyPrivAccountNotFoundException(msg=_("需要在 DBM 授权管理中创建 {} 账号".format(apply_username)))

    user_db_map = AccountHandler.aggregate_user_db_rules(bk_biz_id, account_type)

    not_found_dbs = [a_db for a_db in apply_access_dbs if a_db not in user_db_map[apply_username]]

    if not_found_dbs:
        raise DBMMcpMySQLApplyPrivDBRuleNotFoundException(
            msg=_("需要在 DBM 授权管理中为 {} 添加 {} 授权模版".format(apply_username, apply_access_dbs))
        )

    slz = MySQLAuthorizeRulesSerializer(
        data={"authorize_plugin_infos": [{**auth_data, "bk_biz_id": bk_biz_id}], "need_itsm": True}
    )
    slz.context["request"] = request
    slz.is_valid(raise_exception=True)

    ticket_param = {
        "ticket_type": ticket_type,
        "remark": ticket_type,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": slz.validated_data,
    }

    return Ticket.create_ticket(**ticket_param)
