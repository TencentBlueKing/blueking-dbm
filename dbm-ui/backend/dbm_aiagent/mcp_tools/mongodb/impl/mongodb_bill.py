# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

NOTE: details 结构须与正式部署单据 builder 保持一致，改动时两边一起改：
  - ticket/builders/mongodb/mongo_replicaset_apply.py
  - ticket/builders/mongodb/mongo_shard_apply.py
"""
from typing import Any, Dict, Iterable, List, Optional

from django.db.models import Q

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_meta.models import Spec
from backend.db_services.dbbase.constants import IpSource
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

_MONGO_SPEC_MACHINE_TYPES = (
    SpecMachineType.MONGODB.value,
    SpecMachineType.MONOG_CONFIG.value,
    SpecMachineType.MONGOS.value,
)
_MCP_DESC_MARK = "mcp_allow"


def _mcp_allowed_spec_queryset(machine_type: str = ""):
    """启用中、备注(desc)含 mcp_allow（大小写不敏感）的 MongoDB 规格。"""
    qs = Spec.objects.filter(
        spec_cluster_type=DBType.MongoDB.value,
        enable=True,
        spec_machine_type__in=_MONGO_SPEC_MACHINE_TYPES,
    ).filter(Q(desc__icontains=_MCP_DESC_MARK))
    mt = (machine_type or "").strip()
    if mt:
        qs = qs.filter(spec_machine_type=mt)
    return qs


def filter_disallowed_spec_ids(spec_ids: Iterable[int]) -> List[int]:
    """返回不在 mcp_allow 白名单内的 spec_id，供创单前校验。"""
    wanted = {int(spec_id) for spec_id in spec_ids if spec_id is not None}
    if not wanted:
        return []
    allowed = set(_mcp_allowed_spec_queryset().filter(spec_id__in=wanted).values_list("spec_id", flat=True))
    return sorted(wanted - allowed)


def list_mongodb_specs(machine_type: str = "") -> Dict:
    """
    列出启用中、备注(desc)含 mcp_allow（大小写不敏感）的 MongoDB 规格。
    仅返回白名单备注规格，避免名称混乱时全表瞎选。
    """
    qs = _mcp_allowed_spec_queryset(machine_type)

    results = []
    for s in qs.order_by("spec_machine_type", "spec_id"):
        info = s.get_spec_info()
        results.append(
            {
                "spec_id": s.spec_id,
                "spec_name": s.spec_name,
                "machine_type": s.spec_machine_type,
                "cpu": info.get("cpu") or {},
                "mem": info.get("mem") or {},
                "device_class": info.get("device_class") or [],
                "storage_spec": info.get("storage_spec") or [],
                "desc": s.desc or "",
            }
        )
    return {"results": results, "count": len(results)}


def submit_mongodb_replicaset_apply_bill(
    bk_biz_id: int,
    bk_cloud_id: int,
    db_app_abbr: str,
    db_version: str,
    start_port: int,
    replica_count: int,
    node_count: int,
    node_replica_count: int,
    replica_sets: List[Dict[str, Any]],
    spec_id: int,
    oplog_percent: int,
    ip_source: str,
    city_code: str = "default",
    disaster_tolerance_level: str = "NONE",
    resource_spec: Optional[Dict] = None,
    nodes: Optional[Dict] = None,
    creator: str = "mcp_user",
) -> Dict:
    """提交 MongoDB 副本集集群部署单据。"""
    details: Dict[str, Any] = {
        "bk_cloud_id": bk_cloud_id,
        "db_app_abbr": db_app_abbr,
        "city_code": city_code or "default",
        "disaster_tolerance_level": disaster_tolerance_level,
        "cluster_type": ClusterType.MongoReplicaSet.value,
        "db_version": db_version,
        "start_port": start_port,
        "replica_count": replica_count,
        "node_count": node_count,
        "node_replica_count": node_replica_count,
        "replica_sets": replica_sets,
        "spec_id": spec_id,
        "oplog_percent": oplog_percent,
        "ip_source": ip_source,
    }
    if ip_source == IpSource.RESOURCE_POOL.value:
        details["resource_spec"] = resource_spec or {"mongo_machine_set": {"spec_id": spec_id, "count": node_count}}
    if nodes is not None:
        details["nodes"] = nodes

    tk = Ticket.create_ticket(
        bk_biz_id=bk_biz_id,
        ticket_type=TicketType.MONGODB_REPLICASET_APPLY,
        creator=creator,
        helpers=[],
        remark="mcp mongodb replicaset apply ticket",
        details=details,
    )
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_mongodb_shard_apply_bill(
    bk_biz_id: int,
    bk_cloud_id: int,
    db_app_abbr: str,
    cluster_name: str,
    db_version: str,
    start_port: int,
    oplog_percent: int,
    shard_machine_group: int,
    shard_num: int,
    ip_source: str,
    resource_spec: Optional[Dict] = None,
    cluster_alias: str = "",
    city_code: str = "default",
    disaster_tolerance_level: str = "NONE",
    nodes: Optional[Dict] = None,
    creator: str = "mcp_user",
) -> Dict:
    """提交 MongoDB 分片集群部署单据。"""
    details: Dict[str, Any] = {
        "bk_cloud_id": bk_cloud_id,
        "db_app_abbr": db_app_abbr,
        "city_code": city_code or "default",
        "disaster_tolerance_level": disaster_tolerance_level,
        "cluster_type": ClusterType.MongoShardedCluster.value,
        "cluster_name": cluster_name,
        "cluster_alias": cluster_alias or "",
        "db_version": db_version,
        "start_port": start_port,
        "oplog_percent": oplog_percent,
        "ip_source": ip_source,
        "shard_machine_group": shard_machine_group,
        "shard_num": shard_num,
    }
    if ip_source == IpSource.RESOURCE_POOL.value:
        details["resource_spec"] = resource_spec or {}
    if nodes is not None:
        details["nodes"] = nodes

    tk = Ticket.create_ticket(
        bk_biz_id=bk_biz_id,
        ticket_type=TicketType.MONGODB_SHARD_APPLY,
        creator=creator,
        helpers=[],
        remark="mcp mongodb shard apply ticket",
        details=details,
    )
    return {"bill_id": tk.pk, "bill_url": tk.url}
