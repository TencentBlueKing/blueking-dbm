"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy
import logging
import re
import time
from collections import defaultdict
from typing import Dict, List

from django.db.models import F
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, ProxyInstance, StorageInstance

logger = logging.getLogger("root")

# 用于从 TS 指标查询 meta 的 unify_query 模板（instant）
_UNIFY_QUERY_META_PARAMS = {
    "bk_biz_id": 3,
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    "start_time": 0,
    "end_time": 0,
    "slimit": 500,
    "type": "instant",
}


def mongodb_list_clusters(bk_biz_id: int) -> List:
    clusters = Cluster.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
        bk_biz_id=bk_biz_id,
        cluster_type__in=[ClusterType.MongoReplicaSet, ClusterType.MongoShardedCluster],
    )
    result = []
    for c in clusters:
        mongos_count = c.proxyinstance_set.filter(machine_type=MachineType.MONGOS).count()
        storage_count = c.storageinstance_set.count()
        shard_count = 0
        if c.cluster_type == ClusterType.MongoShardedCluster:
            shard_count = (
                c.nosqlstoragesetdtl_set.filter(instance__machine__machine_type=MachineType.MONGODB)
                .values("seg_range")
                .distinct()
                .count()
            )
        elif c.cluster_type == ClusterType.MongoReplicaSet:
            shard_count = 1
        result.append(
            {
                "cluster_id": c.id,
                "bk_cloud_id": c.bk_cloud_id,
                "cluster_type": c.cluster_type,
                "immute_domain": c.immute_domain,
                "alias": c.alias,
                "region": c.region,
                "mongos_count": mongos_count,
                "shard_count": shard_count,
                "storage_count": storage_count,
                "mongodb_version": c.major_version,
            }
        )
    return result


def get_machine_stats(all_machine_ids) -> Dict:
    machines = Machine.objects.filter(bk_host_id__in=all_machine_ids).select_related("bk_city")
    machine_distribution = {
        "total_count": len(all_machine_ids),
        "by_sub_zone": defaultdict(int),
        "by_os": defaultdict(int),
        "by_device_class": defaultdict(int),
        "spec_summary": defaultdict(int),
    }
    for machine in machines:
        if machine.bk_sub_zone:
            machine_distribution["by_sub_zone"][machine.bk_sub_zone] += 1
        if machine.bk_os_name:
            machine_distribution["by_os"][machine.bk_os_name] += 1
        if machine.bk_svr_device_cls_name:
            machine_distribution["by_device_class"][machine.bk_svr_device_cls_name] += 1
        if machine.spec_id:
            machine_distribution["spec_summary"][f"spec_{machine.spec_id}"] += 1
    return machine_distribution


def get_mongodb_meta_from_ts_metric(conds: Dict) -> Dict:
    """
    从监控指标 bkmonitor:dbm_system:cpu_summary:usage 的 label 发现实例。
    返回字段：cluster_domain / cluster_type / instance / instance_role / shard。

    conds 支持：
        - cluster_domain: 集群域名
        - ip: 主机 IP
        - instance_port: 可选，与 ip 一起过滤端口
    """
    group_by_keys = [
        "cluster_domain",
        "bk_target_ip",
        "instance_role",
        "shard",
        "instance_port",
        "cluster_type",
        "instance_host",
        "instance",
    ]
    label_filters = []
    if conds.get("cluster_domain"):
        label_filters.append(f'cluster_domain="{conds["cluster_domain"]}"')
    if conds.get("ip"):
        label_filters.append(f'bk_target_ip="{conds["ip"]}"')
    if conds.get("instance_port"):
        label_filters.append(f'instance_port="{conds["instance_port"]}"')
    label_str = ",".join(label_filters) if label_filters else ""
    promql = (
        f'max by ({",".join(group_by_keys)}) '
        f"(max_over_time(bkmonitor:dbm_system:cpu_summary:usage{{{label_str}}}[5m]))"
    )
    params = copy.deepcopy(_UNIFY_QUERY_META_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    end_ts = int(time.time())
    params["start_time"] = end_ts - 300
    params["end_time"] = end_ts
    params["query_configs"][0]["promql"] = promql

    try:
        resp = BKMonitorV3Api.unify_query(params)
    except Exception as e:
        logger.exception("get_mongodb_meta_from_ts_metric unify_query error: %s", e)
        return {"meta_list": [], "error": str(e)}

    series = resp.get("series", [])
    meta_list = []

    for s in series:
        dims = s.get("dimensions") or s.get("group_keys") or s.get("metric") or {}
        bk_target_ip = dims.get("bk_target_ip") or ""
        instance_port = dims.get("instance_port") or ""
        instance = dims.get("instance") or (
            f"{bk_target_ip}:{instance_port}" if bk_target_ip and instance_port else bk_target_ip
        )
        meta_list.append(
            {
                "cluster_domain": dims.get("cluster_domain") or "",
                "cluster_type": dims.get("cluster_type") or "",
                "instance": instance,
                "instance_role": dims.get("instance_role") or "",
                "shard": dims.get("shard") or "",
            }
        )

    return {"meta_list": meta_list, "error": ""}


def meta_info(target: str) -> Dict:
    """
    从监控时序（TSDB）label 发现实例元信息（非 DBM ORM）。
    指标：bkmonitor:dbm_system:cpu_summary:usage。

    target 支持：
        - IP：如 "x.x.x.x"
        - IP:PORT：如 "x.x.x.x:50005"
        - 集群域名：如 "mongo.xxx.app.db"（含点号）
    """
    try:
        conds = {}
        if target is None:
            return {"meta_list": [], "error": "target is required"}
        target = (target or "").strip()
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target):
            conds["ip"] = target
        elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$", target):
            ip, port = target.split(":", 1)
            conds["ip"] = ip
            conds["instance_port"] = port
        elif "." in target:
            conds["cluster_domain"] = target
        else:
            return {"meta_list": [], "error": "target must be IP, IP:PORT, or cluster domain"}
        return get_mongodb_meta_from_ts_metric(conds)
    except Exception as e:
        return {"meta_list": [], "error": f"查询 MongoDB 实例的元数据信息时出错: {str(e)}"}


def _get_cluster_by_domain(immute_domain: str, prefetch_tags: bool = False) -> Cluster:
    """按域名取集群，不存在时抛 400 而不是 500。"""
    qs = Cluster.objects.prefetch_related("tags") if prefetch_tags else Cluster.objects
    try:
        return qs.get(immute_domain=immute_domain)
    except Cluster.DoesNotExist:
        raise ValidationError(_("集群域名不存在: {}").format(immute_domain))


def cluster_overview(immute_domain: str) -> Dict:
    cluster_obj = _get_cluster_by_domain(immute_domain, prefetch_tags=True)
    stats = {
        "bk_cloud_id": cluster_obj.bk_cloud_id,
        "bk_biz_id": cluster_obj.bk_biz_id,
        "cluster_id": cluster_obj.id,
        "immute_domain": cluster_obj.immute_domain,
        "alias": cluster_obj.alias,
        "cluster_type": cluster_obj.cluster_type,
        "major_version": cluster_obj.major_version,
        "region": cluster_obj.region,
        "disaster_tolerance_level": cluster_obj.disaster_tolerance_level,
        "tags": ["{}:{}".format(tag.key, tag.value) for tag in cluster_obj.tags.all()],
        "cluster_entries": [
            {"entry_type": ce.cluster_entry_type, "entry_addr": ce.entry}
            for ce in ClusterEntry.objects.filter(cluster=cluster_obj)
        ],
    }
    storage_instances = (
        StorageInstance.objects.filter(cluster=cluster_obj)
        .select_related("machine", "machine__bk_city")
        .prefetch_related("bind_entry")
    )
    proxy_instances = (
        ProxyInstance.objects.filter(cluster=cluster_obj)
        .select_related("machine", "machine__bk_city")
        .prefetch_related("bind_entry")
    )
    storage_stats = {
        "by_role": defaultdict(int),
        "by_status": defaultdict(int),
        "by_machine_type": defaultdict(int),
        "versions": set(),
        "machines": set(),
    }
    for instance in storage_instances:
        storage_stats["by_role"][instance.instance_role or instance.machine.machine_type] += 1
        storage_stats["by_status"][instance.status] += 1
        storage_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            storage_stats["versions"].add(instance.version)
        storage_stats["machines"].add(instance.machine.bk_host_id)
    storage_machines = get_machine_stats(storage_stats["machines"])
    stats["storage_instances"] = {
        "node_count": storage_instances.count(),
        "by_role": dict(sorted(storage_stats["by_role"].items())),
        "by_status": dict(sorted(storage_stats["by_status"].items())),
        "versions": sorted(list(storage_stats["versions"])),
        "machine_count": len(storage_stats["machines"]),
        "by_os": dict(sorted(storage_machines["by_os"].items())),
        "by_sub_zone": dict(sorted(storage_machines["by_sub_zone"].items())),
        "by_device_class": dict(sorted(storage_machines["by_device_class"].items())),
    }
    proxy_stats = {
        "by_status": defaultdict(int),
        "by_machine_type": defaultdict(int),
        "versions": set(),
        "machines": set(),
    }
    for instance in proxy_instances:
        proxy_stats["by_status"][instance.status] += 1
        proxy_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            proxy_stats["versions"].add(instance.version)
        proxy_stats["machines"].add(instance.machine.bk_host_id)
    proxy_machines = get_machine_stats(proxy_stats["machines"])
    stats["proxy_instances"] = {
        "node_count": proxy_instances.count(),
        "by_status": dict(sorted(proxy_stats["by_status"].items())),
        "versions": sorted(list(proxy_stats["versions"])),
        "machine_count": len(proxy_stats["machines"]),
        "by_os": dict(sorted(proxy_machines["by_os"].items())),
        "by_sub_zone": dict(sorted(proxy_machines["by_sub_zone"].items())),
        "by_device_class": dict(sorted(proxy_machines["by_device_class"].items())),
    }
    return stats


def cluster_mongos(immute_domain: str) -> List:
    """集群 Mongos 列表（按实例一行，字段与 list_shards 对齐）。"""
    c_obj = _get_cluster_by_domain(immute_domain)
    mongos_instances = c_obj.proxyinstance_set.filter(machine_type=MachineType.MONGOS).select_related("machine")
    result = [
        {
            "address": "{}:{}".format(s.machine.ip, s.port),
            "instance_role": s.machine_type or MachineType.MONGOS.value,
            "status": s.status,
            "version": s.version or "",
            "sub_zone": s.machine.bk_sub_zone or "",
            "cls_name": s.machine.bk_svr_device_cls_name or "",
        }
        for s in mongos_instances
    ]
    result.sort(key=lambda item: item["address"])
    return result


def cluster_shards(immute_domain: str) -> List:
    """
    集群 MongoDB storage 实例清单（按实例一行）。
    shard 取自 NosqlStorageSetDtl.seg_range；副本集无明细时回退为集群域名。
    """
    c_obj = _get_cluster_by_domain(immute_domain)
    storages = c_obj.storageinstance_set.filter(machine_type=MachineType.MONGODB).select_related("machine")
    instance_to_seg = {dtl.instance_id: dtl.seg_range for dtl in c_obj.nosqlstoragesetdtl_set.all()}
    result = []
    for s in storages:
        result.append(
            {
                "shard": instance_to_seg.get(s.id) or c_obj.immute_domain,
                "address": "{}:{}".format(s.machine.ip, s.port),
                "instance_role": s.instance_role or "",
                "status": s.status,
                "version": s.version or "",
                "sub_zone": s.machine.bk_sub_zone or "",
                "cls_name": s.machine.bk_svr_device_cls_name or "",
            }
        )
    result.sort(key=lambda item: (item["shard"], item["instance_role"], item["address"]))
    return result


def list_clusters_by_hosts(hosts: List) -> List[Dict]:
    cluster_host = []
    storage_data = (
        Cluster.objects.filter(storageinstance__machine__ip__in=hosts)
        .values(
            "immute_domain",
            host=F("storageinstance__machine__ip"),
            instance_role=F("storageinstance__instance_role"),
        )
        .distinct()
    )
    cluster_host.extend(list(storage_data))
    proxy_data = (
        Cluster.objects.filter(proxyinstance__machine__ip__in=hosts)
        .values(
            "immute_domain",
            host=F("proxyinstance__machine__ip"),
            instance_role=F("proxyinstance__machine_type"),
        )
        .distinct()
    )
    cluster_host.extend(list(proxy_data))
    seen = set()
    unique_results = []
    for item in cluster_host:
        key = (item["immute_domain"], item["host"], str(item.get("instance_role", "")))
        if key not in seen:
            seen.add(key)
            unique_results.append(item)
    return unique_results
