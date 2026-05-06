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

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import AppCache, Cluster, ClusterEntry, Machine, ProxyInstance, StorageInstance

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


def list_my_mongodb_bizs(username: str) -> List:
    res = []
    for app in AppCache.objects.all():  # pyright: ignore[reportAttributeAccessIssue]
        bk_biz_id = app.bk_biz_id
        if DBAdministrator.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
            bk_biz_id=bk_biz_id, users__0=username, db_type=DBType.MongoDB.value
        ).exists():
            res.append({"bk_biz_id": bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


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
    从监控指标 bkmonitor:dbm_system:cpu_summary:usage 的 label 中解析出 (cluster_domain, bk_target_ip, instance_role)，
    再用 DBM 元数据补全 cluster_name、cluster_id、port、bk_biz_id、app_name、shard 等。

    conds 支持：
        - cluster_domain: 集群域名，仅查询该集群
        - ip: 主机 IP，仅查询该 IP 上的实例
        - instance_port: 可选，与 ip 一起时过滤指定端口（通过 DBM 元数据过滤）
    """
    # mongodb_types = [ClusterType.MongoReplicaSet.value, ClusterType.MongoShardedCluster.value]
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
        cluster_domain = dims.get("cluster_domain")
        bk_target_ip = dims.get("bk_target_ip")
        instance_role = dims.get("instance_role", "")
        instance_port = dims.get("instance_port", "")
        instance = dims.get("instance", "") or f"{bk_target_ip}:{instance_port}"
        instance_host = dims.get("instance_host", "") or f"{bk_target_ip}"
        cluster_type = dims.get("cluster_type", "")
        shard = dims.get("shard", "")
        meta_list.append(
            {
                "cluster_domain": cluster_domain,
                "cluster_type": cluster_type,
                "bk_target_ip": bk_target_ip,
                "instance_port": instance_port,
                "instance_role": instance_role,
                "instance_host": instance_host,
                "instance": instance,
                "shard": shard,
            }
        )

    return {"meta_list": meta_list, "error": ""}


def meta_info(value: str) -> Dict:
    """
    根据输入的值，返回对应的元信息（从 TS 指标 bkmonitor:dbm_system:cpu_summary:usage 的 label 解析，再以 DBM 元数据补全）。

    value 支持：
        - IP：如 "x.x.x.x"
        - IP:PORT：如 "x.x.x.x:50005"
        - 集群域名：如 "mongo.xxx.app.db"（含点号）
    """
    try:
        conds = {}
        if value is None:
            return {"meta_list": [], "error": "value is None"}
        value = (value or "").strip()
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
            conds["ip"] = value
        elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$", value):
            ip, port = value.split(":", 1)
            conds["instance"] = f"{ip}:{port}"
        elif "." in value:
            conds["cluster_domain"] = value
        else:
            return {"meta_list": [], "error": "Invalid value"}
        return get_mongodb_meta_from_ts_metric(conds)
    except Exception as e:
        return {"meta_list": [], "error": f"查询 MongoDB 实例的元数据信息时出错: {str(e)}"}


def cluster_overview(immute_domain: str) -> Dict:
    cluster_obj = Cluster.objects.prefetch_related("tags").get(immute_domain=immute_domain)
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
    """集群 Mongos 列表"""
    c_obj = Cluster.objects.get(immute_domain=immute_domain)
    mongos_instances = c_obj.proxyinstance_set.filter(machine_type=MachineType.MONGOS)
    return [
        {
            "address": "{}:{}".format(s.machine.ip, s.port),
            "status": s.status,
            "version": s.version or "",
            "sub_zone": s.machine.bk_sub_zone or "",
            "cls_name": s.machine.bk_svr_device_cls_name or "",
        }
        for s in mongos_instances
    ]


def cluster_shards(immute_domain: str) -> List:
    """集群分片(Shard)节点列表，按 IP 聚合端口"""
    c_obj = Cluster.objects.get(immute_domain=immute_domain)
    storage_objs = c_obj.storageinstance_set.filter(machine_type=MachineType.MONGODB)
    host_ports = defaultdict(list)
    for ins in storage_objs:
        host_ports[ins.machine.ip].append(ins.port)
    result = []
    for ip, ports in host_ports.items():
        m_obj = Machine.objects.filter(ip=ip, bk_cloud_id=c_obj.bk_cloud_id, bk_biz_id=c_obj.bk_biz_id).first()
        if m_obj:
            result.append(
                {
                    "ip": ip,
                    "ports": ports,
                    "sub_zone": m_obj.bk_sub_zone or "",
                    "cls_name": m_obj.bk_svr_device_cls_name or "",
                }
            )
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
