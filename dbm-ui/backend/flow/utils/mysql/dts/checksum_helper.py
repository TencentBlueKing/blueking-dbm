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
from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.utils.mysql.dts.migrate_helper import resolve_cluster_target_spider_endpoint, resolve_source_endpoint
from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskSpec, SyncScope
from backend.ticket.builders.common.constants import MySQLChecksumTicketMode
from backend.ticket.constants import TicketType


def _to_checksum_glob(name: str) -> str:
    """DTS 通配 * 转为 checksum 方言：独立 * 保持 *，tb_* 转为 tb_%。"""
    text = (name or "").strip()
    if not text or set(text) == {"*"}:
        return "*"
    return text.replace("*", "%")


def _unique_keep_order(names: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _ignore_table_names(scope: SyncScope) -> list[str]:
    ignore_tables: list[str] = []
    for item in scope.ignore_tables or []:
        if isinstance(item, dict):
            ignore_tables.append(item.get("table") or item.get("tablename") or "")
        elif isinstance(item, str):
            ignore_tables.append(item.split(".")[-1])
    return [t for t in ignore_tables if t]


def _scope_to_checksum_patterns(scope: SyncScope) -> tuple[list[str], list[str], list[str], list[str]]:
    """将迁移 sync_scope 粗映射为 checksum db/table patterns。

    table_routes 优先取源端（source_db / source_db_pattern / source_table），不读 target。
    """
    ignore_dbs = list(scope.ignore_dbs or [])
    ignore_tables = _ignore_table_names(scope)
    if scope.table_routes:
        db_patterns = _unique_keep_order(
            [_to_checksum_glob(route.source_schema()) for route in scope.table_routes if route.source_schema()]
        )
        table_patterns = _unique_keep_order(
            [_to_checksum_glob(route.source_table_name()) for route in scope.table_routes]
        )
        return db_patterns, ignore_dbs, table_patterns or ["*"], ignore_tables

    db_patterns = list(scope.do_dbs or []) or ["*"]
    table_patterns: list[str] = []
    for item in scope.do_tables or []:
        if isinstance(item, dict):
            table_patterns.append(item.get("table") or item.get("tablename") or "*")
        elif isinstance(item, str):
            table_patterns.append(item.split(".")[-1])
    if not table_patterns:
        table_patterns = ["*"]
    return db_patterns, ignore_dbs, table_patterns, ignore_tables


def _instance_payload(ins: StorageInstance | ProxyInstance, cluster: Cluster, inner_role: str) -> dict[str, Any]:
    return {
        "id": ins.id,
        "bk_biz_id": cluster.bk_biz_id,
        "bk_cloud_id": cluster.bk_cloud_id,
        "bk_host_id": ins.machine_id,
        "ip": ins.machine.ip,
        "port": ins.port,
        "instance_inner_role": inner_role,
    }


def _resolve_storage_by_endpoint(cluster: Cluster, host: str, port: int) -> StorageInstance:
    ins = cluster.storageinstance_set.filter(machine__ip=host, port=port).first()
    if not ins:
        raise ValueError(_("集群 {} 上未找到实例 {}:{}").format(cluster.id, host, port))
    return ins


def _resolve_proxy_by_endpoint(cluster: Cluster, host: str, port: int) -> ProxyInstance:
    ins = cluster.proxyinstance_set.filter(machine__ip=host, port=port).first()
    if not ins:
        raise ValueError(_("集群 {} 上未找到 Proxy 实例 {}:{}").format(cluster.id, host, port))
    return ins


def _resolve_target_write_instance(cluster: Cluster) -> StorageInstance:
    """目标侧按 checksum slave 角色使用：优先 Backend/Remote Master（DTS 写入端）。"""
    for role in (InstanceRole.BACKEND_MASTER, InstanceRole.REMOTE_MASTER):
        ins = cluster.storageinstance_set.filter(instance_role=role).first()
        if ins:
            return ins
    ins = cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER.value).first()
    if not ins:
        raise ValueError(_("目标集群 {} 未找到可用写入实例").format(cluster.id))
    return ins


def build_dts_checksum_ticket_info(*, task_spec: DtsTaskSpec, bk_biz_id: int) -> dict[str, Any]:
    """组装 DTS 模式关联 checksum 单据详情（源=master，目标=slave）。"""
    if not task_spec.sources:
        raise ValueError(_("checksum 组装失败：task_spec 无 sources"))
    source_spec = task_spec.sources[0]
    src_cluster = Cluster.objects.get(id=source_spec.cluster_id)
    dst_cluster = Cluster.objects.get(id=task_spec.target_cluster_id)
    host, port = resolve_source_endpoint(source_spec, src_cluster)
    master_ins = _resolve_storage_by_endpoint(src_cluster, host, port)
    if dst_cluster.cluster_type == ClusterType.TenDBCluster.value:
        spider_host, spider_port = resolve_cluster_target_spider_endpoint(dst_cluster, task_spec.target_spider)
        slave_ins = _resolve_proxy_by_endpoint(dst_cluster, spider_host, spider_port)
    else:
        slave_ins = _resolve_target_write_instance(dst_cluster)
    db_patterns, ignore_dbs, table_patterns, ignore_tables = _scope_to_checksum_patterns(source_spec.sync_scope)

    return {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.MYSQL_DTS_CHECKSUM,
        "remark": _("DTS 迁移自动生成 checksum 单据"),
        "details": {
            "data_repair": {"is_repair": False, "mode": MySQLChecksumTicketMode.MANUAL},
            "is_sync_non_innodb": False,
            "runtime_hour": 48,
            "dts_mode": True,
            "need_manual_confirm": False,
            "infos": [
                {
                    "cluster_id": src_cluster.id,
                    "dts_mode": True,
                    "master": _instance_payload(master_ins, src_cluster, InstanceInnerRole.MASTER.value),
                    "slaves": [_instance_payload(slave_ins, dst_cluster, InstanceInnerRole.SLAVE.value)],
                    "db_patterns": db_patterns,
                    "ignore_dbs": ignore_dbs,
                    "table_patterns": table_patterns,
                    "ignore_tables": ignore_tables,
                }
            ],
        },
    }
