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
from backend.db_meta.models import StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.helper import (
    validate_sqlserver_ha_clusters,
    validate_sqlserver_specs,
)
from backend.ticket.builders.sqlserver.sqlserver_restore_slave import SQLServerRestoreSlaveDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_sqlserver_restore_slave(
    username: str, cluster_domain: str, ips: List[str], spec_id: int, labels: List[str] = None
):
    """创建 SQLServer 新机重建单据，ips 仅支持单个旧 slave ip。"""
    if len(ips) != 1:
        raise DBMMcpBaseException(msg=_("期望恰好 1 个旧 slave ip, 实际: {}").format(ips))

    ip = ips[0]
    labels = labels or []

    cluster_objs, bk_biz_id, bk_cloud_id = validate_sqlserver_ha_clusters([cluster_domain])
    cluster = cluster_objs[0]

    validate_sqlserver_specs({spec_id})

    slave = (
        StorageInstance.objects.filter(
            cluster=cluster,
            machine__ip=ip,
            machine__bk_cloud_id=bk_cloud_id,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
        )
        .select_related("machine")
        .first()
    )
    if not slave:
        raise DBMMcpBaseException(msg=_("未找到旧 slave 实例: {}@{}").format(cluster_domain, ip))

    ticket_param = {
        "ticket_type": TicketType.SQLSERVER_RESTORE_SLAVE,
        "remark": TicketType.SQLSERVER_RESTORE_SLAVE,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "ip_source": IpSource.RESOURCE_POOL,
            "infos": [
                {
                    "cluster_ids": [cluster.id],
                    "old_nodes": {
                        "old_slave_host": [
                            {
                                "ip": ip,
                                "bk_cloud_id": bk_cloud_id,
                                "bk_host_id": slave.machine.bk_host_id,
                            }
                        ]
                    },
                    "resource_spec": {"sqlserver_ha": {"spec_id": spec_id, "count": 1, "labels": labels}},
                }
            ],
        },
    }

    slz = SQLServerRestoreSlaveDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.SQLSERVER_RESTORE_SLAVE
    slz.context["bk_biz_id"] = bk_biz_id
    slz.is_valid(raise_exception=True)

    def _fingerprint(infos):
        return tuple(
            sorted(
                (
                    tuple(sorted(info["cluster_ids"])),
                    info["old_nodes"]["old_slave_host"][0]["ip"],
                    info["resource_spec"]["sqlserver_ha"]["spec_id"],
                    info["resource_spec"]["sqlserver_ha"]["count"],
                    tuple(sorted(info["resource_spec"]["sqlserver_ha"].get("labels") or [])),
                )
                for info in infos
            )
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.SQLSERVER_RESTORE_SLAVE,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(ticket_param["details"]["infos"]),
        fingerprint_of=lambda tk: _fingerprint(tk.details.get("infos", [])),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
