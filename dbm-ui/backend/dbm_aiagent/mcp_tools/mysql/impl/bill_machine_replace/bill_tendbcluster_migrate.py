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

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_meta.models import Spec, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.tendbcluster.tendb_migrate_cluster import TendbClusterMigrateClusterDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def bill_tendbcluster_migrate(
    username: str,
    infos: List[dict],
    backup_source: str = MySQLBackupSource.REMOTE,
    need_checksum: bool = True,
):
    """
    创建 TenDB Cluster 主从迁移单据，支持多行，每行一对 remote 主从。

    每行（info）字段：
    - cluster_domain: 集群域名
    - old_master_ip: 旧 remote master IP
    - old_slave_ip: 旧 remote slave IP
    - spec_id: 目标规格 ID
    - count: 机器组数（1组=1主+1从），默认 1
    - labels: 资源标签 ID 列表（可选）

    backup_source / need_checksum 为整单共用参数；is_safe 固定为 True（安全模式）。
    """
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    cluster_domains = [info["cluster_domain"] for info in infos]
    if len(cluster_domains) != len(set(cluster_domains)):
        raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(cluster_domains))

    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBCluster)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}

    # 校验所有行的目标规格存在且启用，且为 remote（backend）类型
    spec_ids = {info["spec_id"] for info in infos}
    spec_objs = Spec.objects.filter(
        spec_id__in=spec_ids,
        spec_cluster_type=DBType.TenDBCluster,
        spec_machine_type=SpecMachineType.BACKEND,
        enable=True,
    )
    if spec_objs.count() != len(spec_ids):
        found_ids = set(spec_objs.values_list("spec_id", flat=True))
        missing = spec_ids - found_ids
        raise DBMMcpBaseException(msg=_("目标规格不存在或未启用: spec_id={}").format(sorted(missing)))

    built_infos = []
    for info in infos:
        cluster = cluster_map[info["cluster_domain"]]
        old_master_ip = info["old_master_ip"]
        old_slave_ip = info["old_slave_ip"]
        spec_id = info["spec_id"]
        count = info.get("count", 1)
        labels = info.get("labels") or []

        if count <= 0:
            raise DBMMcpBaseException(msg=_("机器组数必须为正整数: {}").format(count))

        # 反查旧 remote master / slave 实例，校验确实属于该集群
        master_inst = (
            StorageInstance.objects.using(MYSQL_MCP_DB_READ)
            .filter(
                cluster=cluster,
                machine__ip=old_master_ip,
                instance_inner_role=InstanceInnerRole.MASTER.value,
            )
            .select_related("machine")
            .first()
        )
        if not master_inst:
            raise DBMMcpBaseException(
                msg=_("IP {} 不是集群 {} 的 remote master").format(old_master_ip, cluster.immute_domain)
            )

        slave_inst = (
            StorageInstance.objects.using(MYSQL_MCP_DB_READ)
            .filter(
                cluster=cluster,
                machine__ip=old_slave_ip,
                instance_inner_role=InstanceInnerRole.SLAVE.value,
                is_stand_by=True,
            )
            .select_related("machine")
            .first()
        )
        if not slave_inst:
            raise DBMMcpBaseException(
                msg=_("IP {} 不是集群 {} 的 remote slave").format(old_slave_ip, cluster.immute_domain)
            )

        old_master_info = {
            "ip": old_master_ip,
            "bk_host_id": master_inst.machine.bk_host_id,
            "bk_cloud_id": bk_cloud_id,
            "bk_biz_id": bk_biz_id,
        }
        old_slave_info = {
            "ip": old_slave_ip,
            "bk_host_id": slave_inst.machine.bk_host_id,
            "bk_cloud_id": bk_cloud_id,
            "bk_biz_id": bk_biz_id,
        }

        resource_spec = {
            "backend_group": {
                "count": count,
                "spec_id": spec_id,
                "labels": labels,
            }
        }

        built_infos.append(
            {
                "old_nodes": {
                    "old_master": [old_master_info],
                    "old_slave": [old_slave_info],
                },
                "cluster_id": cluster.id,
                "resource_spec": resource_spec,
            }
        )

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_MIGRATE_CLUSTER,
        "remark": TicketType.TENDBCLUSTER_MIGRATE_CLUSTER,
        "creator": username,
        "helpers": [],
        "details": {
            "ip_source": IpSource.RESOURCE_POOL,
            "backup_source": backup_source,
            "is_safe": True,
            "need_checksum": need_checksum,
            "infos": built_infos,
        },
        "bk_biz_id": bk_biz_id,
    }

    slz = TendbClusterMigrateClusterDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_MIGRATE_CLUSTER
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    def _fingerprint(infos, backup_source, need_checksum):
        return (
            backup_source,
            need_checksum,
            tuple(
                sorted(
                    (
                        info["cluster_id"],
                        info["old_nodes"]["old_master"][0]["ip"],
                        info["old_nodes"]["old_slave"][0]["ip"],
                        info["resource_spec"]["backend_group"]["spec_id"],
                        info["resource_spec"]["backend_group"]["count"],
                        tuple(sorted(info["resource_spec"]["backend_group"].get("labels") or [])),
                    )
                    for info in infos
                )
            ),
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.TENDBCLUSTER_MIGRATE_CLUSTER,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(built_infos, backup_source, need_checksum),
        fingerprint_of=lambda tk: _fingerprint(
            tk.details.get("infos", []),
            tk.details.get("backup_source"),
            tk.details.get("need_checksum"),
        ),
    )
    if existing:
        return [
            {
                "bill_id": existing.pk,
                "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{existing.pk}",
            }
        ]

    tk = Ticket.create_ticket(**ticket_param)
    return [{"bill_id": tk.pk, "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{tk.pk}"}]
