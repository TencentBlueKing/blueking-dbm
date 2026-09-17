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

from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.helper import (
    validate_sqlserver_ha_clusters,
    validate_sqlserver_specs,
)
from backend.ticket.builders.sqlserver.sqlserver_cluster_migrate import SQLServerClusterMigrateDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_sqlserver_cluster_migrate(username: str, infos: List[dict]):
    """创建 SQLServer 集群迁移单据，支持多行，每行一个集群 + 目标规格。"""
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    cluster_domains = [info["cluster_domain"] for info in infos]
    if len(cluster_domains) != len(set(cluster_domains)):
        raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(cluster_domains))

    cluster_objs, bk_biz_id, _bk_cloud_id = validate_sqlserver_ha_clusters(cluster_domains)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}

    spec_ids = {info["spec_id"] for info in infos}
    validate_sqlserver_specs(spec_ids)

    built_infos = []
    for info in infos:
        cluster = cluster_map[info["cluster_domain"]]
        spec_id = info["spec_id"]
        count = info.get("count", 1)
        labels = info.get("labels") or []

        if count <= 0:
            raise DBMMcpBaseException(msg=_("count 必须为正整数: {}").format(count))

        built_infos.append(
            {
                "cluster_ids": [cluster.id],
                "resource_spec": {"backend_group": {"count": count, "spec_id": spec_id, "labels": labels}},
            }
        )

    ticket_param = {
        "ticket_type": TicketType.SQLSERVER_CLUSTER_MIGRATE,
        "remark": TicketType.SQLSERVER_CLUSTER_MIGRATE,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "ip_source": IpSource.RESOURCE_POOL,
            "infos": built_infos,
        },
    }

    slz = SQLServerClusterMigrateDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.SQLSERVER_CLUSTER_MIGRATE
    slz.context["bk_biz_id"] = bk_biz_id
    slz.is_valid(raise_exception=True)

    def _fingerprint(infos):
        return tuple(
            sorted(
                (
                    tuple(sorted(info["cluster_ids"])),
                    info["resource_spec"]["backend_group"]["spec_id"],
                    info["resource_spec"]["backend_group"]["count"],
                    tuple(sorted(info["resource_spec"]["backend_group"].get("labels") or [])),
                )
                for info in infos
            )
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.SQLSERVER_CLUSTER_MIGRATE,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(built_infos),
        fingerprint_of=lambda tk: _fingerprint(tk.details.get("infos", [])),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
