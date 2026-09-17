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
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.ticket.builders.common.constants import MySQLBackupSource, OperaObjType
from backend.ticket.builders.mysql.mysql_migrate_cluster import MysqlMigrateClusterDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def bill_tendbha_migrate(
    username: str,
    infos: List[dict],
    opera_object: str,
    backup_source: str = MySQLBackupSource.REMOTE,
    need_checksum: bool = True,
):
    """
    创建 TenDBHA 主从迁移单据，支持多行。

    每行（info）字段：
    - cluster_domain: 集群域名
    - spec_id: 目标规格 ID
    - count: 机器组数（1组=1主+1从）
    - labels: 资源标签 ID 列表（可选）

    opera_object 决定行的粒度：
    - cluster（集群迁移）：每行一个集群，cluster_ids 固定为单集群
    - machine（整机迁移）：每行一个 master+standby slave 机器组，可聚合多个同机关联集群

    opera_object / backup_source / need_checksum 为整单共用参数；is_safe 固定为 True（安全模式）。
    """
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    if opera_object not in [OperaObjType.CLUSTER.value, OperaObjType.MACHINE.value]:
        raise DBMMcpBaseException(msg=_("不支持的迁移类型: {}").format(opera_object))

    cluster_domains = [info["cluster_domain"] for info in infos]
    if len(cluster_domains) != len(set(cluster_domains)):
        raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(cluster_domains))

    cluster_objs, bk_biz_id, _bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBHA)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}

    # 校验所有行的目标规格存在且启用，且为 MySQL backend 存储类型
    spec_ids = {info["spec_id"] for info in infos}
    spec_objs = Spec.objects.filter(
        spec_id__in=spec_ids,
        spec_cluster_type=DBType.MySQL,
        spec_machine_type=SpecMachineType.BACKEND,
        enable=True,
    )
    if spec_objs.count() != len(spec_ids):
        found_ids = set(spec_objs.values_list("spec_id", flat=True))
        missing = spec_ids - found_ids
        raise DBMMcpBaseException(msg=_("目标规格不存在或未启用: spec_id={}").format(sorted(missing)))

    # 集群迁移：每个集群单独一行；整机迁移：按 master+slave 机器组聚合同机关联集群
    built_infos = (
        _build_machine_migrate_infos(infos, cluster_objs, cluster_map)
        if opera_object == OperaObjType.MACHINE.value
        else _build_cluster_migrate_infos(infos, cluster_map)
    )

    ticket_param = {
        "ticket_type": TicketType.MYSQL_MIGRATE_CLUSTER,
        "remark": TicketType.MYSQL_MIGRATE_CLUSTER,
        "creator": username,
        "helpers": [],
        "details": {
            "ip_source": IpSource.RESOURCE_POOL,
            "source_type": SourceType.RESOURCE_AUTO,
            "backup_source": backup_source,
            "is_safe": True,
            "need_checksum": need_checksum,
            "opera_object": opera_object,
            "infos": built_infos,
        },
        "bk_biz_id": bk_biz_id,
    }

    slz = MysqlMigrateClusterDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.MYSQL_MIGRATE_CLUSTER
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    def _fingerprint(infos, opera_object, backup_source, need_checksum):
        return (
            opera_object,
            backup_source,
            need_checksum,
            tuple(
                sorted(
                    (
                        tuple(sorted(info["cluster_ids"])),
                        info["resource_spec"]["backend_group"]["spec_id"],
                        info["resource_spec"]["backend_group"]["count"],
                        tuple(sorted(info["resource_spec"]["backend_group"].get("labels") or [])),
                    )
                    for info in infos
                )
            ),
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.MYSQL_MIGRATE_CLUSTER,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(built_infos, opera_object, backup_source, need_checksum),
        fingerprint_of=lambda tk: _fingerprint(
            tk.details.get("infos", []),
            tk.details.get("opera_object"),
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


def _build_cluster_migrate_infos(infos: List[dict], cluster_map: dict) -> List[dict]:
    """
    集群迁移：每个集群单独一行，cluster_ids 固定为单集群。
    与真实单据 2499858（opera_object=cluster）行为对齐。
    """
    built_infos = []
    for info in infos:
        cluster = cluster_map[info["cluster_domain"]]
        spec_id = info["spec_id"]
        count = info.get("count", 1)
        labels = info.get("labels") or []

        if count <= 0:
            raise DBMMcpBaseException(msg=_("count 必须为正整数: {}").format(count))

        # 主从迁移成对迁移：resource_spec.backend_group（1组 = 1 master + 1 slave）
        resource_spec = {"backend_group": {"count": count, "spec_id": spec_id, "labels": labels}}

        built_infos.append(
            {
                "cluster_ids": [cluster.id],
                "resource_spec": resource_spec,
            }
        )
    return built_infos


def _build_machine_migrate_infos(infos: List[dict], cluster_objs, cluster_map: dict) -> List[dict]:
    """
    整机迁移：按 master+slave 机器组聚合同机关联集群，cluster_ids 传全。
    与真实单据 2499956（opera_object=machine）行为对齐：
    - 一台 master 机器 + 一台 slave 机器构成一个「机器组」；
    - 该机器组承载的所有集群（master 都在同一台 master、slave 都在同一台 slave）合并为一行。
    """
    cluster_ids = [cluster.id for cluster in cluster_objs]

    # 一次性取出所有提交集群的存储实例（master/slave），避免 N+1
    storage_objs = list(
        StorageInstance.objects.using(MYSQL_MCP_DB_READ)
        .filter(cluster__pk__in=cluster_ids)
        .select_related("machine")
        .prefetch_related("cluster")
    )

    insts_by_cluster = {}
    for si in storage_objs:
        for cluster in si.cluster.all():
            if cluster.id in cluster_ids:
                insts_by_cluster.setdefault(cluster.id, []).append(si)

    # 每个集群的 (master_host_id, slave_host_id)
    cluster_master_slave = {}
    for cluster in cluster_objs:
        insts = insts_by_cluster.get(cluster.id, [])
        masters = [si for si in insts if si.instance_inner_role == InstanceInnerRole.MASTER.value]
        slaves = [si for si in insts if si.instance_inner_role == InstanceInnerRole.SLAVE.value and si.is_stand_by]
        if not masters or not slaves:
            raise DBMMcpBaseException(msg=_("集群无主从实例: {}").format(cluster.immute_domain))
        cluster_master_slave[cluster.id] = (masters[0].machine.bk_host_id, slaves[0].machine.bk_host_id)

    # 反查每台 master / slave 机器承载的全部集群（用于补齐同机关联集群）
    all_master_host_ids = {ms[0] for ms in cluster_master_slave.values()}
    all_slave_host_ids = {ms[1] for ms in cluster_master_slave.values()}

    master_cluster_map = {}
    master_objs = (
        StorageInstance.objects.using(MYSQL_MCP_DB_READ)
        .filter(
            machine__bk_host_id__in=all_master_host_ids,
            instance_inner_role=InstanceInnerRole.MASTER.value,
            cluster_type=ClusterType.TenDBHA.value,
        )
        .prefetch_related("cluster")
    )
    for si in master_objs:
        for cluster in si.cluster.all():
            master_cluster_map.setdefault(si.machine.bk_host_id, set()).add(cluster.id)

    slave_cluster_map = {}
    slave_objs = (
        StorageInstance.objects.using(MYSQL_MCP_DB_READ)
        .filter(
            machine__bk_host_id__in=all_slave_host_ids,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            is_stand_by=True,
            cluster_type=ClusterType.TenDBHA.value,
        )
        .prefetch_related("cluster")
    )
    for si in slave_objs:
        for cluster in si.cluster.all():
            slave_cluster_map.setdefault(si.machine.bk_host_id, set()).add(cluster.id)

    # 按 (master_host_id, slave_host_id) 分组提交集群
    groups = {}
    for info in infos:
        cluster = cluster_map[info["cluster_domain"]]
        key = cluster_master_slave[cluster.id]
        spec_id = info["spec_id"]
        count = info.get("count", 1)
        labels = info.get("labels") or []

        if count <= 0:
            raise DBMMcpBaseException(msg=_("count 必须为正整数: {}").format(count))

        group = groups.setdefault(key, {"cluster_ids": set(), "spec_ids": set(), "counts": set(), "labels": None})
        group["cluster_ids"].add(cluster.id)
        group["spec_ids"].add(spec_id)
        group["counts"].add(count)
        if group["labels"] is None:
            group["labels"] = labels
        elif sorted(group["labels"]) != sorted(labels):
            raise DBMMcpBaseException(msg=_("同机迁移集群资源标签不一致: {}").format(cluster.immute_domain))

    # 自动补齐：每个机器组承载的全部集群（master 与 slave 机器交集）
    for key in groups:
        master_host_id, slave_host_id = key
        related_clusters = master_cluster_map.get(master_host_id, set()) & slave_cluster_map.get(slave_host_id, set())
        groups[key]["cluster_ids"] |= related_clusters

    # 组装最终 infos
    built_infos = []
    for group in groups.values():
        cluster_ids_in_group = sorted(group["cluster_ids"])
        if len(group["spec_ids"]) != 1:
            raise DBMMcpBaseException(msg=_("同机迁移集群目标规格不一致: {}").format(cluster_ids_in_group))
        if len(group["counts"]) != 1:
            raise DBMMcpBaseException(msg=_("同机迁移集群机器组数不一致: {}").format(cluster_ids_in_group))

        spec_id = next(iter(group["spec_ids"]))
        count = next(iter(group["counts"]))
        resource_spec = {"backend_group": {"count": count, "spec_id": spec_id, "labels": group["labels"]}}

        built_infos.append(
            {
                "cluster_ids": cluster_ids_in_group,
                "resource_spec": resource_spec,
            }
        )

    return built_infos
