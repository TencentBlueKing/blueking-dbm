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
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.configuration.constants import AffinityEnum
from backend.constants import INT_MAX
from backend.db_dirty.constants import MachineEventType
from backend.db_dirty.models import MachineEvent
from backend.db_meta.models import AppCache, Cluster, Machine, Spec, StorageInstance, Tag
from backend.ticket.builders.common.base import fetch_apply_hosts
from backend.ticket.constants import ResourceApplyErrCode

logger = logging.getLogger("flow")

DEFAULT_SPEC = {
    "id": 0,
    "name": "",
    "cpu": "",
    "mem": "",
    "qps": "",
    "device_class": "",
    "storage_spec": "",
}


@dataclass
class ApplyExerciseResourcesResult:
    success: bool
    skipped_idempotent: bool = False
    resource_request_id: str = ""
    node_infos: Dict[str, List] = field(default_factory=dict)
    resource_apply_summary: List[Dict] = field(default_factory=list)
    error_message: str = ""


def all_infos_have_redis(infos: List[dict]) -> bool:
    return bool(infos) and all(info.get("redis") for info in infos)


def info_has_applied_redis(info: Optional[dict]) -> bool:
    if not info:
        return False
    redis_hosts = info.get("redis") or []
    return len(redis_hosts) == 1


def get_effective_drill_infos(global_data: dict, trans_data=None) -> List[dict]:
    """Return drill infos with applied hosts.

    Sub-processes receive a build-time snapshot of ``global_data`` that does not
    include hosts assigned by the resource-apply act. Prefer ``trans_data.applied_infos``
    when present.
    """
    if trans_data is not None:
        applied_infos = getattr(trans_data, "applied_infos", None)
        if applied_infos:
            return applied_infos
    return global_data.get("infos") or []


def get_instance_machine(info: dict, cluster: Cluster) -> Optional[Machine]:
    instance = (
        StorageInstance.objects.filter(
            cluster=cluster,
            machine__ip=info["instance_ip"],
            port=info["instance_port"],
        )
        .select_related("machine")
        .first()
    )
    if instance:
        return instance.machine
    return Machine.objects.filter(ip=info["instance_ip"], bk_cloud_id=cluster.bk_cloud_id).first()


def _resolve_mem_min_gb(machine: Machine) -> int:
    """Return minimum memory (GB) from machine spec_config with Spec fallback.

    ``spec_config.mem`` / ``Spec.mem`` use GB, consistent with
    ``Spec._get_apply_params_detail`` (GB -> MB via ``* 1024`` for resource pool).
    """
    spec_config = machine.spec_config or {}
    mem_info = spec_config.get("mem") or {}
    mem_min_gb = int(mem_info.get("min") or 0)

    if not mem_min_gb and machine.spec_id:
        try:
            spec = Spec.objects.get(spec_id=machine.spec_id)
            mem_min_gb = int(spec.mem.get("min") or 1)
        except Spec.DoesNotExist:
            pass

    if not mem_min_gb and getattr(machine, "mem", 0):
        mem_min_gb = int(machine.mem)

    return max(mem_min_gb, 1)


def _build_storage_spec(machine: Machine) -> List[dict]:
    storage_spec = []
    for mount_point, disk in (machine.storage_device or {}).items():
        size = disk.get("size")
        if size is None:
            continue
        storage_spec.append(
            {
                "mount_point": mount_point,
                "disk_type": "",
                "min": int(size),
                "max": INT_MAX,
            }
        )

    if storage_spec:
        return storage_spec

    spec_config = machine.spec_config or {}
    for item in spec_config.get("storage_spec") or []:
        mount_point = item.get("mount_point")
        spec_item = {
            "disk_type": "",
            "min": int(item.get("min") or 0),
            "max": INT_MAX,
        }
        if mount_point:
            spec_item["mount_point"] = mount_point
        storage_spec.append(spec_item)

    if storage_spec:
        return storage_spec

    return [{"disk_type": "", "min": 1, "max": INT_MAX}]


def _build_location_spec(region: str) -> dict:
    """Random region ('default') means no city filter, aligned with Spec._get_apply_params_detail."""
    city = region or ""
    if city == "default":
        city = ""
    return {"city": city, "sub_zone_ids": []}


def build_apply_detail_from_machine(index: int, cluster: Cluster, machine: Machine) -> dict:
    mem_min_gb = _resolve_mem_min_gb(machine)
    return {
        "group_mark": f"{index}_redis",
        "bk_cloud_id": cluster.bk_cloud_id,
        "count": 1,
        "affinity": AffinityEnum.NONE.value,
        "location_spec": _build_location_spec(cluster.region),
        "spec": {
            # Drill only constrains memory; CPU is unconstrained (0/0 = empty spec in db-resource).
            "cpu": {"min": 0, "max": 0},
            "ram": {"min": int(mem_min_gb * 1024), "max": INT_MAX},
        },
        "storage_spec": _build_storage_spec(machine),
    }


def format_resource_hosts(hosts, biz_name_map, label_name_map) -> List[dict]:
    return [
        {
            "bk_biz_id": host.get("bk_biz_id", 0),
            "ip": host["ip"],
            "bk_cloud_id": host["bk_cloud_id"],
            "host_id": host["bk_host_id"],
            "bk_host_id": host["bk_host_id"],
            "bk_idc_id": host.get("idc_id"),
            "bk_cpu": host["cpu_num"],
            "bk_disk": host["total_storage_cap"],
            "bk_mem": host["dram_cap"],
            "os_name": host["os_name"],
            "os_type": host["os_type"],
            "storage_device": host["storage_device"],
            "city": host.get("city"),
            "sub_zone": host.get("sub_zone"),
            "sub_zone_id": host.get("sub_zone_id"),
            "rack_id": host.get("rack_id"),
            "device_class": host.get("device_class"),
            "bk_svr_device_cls_name": host.get("bk_svr_device_cls_name") or host.get("device_class") or "",
            "for_biz": host["dedicated_biz"],
            "labels": host["labels"],
            "for_biz_info": {
                "bk_biz_id": host["dedicated_biz"],
                "bk_biz_name": biz_name_map.get(host["dedicated_biz"]),
            },
            "label_info": [
                {"id": int(label_id), "name": label_name_map.get(int(label_id), "")} for label_id in host["labels"]
            ],
            "resource_type": host["rs_type"],
            "spec": DEFAULT_SPEC,
        }
        for host in hosts
    ]


def build_drill_resource_spec(machine: Machine, host_count: int = 1) -> dict:
    """Build the resource_spec block expected by RedisDataStructureFlow."""
    redis_spec = dict(machine.spec_config or {})
    if machine.spec_id:
        redis_spec["id"] = machine.spec_id
    redis_spec.setdefault("id", 0)
    redis_spec["count"] = host_count
    return {"redis": redis_spec}


def build_resource_apply_summary(info: dict, cluster: Cluster, host: dict) -> dict:
    return {
        "cluster_id": cluster.id,
        "cluster_domain": cluster.immute_domain,
        "instance_ip": info.get("instance_ip"),
        "instance_port": info.get("instance_port"),
        "applied_ip": host.get("ip"),
        "applied_bk_host_id": host.get("bk_host_id"),
        "region": host.get("city") or cluster.region,
        "sub_zone": host.get("sub_zone"),
        "cpu": host.get("bk_cpu"),
        "mem_mb": host.get("bk_mem"),
        "storage_device": host.get("storage_device"),
        "device_class": host.get("device_class"),
    }


def apply_exercise_resources(ticket_data: dict, root_id: str) -> ApplyExerciseResourcesResult:
    infos = ticket_data.get("infos") or []
    if all_infos_have_redis(infos):
        return ApplyExerciseResourcesResult(success=True, skipped_idempotent=True)

    apply_details = []
    cluster_map = {}
    for index, info in enumerate(infos):
        try:
            cluster = Cluster.objects.get(id=info["cluster_id"])
        except Cluster.DoesNotExist:
            return ApplyExerciseResourcesResult(
                success=False,
                error_message=_("集群 {} 不存在").format(info["cluster_id"]),
            )
        cluster_map[index] = cluster
        machine = get_instance_machine(info, cluster)
        if machine is None:
            return ApplyExerciseResourcesResult(
                success=False,
                error_message=_("实例 {}:{} 机器不存在").format(info.get("instance_ip"), info.get("instance_port")),
            )
        apply_details.append(build_apply_detail_from_machine(index, cluster, machine))

    if not apply_details:
        return ApplyExerciseResourcesResult(success=False, error_message=_("无有效资源申请项"))

    apply_params = {
        "for_biz_id": ticket_data["bk_biz_id"],
        "resource_type": "redis",
        "bill_id": str(ticket_data.get("uid", root_id)),
        "bill_type": ticket_data.get("ticket_type", ""),
        "task_id": root_id,
        "operator": ticket_data.get("created_by", "system"),
        "details": apply_details,
    }

    resp = DBResourceApi.resource_apply(params=apply_params, raw=True)
    if resp.get("code") != 0:
        err_code = resp.get("code")
        if err_code in ResourceApplyErrCode.get_values():
            err_label = ResourceApplyErrCode.get_choice_label(err_code)
            message = _("资源池服务错误 [{}]: {}").format(err_label, resp.get("message", ""))
        else:
            message = _("资源申请失败 [{}]: {}").format(err_code, resp.get("message", ""))
        return ApplyExerciseResourcesResult(success=False, error_message=message)

    resource_request_id = resp.get("request_id", "")
    apply_data = resp.get("data") or []
    for_biz_ids = [item["dedicated_biz"] for info in apply_data for item in info["data"]]
    biz_name_map = AppCache.batch_get_app_attr(bk_biz_ids=for_biz_ids, attr_name="bk_biz_name")
    label_ids = [int(label) for info in apply_data for item in info["data"] for label in item["labels"]]
    label_name_map = {tag.id: tag.value for tag in Tag.objects.filter(id__in=label_ids)}

    node_infos: Dict[str, List] = defaultdict(list)
    resource_apply_summary: List[dict] = []
    for info in apply_data:
        role = info["item"]
        host_infos = format_resource_hosts(info["data"], biz_name_map, label_name_map)
        node_infos[role].extend(host_infos)

    for index, info in enumerate(infos):
        hosts = node_infos.get(f"{index}_redis") or []
        if len(hosts) != 1:
            return ApplyExerciseResourcesResult(
                success=False,
                resource_request_id=resource_request_id,
                node_infos=dict(node_infos),
                error_message=_("资源申请结果异常: index={}, hosts={}").format(index, hosts),
            )
        info["redis"] = hosts
        cluster = cluster_map[index]
        resource_apply_summary.append(build_resource_apply_summary(info, cluster, hosts[0]))

    applied_host_infos = fetch_apply_hosts({"nodes": node_infos})
    ticket = None
    ticket_id = ticket_data.get("uid")
    if ticket_id:
        from backend.ticket.models import Ticket

        ticket = Ticket.objects.filter(id=ticket_id).first()

    MachineEvent.host_event_trigger(
        ticket_data["bk_biz_id"],
        applied_host_infos,
        event=MachineEventType.ApplyResource,
        operator=ticket_data.get("created_by", "system"),
        ticket=ticket,
    )

    return ApplyExerciseResourcesResult(
        success=True,
        resource_request_id=resource_request_id,
        node_infos=dict(node_infos),
        resource_apply_summary=resource_apply_summary,
    )
