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
import time
from typing import Callable, List, Optional, Tuple

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple

ProgressCallback = Optional[Callable[[str], None]]


def emit_progress(progress_callback: ProgressCallback, message: str):
    if progress_callback:
        progress_callback(message)


class StageTimer:
    """阶段开始/完成日志，附带数量和耗时。"""

    def __init__(self, progress_callback: ProgressCallback, stage_name: str, count: Optional[int] = None):
        self.progress_callback = progress_callback
        self.stage_name = stage_name
        self.count = count
        self._started = time.monotonic()
        count_part = f", count={count}" if count is not None else ""
        emit_progress(progress_callback, f"[start] {stage_name}{count_part}")

    def done(self, skipped: Optional[int] = None, created: Optional[int] = None):
        elapsed = time.monotonic() - self._started
        parts = [f"[done] {self.stage_name}", f"elapsed={elapsed:.2f}s"]
        if self.count is not None:
            parts.append(f"count={self.count}")
        if skipped is not None:
            parts.append(f"skipped={skipped}")
        if created is not None:
            parts.append(f"created={created}")
        emit_progress(self.progress_callback, ", ".join(parts))


def _storage_key(ip: str, port: int, bk_cloud_id: int) -> Tuple[str, int, int]:
    return ip, int(port), int(bk_cloud_id)


def _belongs_only_to_allowed_cluster(instance, allowed_cluster_id: Optional[int], cluster_name: str = "") -> bool:
    """
    实例只挂在允许复用的本次集群上，或未挂集群但 name 就是本次集群名。
    未绑定且 name 为空或其他集群名时拒绝，避免被另一次部署收走。
    """
    cluster_ids = list(instance.cluster.values_list("id", flat=True))
    if not cluster_ids:
        return bool(cluster_name) and instance.name == cluster_name
    if allowed_cluster_id is not None and cluster_ids == [allowed_cluster_id]:
        return True
    return False


def partition_proxy_inputs(
    proxies: List[dict],
    bk_cloud_id: int,
    allowed_cluster_id: Optional[int] = None,
    cluster_name: str = "",
) -> Tuple[List[dict], List[ProxyInstance], List[str]]:
    """
    拆分 mongos：缺失待创建 / 可复用 / 冲突。
    可复用：只挂在 allowed_cluster_id，或未挂集群且 name 等于本次集群名。
    冲突：已挂到其他集群，或未绑定但不属于本次集群名。
    """
    missing, reusable, conflicts = [], [], []
    for proxy in proxies:
        existing = ProxyInstance.objects.filter(
            machine__ip=proxy["ip"], port=proxy["port"], machine__bk_cloud_id=bk_cloud_id
        ).first()
        if not existing:
            missing.append(proxy)
            continue
        if not _belongs_only_to_allowed_cluster(existing, allowed_cluster_id, cluster_name):
            conflicts.append("{}:{} already belongs to another cluster".format(proxy["ip"], proxy["port"]))
            continue
        reusable.append(existing)
    return missing, reusable, conflicts


def partition_storage_inputs(
    storages: List[dict],
    bk_cloud_id: int,
    allowed_cluster_id: Optional[int] = None,
    cluster_name: str = "",
) -> Tuple[List[dict], List[StorageInstance], List[str]]:
    """
    拆分 storage 节点列表（flat）：缺失 / 可复用 / 冲突。
    storage 项至少含 ip/port，可选 role。
    """
    missing, reusable, conflicts = [], [], []
    for storage in storages:
        existing = StorageInstance.objects.filter(
            machine__ip=storage["ip"], port=storage["port"], machine__bk_cloud_id=bk_cloud_id
        ).first()
        if not existing:
            missing.append(storage)
            continue
        if not _belongs_only_to_allowed_cluster(existing, allowed_cluster_id, cluster_name):
            conflicts.append("{}:{} already belongs to another cluster".format(storage["ip"], storage["port"]))
            continue
        reusable.append(existing)
    return missing, reusable, conflicts


def partition_shard_pairs(
    inst_pairs: List[dict],
    bk_cloud_id: int,
    allowed_cluster_id: Optional[int] = None,
    cluster_name: str = "",
) -> Tuple[List[dict], List[StorageInstance], List[str]]:
    """
    拆分 shard/config 结构 [{"shard":..., "nodes":[...]}]。
    返回仍需创建的 pairs（仅含缺失节点）、已可复用实例、冲突信息。
    """
    missing_pairs = []
    reusable = []
    conflicts = []
    for pair in inst_pairs:
        missing_nodes = []
        for node in pair["nodes"]:
            existing = StorageInstance.objects.filter(
                machine__ip=node["ip"], port=node["port"], machine__bk_cloud_id=bk_cloud_id
            ).first()
            if not existing:
                missing_nodes.append(node)
                continue
            if not _belongs_only_to_allowed_cluster(existing, allowed_cluster_id, cluster_name):
                conflicts.append("{}:{} already belongs to another cluster".format(node["ip"], node["port"]))
                continue
            reusable.append(existing)
        if missing_nodes:
            missing_pairs.append({"shard": pair.get("shard", ""), "nodes": missing_nodes})
    return missing_pairs, reusable, conflicts


def ensure_storage_tuples(nodes: List[dict], role_key: str = "role", bk_cloud_id: Optional[int] = None):
    """
    按 MONGO_M1 为主，补齐缺失的 StorageInstanceTuple。
    nodes: [{"ip","port","role"}, ...]
    """
    from backend.db_meta.enums import InstanceRole

    primary = None
    for node in nodes:
        if node[role_key] == InstanceRole.MONGO_M1:
            primary = node
            break
    if not primary:
        return

    primary_filter = {"machine__ip": primary["ip"], "port": primary["port"]}
    if bk_cloud_id is not None:
        primary_filter["machine__bk_cloud_id"] = bk_cloud_id
    primary_obj = StorageInstance.objects.get(**primary_filter)
    for node in nodes:
        if node[role_key] == InstanceRole.MONGO_M1:
            continue
        receiver_filter = {"machine__ip": node["ip"], "port": node["port"]}
        if bk_cloud_id is not None:
            receiver_filter["machine__bk_cloud_id"] = bk_cloud_id
        receiver_obj = StorageInstance.objects.get(**receiver_filter)
        StorageInstanceTuple.objects.get_or_create(ejector=primary_obj, receiver=receiver_obj)


def _instance_keys(instances) -> set:
    return {(ins.machine.ip, ins.port, ins.machine.bk_cloud_id) for ins in instances}


def _require_exact_instance_keys(name: str, kind: str, instances, expected: Optional[set]):
    """请求给出了实例集合时必须完全一致。空集合和子集都不能续跑。"""
    if expected is None:
        return
    actual = _instance_keys(instances)
    if actual != expected:
        raise Exception("Cluster {} {} instances do not match request".format(name, kind))


def find_reusable_cluster(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    cluster_type: str,
    expected_storage_keys: Optional[set] = None,
    expected_proxy_keys: Optional[set] = None,
) -> Optional[Cluster]:
    """
    查找本次可继续完成的集群。
    只继续 phase=offline、域名一致、且实例集合与请求完全一致的集群。
    已经 online、实例为空、或只是请求子集的同名集群直接拒绝。
    """
    cluster = Cluster.objects.filter(bk_biz_id=bk_biz_id, name=name, cluster_type=cluster_type).first()
    if not cluster:
        # Domain taken by another cluster name?
        domain_owner = Cluster.objects.filter(immute_domain=immute_domain).first()
        if domain_owner:
            raise Exception("Cluster domain {} already exists on cluster {}".format(immute_domain, domain_owner.name))
        return None

    if cluster.immute_domain != immute_domain:
        raise Exception(
            "Cluster {} already exists with different domain {} <> {}".format(
                name, cluster.immute_domain, immute_domain
            )
        )

    if cluster.phase != ClusterPhase.OFFLINE.value:
        raise Exception(
            "Cluster {} already exists with phase {}, only an offline cluster can be resumed".format(
                name, cluster.phase
            )
        )

    _require_exact_instance_keys(name, "storage", cluster.storageinstance_set.all(), expected_storage_keys)
    _require_exact_instance_keys(name, "proxy", cluster.proxyinstance_set.all(), expected_proxy_keys)

    return cluster


def storage_instance_keys(storages: List[dict], bk_cloud_id: int) -> set:
    return {_storage_key(s["ip"], s["port"], bk_cloud_id) for s in storages}


def proxy_instance_keys(proxies: List[dict], bk_cloud_id: int) -> set:
    return {_storage_key(p["ip"], p["port"], bk_cloud_id) for p in proxies}


def get_storage_objs(nodes: List[dict], bk_cloud_id: int) -> List[StorageInstance]:
    objs = []
    for node in nodes:
        objs.append(
            StorageInstance.objects.get(machine__ip=node["ip"], port=node["port"], machine__bk_cloud_id=bk_cloud_id)
        )
    return objs


def get_proxy_objs(proxies: List[dict], bk_cloud_id: int) -> List[ProxyInstance]:
    objs = []
    for proxy in proxies:
        objs.append(
            ProxyInstance.objects.get(machine__ip=proxy["ip"], port=proxy["port"], machine__bk_cloud_id=bk_cloud_id)
        )
    return objs
