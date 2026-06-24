# -*- coding: utf-8 -*-
"""
Resolve MongoDB instance-restart targets from infos[] (explicit instance / cluster_id / ip / instance).
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.enums.instance_status import MongoDBStorageInstanceStatus
from backend.db_meta.models import Cluster, MongoDBStorageInstanceExt, ProxyInstance, StorageInstance
from backend.flow.consts import MongoDBClusterRole, MongoDBManagerUser
from backend.flow.utils.mongodb.mongodb_password import MongoDBPassword
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoNode, MongoRepository

_MONGO_CLUSTER_TYPES = (ClusterType.MongoReplicaSet.value, ClusterType.MongoShardedCluster.value)

_META_ROLE_ORDER = [
    InstanceRole.MONGO_BACKUP.value,
    InstanceRole.MONGO_M1.value,
    InstanceRole.MONGO_M2.value,
    InstanceRole.MONGO_M3.value,
    InstanceRole.MONGO_M4.value,
    InstanceRole.MONGO_M5.value,
    InstanceRole.MONGO_M6.value,
    InstanceRole.MONGO_M7.value,
    InstanceRole.MONGO_M8.value,
    InstanceRole.MONGO_M9.value,
    InstanceRole.MONGO_M10.value,
]
_META_ROLE_INDEX = {role: idx for idx, role in enumerate(_META_ROLE_ORDER)}

_INSTANCE_ADDR_RE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$")

ROLLING_RESTART_TIMEOUT_SECONDS = 300

INFO_KIND_EXPLICIT = "explicit"
INFO_KIND_CLUSTER = "cluster"
INFO_KIND_IP = "ip"
INFO_KIND_INSTANCE = "instance"


@dataclass(frozen=True)
class RestartTargetNode:
    ip: str
    port: int
    role: str
    bk_cloud_id: int
    machine_type: str
    cluster_id: int
    cluster_type: str
    set_name: str
    rs_type: str
    is_mongos: bool

    @classmethod
    def from_mongo_node(
        cls,
        node: MongoNode,
        cluster_id: int,
        cluster_type: str,
        set_name: str = "",
        rs_type: str = "",
        is_mongos: bool = False,
    ) -> "RestartTargetNode":
        return cls(
            ip=node.ip,
            port=int(node.port),
            role=node.role,
            bk_cloud_id=node.bk_cloud_id,
            machine_type=node.machine_type,
            cluster_id=int(cluster_id),
            cluster_type=cluster_type,
            set_name=set_name or "",
            rs_type=rs_type or "",
            is_mongos=is_mongos,
        )

    def addr(self) -> str:
        return f"{self.ip}:{self.port}"

    def node_key(self) -> Tuple[int, str, int]:
        return self.bk_cloud_id, self.ip, self.port

    def to_mongo_node(self) -> MongoNode:
        return MongoNode(self.ip, self.port, self.role, self.bk_cloud_id, self.machine_type)


class InstanceRestartInfoSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(required=False)
    ip = serializers.CharField(required=False, allow_blank=True, default="")
    port = serializers.IntegerField(required=False)
    instance = serializers.CharField(required=False, allow_blank=True, default="")
    role = serializers.CharField(required=False, allow_blank=True, default="")
    bk_cloud_id = serializers.IntegerField(required=False)
    bk_host_id = serializers.IntegerField(required=False)
    instance_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        ip = (attrs.get("ip") or "").strip()
        instance = (attrs.get("instance") or "").strip()
        cluster_id = attrs.get("cluster_id")
        port = attrs.get("port")

        has_ip = bool(ip)
        has_port = port is not None
        has_cluster_id = cluster_id is not None
        has_instance = bool(instance)

        if has_ip and has_port and has_cluster_id:
            attrs["ip"] = ip
            attrs["info_kind"] = INFO_KIND_EXPLICIT
            return attrs

        if has_cluster_id and not has_ip and not has_port and not has_instance:
            attrs["info_kind"] = INFO_KIND_CLUSTER
            return attrs

        if has_ip and not has_port and not has_cluster_id and not has_instance:
            attrs["ip"] = ip
            attrs["info_kind"] = INFO_KIND_IP
            return attrs

        if has_instance and not has_ip and not has_port and not has_cluster_id:
            if not _INSTANCE_ADDR_RE.match(instance):
                raise serializers.ValidationError(_("instance must be in ip:port format"))
            attrs["instance"] = instance
            attrs["info_kind"] = INFO_KIND_INSTANCE
            return attrs

        raise serializers.ValidationError(
            _("each info must be one of: ip+port+cluster_id, cluster_id only, ip only, or instance only")
        )


class InstanceRestartPayloadSerializer(serializers.Serializer):
    uid = serializers.CharField(required=False, allow_blank=True, default="")
    created_by = serializers.CharField()
    bk_biz_id = serializers.IntegerField()
    bk_cloud_id = serializers.IntegerField(required=False)
    ticket_type = serializers.CharField(required=False, default="MONGODB_INSTANCE_RELOAD")
    infos = InstanceRestartInfoSerializer(many=True, allow_empty=False)
    force = serializers.BooleanField(required=False, default=False)

    def validate_uid(self, value):
        if value is None or value == "":
            return ""
        if isinstance(value, int):
            return str(value)
        text = str(value).strip()
        if not text:
            raise serializers.ValidationError(_("uid cannot be empty"))
        return text

    def validate_infos(self, infos):
        if not infos:
            raise serializers.ValidationError(_("infos cannot be empty"))
        return infos

    def validate(self, attrs):
        bk_cloud_id = attrs.get("bk_cloud_id")
        if bk_cloud_id is None:
            cloud_ids = {info["bk_cloud_id"] for info in attrs["infos"] if info.get("bk_cloud_id") is not None}
            if len(cloud_ids) == 1:
                attrs["bk_cloud_id"] = cloud_ids.pop()
            elif len(cloud_ids) > 1:
                raise serializers.ValidationError(
                    _("infos must share the same bk_cloud_id when top-level bk_cloud_id is omitted")
                )
            else:
                raise serializers.ValidationError(_("bk_cloud_id is required"))
        return attrs


def _cluster_queryset(bk_biz_id: int, bk_cloud_id: int):
    return Cluster.objects.filter(
        cluster_type__in=_MONGO_CLUSTER_TYPES,
        bk_biz_id=bk_biz_id,
        bk_cloud_id=bk_cloud_id,
    )


def _mongo_instance_querysets(bk_biz_id: int, bk_cloud_id: int):
    storage_qs = (
        StorageInstance.objects.select_related("machine")
        .prefetch_related("cluster")
        .filter(
            cluster__bk_biz_id=bk_biz_id,
            cluster__cluster_type__in=_MONGO_CLUSTER_TYPES,
            cluster__bk_cloud_id=bk_cloud_id,
            machine__bk_cloud_id=bk_cloud_id,
        )
    )
    proxy_qs = (
        ProxyInstance.objects.select_related("machine")
        .prefetch_related("cluster")
        .filter(
            cluster__bk_biz_id=bk_biz_id,
            cluster__cluster_type__in=_MONGO_CLUSTER_TYPES,
            cluster__bk_cloud_id=bk_cloud_id,
            machine__bk_cloud_id=bk_cloud_id,
        )
    )
    return storage_qs, proxy_qs


def _nodes_from_cluster(cluster: MongoDBCluster) -> List[RestartTargetNode]:
    nodes: List[RestartTargetNode] = []
    for rs in cluster.get_shards(with_config=True):
        if rs is None:
            continue
        for member in rs.members:
            nodes.append(
                RestartTargetNode.from_mongo_node(
                    member,
                    cluster_id=cluster.cluster_id,
                    cluster_type=cluster.cluster_type,
                    set_name=rs.set_name or cluster.name,
                    rs_type=rs.set_type,
                )
            )
    for mongos in cluster.get_mongos():
        nodes.append(
            RestartTargetNode.from_mongo_node(
                mongos,
                cluster_id=cluster.cluster_id,
                cluster_type=cluster.cluster_type,
                is_mongos=True,
            )
        )
    return nodes


def _resolve_cluster_id(cluster_id: int, bk_biz_id: int, bk_cloud_id: int) -> List[RestartTargetNode]:
    cluster_row = _cluster_queryset(bk_biz_id, bk_cloud_id).filter(id=cluster_id).first()
    if cluster_row is None:
        raise ValueError(
            _("cluster_id {} not found in bk_biz_id {} bk_cloud_id {}").format(cluster_id, bk_biz_id, bk_cloud_id)
        )
    cluster = MongoRepository.fetch_one_cluster(id=cluster_row.id)
    if cluster is None:
        raise ValueError(_("cluster_id {} is not a MongoDB cluster").format(cluster_id))
    return _nodes_from_cluster(cluster)


def _resolve_explicit_instance(
    ip: str, port: int, cluster_id: int, bk_biz_id: int, bk_cloud_id: int
) -> List[RestartTargetNode]:
    cluster = MongoRepository.fetch_one_cluster(id=cluster_id)
    if cluster is None:
        raise ValueError(_("cluster_id {} is not a MongoDB cluster").format(cluster_id))
    if cluster.bk_biz_id != bk_biz_id or cluster.bk_cloud_id != bk_cloud_id:
        raise ValueError(_("cluster_id {} does not match bk_biz_id/bk_cloud_id").format(cluster_id))
    for node in _nodes_from_cluster(cluster):
        if node.ip == ip and node.port == port and node.bk_cloud_id == bk_cloud_id:
            return [node]
    raise ValueError(_("instance {}:{} not found in cluster_id {}").format(ip, port, cluster_id))


def _resolve_ip(ip: str, bk_biz_id: int, bk_cloud_id: int) -> List[RestartTargetNode]:
    storage_qs, proxy_qs = _mongo_instance_querysets(bk_biz_id, bk_cloud_id)

    cluster_ids = set()
    for storage in storage_qs.filter(machine__ip=ip):
        cluster_ids.update(storage.cluster.values_list("id", flat=True))
    for proxy in proxy_qs.filter(machine__ip=ip):
        cluster_ids.update(proxy.cluster.values_list("id", flat=True))
    if not cluster_ids:
        raise ValueError(_("ip {} has no MongoDB instances in bk_cloud_id {}").format(ip, bk_cloud_id))

    nodes: List[RestartTargetNode] = []
    for cluster in MongoRepository.fetch_many_cluster(id__in=list(cluster_ids)):
        for node in _nodes_from_cluster(cluster):
            if node.ip == ip and node.bk_cloud_id == bk_cloud_id:
                nodes.append(node)
    return nodes


def _resolve_instance_addr(instance_addr: str, bk_biz_id: int, bk_cloud_id: int) -> List[RestartTargetNode]:
    match = _INSTANCE_ADDR_RE.match(instance_addr.strip())
    if not match:
        raise ValueError(_("invalid instance address {}").format(instance_addr))
    ip, port = match.group(1), int(match.group(2))

    storage_qs, proxy_qs = _mongo_instance_querysets(bk_biz_id, bk_cloud_id)

    cluster_ids = set()
    for storage in storage_qs.filter(machine__ip=ip, port=port):
        cluster_ids.update(storage.cluster.values_list("id", flat=True))
    for proxy in proxy_qs.filter(machine__ip=ip, port=port):
        cluster_ids.update(proxy.cluster.values_list("id", flat=True))
    if not cluster_ids:
        raise ValueError(_("instance {} has no MongoDB metadata in bk_cloud_id {}").format(instance_addr, bk_cloud_id))

    nodes: List[RestartTargetNode] = []
    for cluster in MongoRepository.fetch_many_cluster(id__in=list(cluster_ids)):
        for node in _nodes_from_cluster(cluster):
            if node.ip == ip and node.port == port and node.bk_cloud_id == bk_cloud_id:
                nodes.append(node)
    return nodes


def resolve_one_info(info: dict, bk_biz_id: int, bk_cloud_id: int) -> List[RestartTargetNode]:
    info_kind = info.get("info_kind")
    if info_kind == INFO_KIND_EXPLICIT:
        return _resolve_explicit_instance(info["ip"], info["port"], info["cluster_id"], bk_biz_id, bk_cloud_id)
    if info_kind == INFO_KIND_CLUSTER:
        return _resolve_cluster_id(info["cluster_id"], bk_biz_id, bk_cloud_id)
    if info_kind == INFO_KIND_IP:
        return _resolve_ip(info["ip"], bk_biz_id, bk_cloud_id)
    if info_kind == INFO_KIND_INSTANCE:
        return _resolve_instance_addr(info["instance"], bk_biz_id, bk_cloud_id)
    raise ValueError(_("empty restart info"))


def dedupe_restart_targets(nodes: List[RestartTargetNode]) -> List[RestartTargetNode]:
    seen = set()
    result: List[RestartTargetNode] = []
    for node in nodes:
        key = node.node_key()
        if key in seen:
            continue
        seen.add(key)
        result.append(node)
    return result


def batch_get_restart_node_credentials(
    nodes: List[RestartTargetNode],
    username: str = MongoDBManagerUser.DbaUser.value,
) -> Dict[Tuple[int, str, int], Tuple[str, str]]:
    """Batch fetch dba credentials for all restart targets (one DBPriv API call)."""
    unique_nodes = dedupe_restart_targets(nodes)
    if not unique_nodes:
        return {}

    instances = [{"ip": node.ip, "port": node.port, "bk_cloud_id": node.bk_cloud_id} for node in unique_nodes]
    result = MongoDBPassword().get_users_password_from_db(instances, [username])
    if result["password"] is None:
        raise ValueError(_("get password from password service failed: {}").format(result["info"]))

    credentials: Dict[Tuple[int, str, int], Tuple[str, str]] = {}
    for row in result["password"]:
        key = (int(row["bk_cloud_id"]), row["ip"], int(row["port"]))
        password = row.get("password")
        if not password:
            raise ValueError(_("empty password for {}:{}:{} user {}").format(key[1], key[2], key[0], username))
        credentials[key] = (username, password)

    missing = [node for node in unique_nodes if node.node_key() not in credentials]
    if missing:
        sample = missing[0]
        raise ValueError(
            _("missing password for {}:{}:{} user {}").format(sample.ip, sample.port, sample.bk_cloud_id, username)
        )
    return credentials


def resolve_restart_targets_from_infos(infos: List[dict], bk_biz_id: int, bk_cloud_id: int) -> List[RestartTargetNode]:
    nodes: List[RestartTargetNode] = []
    for info in infos:
        nodes.extend(resolve_one_info(info, bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id))
    nodes = dedupe_restart_targets(nodes)
    if not nodes:
        raise ValueError(_("no MongoDB instances resolved from infos"))
    return nodes


def group_restart_targets(
    nodes: List[RestartTargetNode],
) -> Tuple[Dict[str, List[RestartTargetNode]], List[RestartTargetNode]]:
    replicasets: Dict[str, List[RestartTargetNode]] = {}
    mongos: List[RestartTargetNode] = []
    for node in nodes:
        if node.is_mongos or node.role == MongoDBClusterRole.Mongos.value:
            mongos.append(node)
            continue
        rs_key = f"{node.cluster_id}:{node.set_name}"
        replicasets.setdefault(rs_key, []).append(node)
    return replicasets, mongos


@dataclass
class ClusterRestartPlan:
    cluster_id: int
    cluster_type: str
    shard_rs: Dict[str, List[RestartTargetNode]]
    config_rs: Dict[str, List[RestartTargetNode]]
    mongos: List[RestartTargetNode]


def group_restart_targets_by_cluster(nodes: List[RestartTargetNode]) -> Dict[int, ClusterRestartPlan]:
    plans: Dict[int, ClusterRestartPlan] = {}
    for node in nodes:
        if node.cluster_id not in plans:
            plans[node.cluster_id] = ClusterRestartPlan(
                cluster_id=node.cluster_id,
                cluster_type=node.cluster_type,
                shard_rs={},
                config_rs={},
                mongos=[],
            )
        plan = plans[node.cluster_id]
        if node.is_mongos or node.role == MongoDBClusterRole.Mongos.value:
            plan.mongos.append(node)
            continue
        rs_key = f"{node.cluster_id}:{node.set_name}"
        if node.rs_type == MongoDBClusterRole.ConfigSvr.value:
            plan.config_rs.setdefault(rs_key, []).append(node)
        else:
            plan.shard_rs.setdefault(rs_key, []).append(node)
    return plans


def _meta_role_sort_key(node: RestartTargetNode) -> Tuple[int, str, int]:
    return _META_ROLE_INDEX.get(node.role, len(_META_ROLE_ORDER)), node.ip, node.port


def order_rs_members_by_meta_role(nodes: List[RestartTargetNode]) -> List[RestartTargetNode]:
    return sorted(nodes, key=_meta_role_sort_key)


def _detect_primary_addrs_from_ext(nodes: List[RestartTargetNode]) -> Set[Tuple[str, int]]:
    if not nodes:
        return set()
    addr_set = {(node.ip, node.port) for node in nodes}
    ips = list({ip for ip, _ in addr_set})
    primary_addrs: Set[Tuple[str, int]] = set()
    ext_qs = MongoDBStorageInstanceExt.objects.filter(
        state=MongoDBStorageInstanceStatus.PRIMARY.name,
        instance__machine__ip__in=ips,
    ).select_related("instance", "instance__machine")
    for ext in ext_qs:
        inst = ext.instance
        key = (inst.machine.ip, inst.port)
        if key in addr_set:
            primary_addrs.add(key)
    return primary_addrs


def order_rs_members_defer_ext_primary(nodes: List[RestartTargetNode]) -> List[RestartTargetNode]:
    if not nodes:
        return []
    primary_addrs = _detect_primary_addrs_from_ext(nodes)
    if not primary_addrs:
        return order_rs_members_by_meta_role(nodes)

    backup_nodes = [node for node in nodes if node.role == InstanceRole.MONGO_BACKUP.value]
    primary_nodes: List[RestartTargetNode] = []
    other_nodes: List[RestartTargetNode] = []
    for node in nodes:
        if node.role == InstanceRole.MONGO_BACKUP.value:
            continue
        if (node.ip, node.port) in primary_addrs:
            primary_nodes.append(node)
        else:
            other_nodes.append(node)
    other_nodes.sort(key=_meta_role_sort_key)
    ordered: List[RestartTargetNode] = []
    if backup_nodes:
        ordered.extend(sorted(backup_nodes, key=_meta_role_sort_key))
    ordered.extend(other_nodes)
    ordered.extend(sorted(primary_nodes, key=_meta_role_sort_key))
    return ordered


def order_rs_members(nodes: List[RestartTargetNode], force: bool = False) -> List[RestartTargetNode]:
    """Order RS members for restart. `force` is accepted for call-site symmetry; ordering is identical."""
    del force
    return order_rs_members_defer_ext_primary(nodes)


def collect_hosts(nodes: List[RestartTargetNode]) -> List[dict]:
    host_map = {}
    for node in nodes:
        host_map[(node.bk_cloud_id, node.ip)] = {"ip": node.ip, "bk_cloud_id": node.bk_cloud_id}
    return list(host_map.values())
