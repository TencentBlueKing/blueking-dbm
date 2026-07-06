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

from collections import OrderedDict
from typing import Any, Dict, List, Tuple

# 仅依赖同目录取数模块中的忽略键常量；取数函数在入口包装里惰性导入，便于纯函数单测。
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables import IGNORED_RUNTIME_VARIABLE_KEYS

# 内置：角色/实例天然不同（与 skill compare_instances 对齐，一般不随意删）
PER_INSTANCE_VARIABLE_KEYS = frozenset(
    {
        "server_id",
        "server_uuid",
        "hostname",
        "bind_address",
        "report_host",
        "report_port",
        "admin_address",
        "gtid_executed",
        "gtid_purged",
        "gtid_owned",
        "port",
        "admin_port",
        "mysqlx_port",
        "datadir",
        "basedir",
        "tmpdir",
        "socket",
        "pid_file",
        "secure_file_priv",
        "slave_load_tmpdir",
        "lc_messages_dir",
        "plugin_dir",
        "character_sets_dir",
        "innodb_data_home_dir",
        "innodb_log_group_home_dir",
        "innodb_temp_tablespaces_dir",
        "log_error",
        "general_log_file",
        "slow_query_log_file",
        "log_bin_basename",
        "log_bin_index",
        "relay_log",
        "relay_log_basename",
        "relay_log_index",
        "innodb_buffer_pool_size",
        # Spider 每节点独立自增分配参数，节点间天然不同
        "spider_auto_increment_mode_switch",
        "spider_auto_increment_mode_value",
        "spider_auto_increment_step",
    }
)

HIGH_IMPACT_KEYS = frozenset(
    {
        "gtid_mode",
        "enforce_gtid_consistency",
        "sql_mode",
        "character_set_server",
        "collation_server",
        "lower_case_table_names",
        "transaction_isolation",
        "tx_isolation",
        "binlog_format",
        "binlog_row_image",
        "log_bin",
        "default_table_encryption",
    }
)

# 可自定义：额外忽略的精确变量名（小写匹配）。在此追加业务侧不想对比的键。
EXTRA_IGNORE_VARIABLE_KEYS: frozenset[str] = frozenset(
    {
        "read_only",
        "super_read_only",
    }
)

# 可自定义：额外忽略的变量名前缀（小写 startswith）。在此追加前缀。
# 注：myisam_ / performance_schema_ 等已在 cluster_runtime_variables 取数时过滤，此处不必重复。
EXTRA_IGNORE_VARIABLE_PREFIXES: Tuple[str, ...] = (
    # 例: "spider_auto_increment_",
)


def _lower_key_set(keys) -> frozenset:
    return frozenset(k.lower() for k in keys)


def should_skip_variable(name: str) -> bool:
    """判断变量是否应在对比中跳过（天然不同 / 额外忽略键 / 前缀）。"""
    lname = (name or "").lower()
    if not lname:
        return True
    if lname in _lower_key_set(IGNORED_RUNTIME_VARIABLE_KEYS):
        return True
    if lname in _lower_key_set(PER_INSTANCE_VARIABLE_KEYS):
        return True
    if lname in _lower_key_set(EXTRA_IGNORE_VARIABLE_KEYS):
        return True
    for prefix in EXTRA_IGNORE_VARIABLE_PREFIXES:
        if prefix and lname.startswith(prefix.lower()):
            return True
    return False


def diff_variables(left_vars: Dict[str, Any], right_vars: Dict[str, Any]) -> List[Dict[str, Any]]:
    """双方共有键逐项对比；仅一侧存在的键不报 mismatch。"""
    mismatches: List[Dict[str, Any]] = []
    for key in sorted(set(left_vars or {}) & set(right_vars or {})):
        if should_skip_variable(key):
            continue
        left_val = left_vars[key]
        right_val = right_vars[key]
        if str(left_val) != str(right_val):
            lname = key.lower()
            mismatches.append(
                {
                    "variable_name": key,
                    "left_value": left_val,
                    "right_value": right_val,
                    "severity": "high" if lname in {k.lower() for k in HIGH_IMPACT_KEYS} else "warn",
                }
            )
    return mismatches


def _has_vars(node: Any) -> bool:
    return isinstance(node, dict) and isinstance(node.get("variables"), dict)


def _as_list(val: Any) -> List:
    if val is None:
        return []
    return val if isinstance(val, list) else [val]


def _slaves_of(node: Dict) -> List:
    raw = node.get("slaves") if node.get("slaves") is not None else node.get("slave")
    return _as_list(raw)


def _normalize(node: Dict, role: str, shard_id: Any) -> Dict:
    return {
        "address": node.get("address"),
        "instance_role": (node.get("instance_role") or "").lower(),
        "machine_type": (node.get("machine_type") or "").lower(),
        "role": role,
        "shard_id": shard_id,
        "variables": node.get("variables") or {},
        "version_top": node.get("version") or "",
    }


def _instance_version(inst: Dict) -> str:
    top = (inst.get("version_top") or inst.get("version") or "").strip()
    if top:
        return top
    vars_ = inst.get("variables") or {}
    return str(vars_.get("version") or "").strip()


def _is_spider(inst: Dict) -> bool:
    ir = (inst.get("instance_role") or "").lower()
    mt = (inst.get("machine_type") or "").lower()
    if "spider" in ir or "spider" in mt:
        return True
    vars_ = inst.get("variables") or {}
    if any(str(k).startswith("spider_") for k in vars_):
        return True
    ver = _instance_version(inst).lower()
    if "tspider" in ver:
        return True
    if "mariadb" in ver and "spider" in ver:
        return True
    return False


def _mismatch_key(mismatches: List[Dict]) -> Tuple:
    return tuple(sorted((m["variable_name"], str(m["left_value"]), str(m["right_value"])) for m in mismatches))


def _aggregate(pairs: List[Dict], kind: str) -> List[Dict]:
    groups: Dict[Tuple, Dict] = {}
    order: List[Tuple] = []
    for p in pairs:
        k = _mismatch_key(p["mismatches"])
        if k not in groups:
            groups[k] = {"members": [], "mismatches": p["mismatches"]}
            order.append(k)
        groups[k]["members"].append(p)
    out: List[Dict] = []
    for k in order:
        ms = groups[k]["members"]
        if len(ms) == 1:
            out.append(ms[0])
        elif kind == "shard":
            out.append(
                {
                    "scope": "shard_group",
                    "affected_shards": [m["shard_id"] for m in ms],
                    "pairs_example": {
                        "shard_id": ms[0]["shard_id"],
                        "master": ms[0]["master"],
                        "slave": ms[0]["slave"],
                    },
                    "mismatches": groups[k]["mismatches"],
                }
            )
        else:
            out.append(
                {
                    "scope": "replica_group",
                    "master": ms[0]["master"],
                    "affected_slaves": [m["slave"] for m in ms],
                    "mismatches": groups[k]["mismatches"],
                }
            )
    return out


def _is_standby_slave(node: Dict) -> bool:
    """TenDBHA 一主多从时，仅 is_stand_by=True 的从库参与对比。"""
    return bool(node.get("is_stand_by"))


def _collect_tendbha(data: Dict) -> List[Dict]:
    """收集 HA 对比实例：master + standby slave（忽略普通 slave）。"""
    out: List[Dict] = []
    if _has_vars(data.get("master")):
        out.append(_normalize(data["master"], "master", None))
    for s in _slaves_of(data):
        if not _has_vars(s):
            continue
        if not _is_standby_slave(s):
            continue
        out.append(_normalize(s, "slave", None))
    return out


def _collect_tendbcluster_shards(data: Dict) -> List[Dict]:
    out: List[Dict] = []
    shards = data.get("shards")
    if isinstance(shards, dict):
        items = shards.items()
    elif isinstance(shards, list):
        items = enumerate(shards)
    else:
        items = []
    for sid, shard in items:
        if not isinstance(shard, dict):
            continue
        sid = shard.get("shard_id", sid)
        if _has_vars(shard.get("master")):
            out.append(_normalize(shard["master"], "master", sid))
        for s in _slaves_of(shard):
            if _has_vars(s):
                out.append(_normalize(s, "slave", sid))
    return out


def _ha_pairs(instances: List[Dict]) -> List[Dict]:
    masters = [i for i in instances if i["role"] == "master" and not _is_spider(i)]
    slaves = [i for i in instances if i["role"] == "slave" and not _is_spider(i)]
    raw: List[Dict] = []
    for m in masters:
        for s in slaves:
            mm = diff_variables(m["variables"], s["variables"])
            if mm:
                raw.append(
                    {
                        "scope": "master_slave",
                        "master": m["address"],
                        "slave": s["address"],
                        "mismatches": mm,
                    }
                )
    return _aggregate(raw, "master_slave")


def _cluster_shard_pairs(instances: List[Dict]) -> List[Dict]:
    masters = [i for i in instances if i["role"] == "master" and not _is_spider(i)]
    slaves = [i for i in instances if i["role"] == "slave" and not _is_spider(i)]
    shard_ids = sorted(
        {i["shard_id"] for i in masters + slaves if i["shard_id"] is not None},
        key=lambda x: str(x),
    )
    raw: List[Dict] = []
    for sid in shard_ids:
        sm = [m for m in masters if m["shard_id"] == sid]
        ss = [s for s in slaves if s["shard_id"] == sid]
        inner: List[Dict] = []
        for m in sm:
            for s in ss:
                mm = diff_variables(m["variables"], s["variables"])
                if mm:
                    inner.append(
                        {
                            "scope": "shard",
                            "shard_id": sid,
                            "master": m["address"],
                            "slave": s["address"],
                            "mismatches": mm,
                        }
                    )
        for it in _aggregate(inner, "master_slave"):
            it["scope"] = "shard"
            it["shard_id"] = sid
            if "master" not in it:
                it["master"] = sm[0]["address"] if sm else None
            it.setdefault("slave", None)
            raw.append(it)
    return _aggregate(raw, "shard")


def _collect_spider_nodes(data: Dict) -> List[Dict]:
    by_addr: Dict[str, Dict] = {}
    for node in _as_list(data.get("spiders")):
        if not _has_vars(node):
            continue
        inst = _normalize(node, "spider", None)
        if _is_spider(inst) and inst.get("address"):
            by_addr[inst["address"]] = inst
    return list(by_addr.values())


def _spider_group_key(inst: Dict) -> str:
    mt = (inst.get("machine_type") or "").lower()
    role = (inst.get("role") or "").lower()
    if "spider" in mt or role == "spider":
        return "proxy"
    return "embedded"


def _build_spider_pairs(data: Dict) -> List[Dict]:
    nodes = [n for n in _collect_spider_nodes(data) if _is_spider(n)]
    if not nodes:
        return []
    groups: Dict[str, List[Dict]] = OrderedDict()
    for n in nodes:
        key = _spider_group_key(n)
        groups.setdefault(key, []).append(n)
    raw: List[Dict] = []
    for group in groups.values():
        group.sort(key=lambda x: str(x.get("address") or ""))
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                addr_a, addr_b = str(a.get("address") or ""), str(b.get("address") or "")
                if not addr_a or not addr_b or addr_a == addr_b:
                    continue
                lo, hi = (a, b) if addr_a <= addr_b else (b, a)
                mm = diff_variables(lo["variables"], hi["variables"])
                if mm:
                    raw.append(
                        {
                            "scope": "spider_peer",
                            "peer_a": lo["address"],
                            "peer_b": hi["address"],
                            "mismatches": mm,
                        }
                    )
    return raw


def _build_spider_versions(data: Dict) -> Tuple[List[Dict], Dict[str, Any]]:
    versions_list: List[Dict] = []
    version_set = set()
    for node in _as_list(data.get("spiders")):
        if not isinstance(node, dict):
            continue
        inst = _normalize(node, "spider", None)
        ver = _instance_version(inst)
        versions_list.append(
            {
                "address": node.get("address") or "",
                "instance_role": node.get("instance_role") or "",
                "version": ver,
            }
        )
        if ver:
            version_set.add(ver)
    versions_list.sort(key=lambda x: str(x.get("address") or ""))
    unique = sorted(version_set)
    return versions_list, {"is_consistent": len(unique) <= 1, "versions": unique}


def build_tendbha_variable_diff(runtime_data: Dict, cluster_domain: str = "") -> Dict:
    """纯函数：基于 cluster_runtime_variables 形态数据产出 HA 差异。"""
    pairs = _ha_pairs(_collect_tendbha(runtime_data))
    return {
        "cluster_type": "tendbha",
        "cluster_domain": cluster_domain,
        "replication_pairs": pairs,
    }


def build_tendbcluster_variable_diff(runtime_data: Dict, cluster_domain: str = "") -> Dict:
    """纯函数：基于 cluster_runtime_variables 形态数据产出 Cluster 差异。"""
    spider_versions, spider_version_diff = _build_spider_versions(runtime_data)
    return {
        "cluster_type": "tendbcluster",
        "cluster_domain": cluster_domain,
        "spider_versions": spider_versions,
        "spider_version_diff": spider_version_diff,
        "spider_pairs": _build_spider_pairs(runtime_data),
        "shard_pairs": _cluster_shard_pairs(_collect_tendbcluster_shards(runtime_data)),
    }


def tendbha_master_slave_variable_diff(cluster_obj) -> Dict:
    from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables import cluster_runtime_variables

    runtime = cluster_runtime_variables(cluster_obj)
    return build_tendbha_variable_diff(runtime, cluster_domain=cluster_obj.immute_domain or "")


def tendbcluster_variable_diff(cluster_obj) -> Dict:
    from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables import cluster_runtime_variables

    runtime = cluster_runtime_variables(cluster_obj)
    return build_tendbcluster_variable_diff(runtime, cluster_domain=cluster_obj.immute_domain or "")
