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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.helper import (
    validate_sqlserver_ha_clusters,
    validate_sqlserver_specs,
)
from backend.ticket.builders.sqlserver.sqlserver_host_migrate import SQLServerHostMigrateDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_sqlserver_host_migrate(username: str, infos: List[dict]):
    """创建 SQLServer 整机迁移单据，支持多行，每行一台源主机 + 目标规格。"""
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    all_domains = [d for info in infos for d in info["cluster_domains"]]
    # 整机迁移中同一集群的 master/slave 分属不同源主机，允许跨行重复；仅校验每行内部无重复
    for info in infos:
        domains = info["cluster_domains"]
        if len(domains) != len(set(domains)):
            raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(domains))

    cluster_objs, bk_biz_id, bk_cloud_id = validate_sqlserver_ha_clusters(all_domains)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}

    spec_ids = {info["spec_id"] for info in infos}
    validate_sqlserver_specs(spec_ids)

    # 一次性取出所有源主机及其 SQLServer 存储实例，避免循环内逐行查询造成 N+1
    all_ips = [info["ip"] for info in infos]
    machines = {m.ip: m for m in Machine.objects.filter(ip__in=all_ips, bk_cloud_id=bk_cloud_id)}

    storage_objs = list(
        StorageInstance.objects.filter(machine__in=list(machines.values()), cluster_type=ClusterType.SqlserverHA)
        .select_related("machine")
        .prefetch_related("cluster")
    )
    instances_by_machine = {}
    for si in storage_objs:
        instances_by_machine.setdefault(si.machine.ip, []).append(si)

    built_infos = []
    for info in infos:
        ip = info["ip"]
        domains = info["cluster_domains"]
        cluster_ids = [cluster_map[d].id for d in domains]
        spec_id = info["spec_id"]
        count = info.get("count", 1)
        labels = info.get("labels") or []

        if count <= 0:
            raise DBMMcpBaseException(msg=_("count 必须为正整数: {}").format(count))

        machine = machines.get(ip)
        if not machine:
            raise DBMMcpBaseException(msg=_("未找到源主机: {}").format(ip))

        machine_insts = instances_by_machine.get(ip, [])
        machine_cluster_ids = set()
        for si in machine_insts:
            machine_cluster_ids.update(cluster.id for cluster in si.cluster.all())
        if machine_cluster_ids != set(cluster_ids):
            raise DBMMcpBaseException(
                msg=_("源主机 {ip} 承载集群 {machine} 与输入集群 {input} 不一致").format(
                    ip=ip,
                    machine=sorted(machine_cluster_ids),
                    input=sorted(cluster_ids),
                )
            )

        # 关联集群实例信息（与前端整机迁移提单保持一致，用于单据详情「关联集群实例」列展示）
        related_cluster_infos = [
            {
                "cluster_id": cluster.id,
                "instance_address": f"{machine.ip}:{si.port}",
                "master_domain": cluster.immute_domain,
            }
            for si in machine_insts
            for cluster in si.cluster.all()
        ]

        built_infos.append(
            {
                "cluster_ids": cluster_ids,
                "origin_ip": {
                    "ip": machine.ip,
                    "bk_cloud_id": machine.bk_cloud_id,
                    "bk_host_id": machine.bk_host_id,
                },
                "related_cluster_infos": related_cluster_infos,
                "resource_spec": {"backend_group": {"count": count, "spec_id": spec_id, "labels": labels}},
            }
        )

    ticket_param = {
        "ticket_type": TicketType.SQLSERVER_HOST_MIGRATE,
        "remark": TicketType.SQLSERVER_HOST_MIGRATE,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "ip_source": IpSource.RESOURCE_POOL,
            "infos": built_infos,
        },
    }

    slz = SQLServerHostMigrateDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.SQLSERVER_HOST_MIGRATE
    slz.context["bk_biz_id"] = bk_biz_id
    slz.is_valid(raise_exception=True)

    def _fingerprint(infos):
        return tuple(
            sorted(
                (
                    tuple(sorted(info["cluster_ids"])),
                    info["origin_ip"]["ip"],
                    info["resource_spec"]["backend_group"]["spec_id"],
                    info["resource_spec"]["backend_group"]["count"],
                    tuple(sorted(info["resource_spec"]["backend_group"].get("labels") or [])),
                )
                for info in infos
            )
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.SQLSERVER_HOST_MIGRATE,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(built_infos),
        fingerprint_of=lambda tk: _fingerprint(tk.details.get("infos", [])),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
