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
import re
from typing import List

from backend import env
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpClusterNotFoundException,
    DBMMcpForbiddenException,
    DBMMcpNoneBillSubmittedException,
    DBMMcpNotSupportClusterTypeException,
)
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.ticket.builders.mysql.mysql_ha_destroy import MysqlHADestroyDetailSerializer
from backend.ticket.builders.mysql.mysql_single_destroy import MysqlSingleDestroyDetailSerializer
from backend.ticket.builders.tendbcluster.tendb_destroy import TendbDestroyDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

# 允许删除的临时集群域名命名规范（正则，与禁用保持一致）：
# 1. tmpdb. + 内容 + .dba.db，如 tmpdb.abc.dba.db
# 2. spider. + 内容 + -tmp + 8位日期数字 + -，如 spider.abc-tmp20240801-xxx
ALLOWED_DESTROY_DOMAIN_PATTERNS = [
    re.compile(r"^tmpdb\..+\.dba\.db$"),
    re.compile(r"^spider\..+-tmp\d{8}-"),
]
# 命名规范的人类可读描述（用于报错提示）
ALLOWED_DESTROY_DOMAIN_RULES = ["tmpdb.内容.dba.db", "spider.内容-tmpYYYYMMDD-"]

# 集群类型 -> (TicketType, DetailSerializer) 映射，按类型分组提单
_DESTROY_GROUP_MAP = [
    (ClusterType.TenDBHA, TicketType.MYSQL_HA_DESTROY, MysqlHADestroyDetailSerializer),
    (ClusterType.TenDBSingle, TicketType.MYSQL_SINGLE_DESTROY, MysqlSingleDestroyDetailSerializer),
    (ClusterType.TenDBCluster, TicketType.TENDBCLUSTER_DESTROY, TendbDestroyDetailSerializer),
]


def bill_mysql_destroy(
    username: str,
    bk_biz_id: int,
    cluster_domains: List[str],
) -> list:
    """创建 MySQL 集群删除单据，返回业务维度单据链接

    前置条件：集群必须处于禁用状态（phase == ClusterPhase.OFFLINE）才可以提交删除单据。

    返回结构：[{bill_id, bill_url}]，其中 bill_url 为业务单据管理页链接：
    {BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{ticket_id}
    """
    # 空列表显式报错，避免静默返回空结果（LLM 会误以为已提交）
    if not cluster_domains:
        raise DBMMcpForbiddenException(msg="cluster_domains 不能为空")

    # 命名规范校验：一次传入的多个集群必须全部符合规范才可提交，否则整体拒绝并返回不符合的集群名
    invalid_domains = [d for d in cluster_domains if not any(p.match(d) for p in ALLOWED_DESTROY_DOMAIN_PATTERNS)]
    if invalid_domains:
        raise DBMMcpForbiddenException(
            msg="一次提交的集群必须全部符合临时集群命名规范（{}），以下集群不符合：{}".format(
                " / ".join(ALLOWED_DESTROY_DOMAIN_RULES), ", ".join(invalid_domains)
            )
        )

    clusters = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(bk_biz_id=bk_biz_id, immute_domain__in=cluster_domains)
    # 校验提交的域名是否全部命中集群，防止部分域名被静默丢弃（拼写错误/跨业务/已删除）
    found_domains = set(clusters.values_list("immute_domain", flat=True))
    not_found_domains = set(cluster_domains) - found_domains
    if not_found_domains:
        raise DBMMcpClusterNotFoundException(
            msg="以下集群未找到，请检查域名是否正确/是否属于当前业务：{}".format(", ".join(sorted(not_found_domains)))
        )

    supported_types = [item[0] for item in _DESTROY_GROUP_MAP]
    unsupported_clusters = clusters.exclude(cluster_type__in=supported_types)
    if unsupported_clusters.exists():
        raise DBMMcpNotSupportClusterTypeException(
            cluster_type=set(unsupported_clusters.values_list("cluster_type", flat=True))
        )

    # 核心校验：集群状态必须是禁用状态（phase == offline）才可以提交删除单据
    not_disabled_clusters = clusters.exclude(phase=ClusterPhase.OFFLINE.value)
    if not_disabled_clusters.exists():
        raise DBMMcpForbiddenException(
            msg="集群必须处于禁用状态（offline）才可以提交删除单据，以下集群未禁用：{}".format(
                ", ".join(not_disabled_clusters.values_list("immute_domain", flat=True))
            )
        )

    # 两阶段提单：先完成所有类型的入参校验，全部通过后才创建单据，
    # 避免「类型 A 已建单、类型 B 校验失败」导致的部分提交（部分成功且未回滚）
    pending_tickets = []
    for cluster_type, ticket_type, detail_slz_cls in _DESTROY_GROUP_MAP:
        type_clusters = clusters.filter(cluster_type=cluster_type)
        if not type_clusters.exists():
            continue

        ticket_param = {
            "ticket_type": ticket_type,
            "remark": ticket_type,
            "creator": username,
            "helpers": [],
            "bk_biz_id": bk_biz_id,
            "details": {
                "cluster_ids": list(type_clusters.values_list("pk", flat=True).distinct()),
                # 固定非强制删除：不允许外部传入 force，执行侧始终走安全检查
                "force": False,
            },
        }

        slz = detail_slz_cls(data=ticket_param["details"])
        slz.context["bk_biz_id"] = bk_biz_id
        slz.context["ticket_type"] = ticket_type
        slz.is_valid(raise_exception=True)
        pending_tickets.append(ticket_param)

    res = []
    for ticket_param in pending_tickets:
        tk = Ticket.create_ticket(**ticket_param)
        res.append(
            {
                "bill_id": tk.pk,
                "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{tk.pk}",
            }
        )

    if not res:
        raise DBMMcpNoneBillSubmittedException(msg="未生成任何删除单据，请检查集群域名")

    return res
