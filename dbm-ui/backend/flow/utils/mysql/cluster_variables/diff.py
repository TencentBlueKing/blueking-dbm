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
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

ABSENT_VALUE = "ABSENT"
_BOOL_TRUE_TOKENS = frozenset({"on", "1", "true"})
_BOOL_FALSE_TOKENS = frozenset({"off", "0", "false"})
_SPIDER_SLAVE_ROLES = frozenset({"spider_slave", "spider_slave_mnt"})
_ISOLATION_KEYS = frozenset({"transaction_isolation", "tx_isolation"})
_CASE_INSENSITIVE_KEYS = frozenset({"default_storage_engine"})

# 内置：角色/实例天然不同（一般不参与一致性对比）
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


def _lower_set(keys: Optional[Iterable[str]]) -> frozenset:
    return frozenset(str(k).lower() for k in (keys or ()) if k)


def _default_should_skip(name: str) -> bool:
    lname = (name or "").lower()
    if not lname:
        return True
    return lname in _lower_set(PER_INSTANCE_VARIABLE_KEYS)


def _normalize_charset_collation(text: str) -> str:
    lowered = text.strip().lower()
    if lowered == "utf8":
        return "utf8mb3"
    if lowered.startswith("utf8_"):
        return f"utf8mb3_{lowered[5:]}"
    return lowered


def _normalize_semantic_value(lname: str, text: str) -> str:
    """对 MySQL 语义等价的不同写法进行归一化（字符集/排序规则、sql_mode、隔离级别、存储引擎）。"""
    if lname.startswith("character_set_") or lname.startswith("collation_"):
        return _normalize_charset_collation(text)
    if lname == "sql_mode":
        tokens = sorted({part.strip().upper() for part in text.split(",") if part.strip()})
        return ",".join(tokens)
    if lname in _ISOLATION_KEYS:
        return text.strip().upper().replace("_", "-")
    if lname in _CASE_INSENSITIVE_KEYS:
        return text.strip().lower()
    return text


def _normalize_compare_value(
    key: str,
    raw: Any,
    bool_set: frozenset,
    *,
    semantic_normalize: bool = False,
) -> str:
    text = str(raw)
    lname = key.lower()
    if lname in bool_set:
        token = text.strip().casefold()
        if token in _BOOL_TRUE_TOKENS:
            return "ON"
        if token in _BOOL_FALSE_TOKENS:
            return "OFF"
        return text
    if semantic_normalize:
        return _normalize_semantic_value(lname, text)
    return text


def diff_variables(
    left_vars: Dict[str, Any],
    right_vars: Dict[str, Any],
    *,
    should_skip: Optional[Callable[[str], bool]] = None,
    high_impact_keys: Optional[Iterable[str]] = None,
    bool_keys: Optional[Iterable[str]] = None,
    check_absent_keys: Optional[Iterable[str]] = None,
    semantic_normalize: bool = False,
) -> List[Dict[str, Any]]:
    """逐项对比两组变量；默认仅比双方共有键，传入 check_absent_keys 时对部分缺失报 ABSENT。"""
    skip_fn = should_skip or _default_should_skip
    high_set = _lower_set(HIGH_IMPACT_KEYS if high_impact_keys is None else high_impact_keys)
    bool_set = _lower_set(bool_keys)
    absent_set = _lower_set(check_absent_keys)

    left_map = left_vars or {}
    right_map = right_vars or {}
    left_keys = set(left_map.keys())
    right_keys = set(right_map.keys())

    candidate_keys = set(left_keys & right_keys)
    if absent_set:
        for key in left_keys ^ right_keys:
            if key.lower() in absent_set:
                candidate_keys.add(key)

    mismatches: List[Dict[str, Any]] = []
    for key in sorted(candidate_keys):
        if skip_fn(key):
            continue
        left_present = key in left_map
        right_present = key in right_map
        if left_present and right_present:
            left_cmp = _normalize_compare_value(key, left_map[key], bool_set, semantic_normalize=semantic_normalize)
            right_cmp = _normalize_compare_value(key, right_map[key], bool_set, semantic_normalize=semantic_normalize)
            if left_cmp == right_cmp:
                continue
            left_val, right_val = left_map[key], right_map[key]
        else:
            left_val = left_map[key] if left_present else ABSENT_VALUE
            right_val = right_map[key] if right_present else ABSENT_VALUE

        mismatches.append(
            {
                "variable_name": key,
                "master_value": left_val,
                "slave_value": right_val,
                "severity": "high" if key.lower() in high_set else "warn",
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


def _instance_version(inst: Dict, *, prefer_runtime: bool = False) -> str:
    vars_ = inst.get("variables") or {}
    runtime_ver = str(vars_.get("version") or "").strip()
    top = (inst.get("version_top") or inst.get("version") or "").strip()
    if prefer_runtime:
        return runtime_ver or top
    return top or runtime_ver


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


def _is_spider_slave(node: Dict) -> bool:
    role = (node.get("instance_role") or "").lower().strip()
    return role in _SPIDER_SLAVE_ROLES or "spider_slave" in role


def _mismatch_key(mismatches: List[Dict]) -> Tuple:
    return tuple(
        sorted(
            (
                m["variable_name"],
                str(m.get("master_value", m.get("left_value", ""))),
                str(m.get("slave_value", m.get("right_value", ""))),
            )
            for m in mismatches
        )
    )


def _aggregate(pairs: List[Dict], kind: str) -> List[Dict]:
    groups: Dict[Tuple, Dict] = {}
    order: List[Tuple] = []
    for pair in pairs:
        key = _mismatch_key(pair["mismatches"])
        if key not in groups:
            groups[key] = {"members": [], "mismatches": pair["mismatches"]}
            order.append(key)
        groups[key]["members"].append(pair)

    out: List[Dict] = []
    for key in order:
        members = groups[key]["members"]
        if len(members) == 1:
            out.append(members[0])
        elif kind == "shard":
            # 同差异模式多分片合并；master/slave 仅保留一例，避免 pairs_example 嵌套
            out.append(
                {
                    "scope": "shard_group",
                    "affected_shards": [m["shard_id"] for m in members],
                    "master": members[0]["master"],
                    "slave": members[0]["slave"],
                    "mismatches": groups[key]["mismatches"],
                }
            )
        else:
            out.append(
                {
                    "scope": "replica_group",
                    "master": members[0]["master"],
                    "affected_slaves": [m["slave"] for m in members],
                    "mismatches": groups[key]["mismatches"],
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
    for slave in _slaves_of(data):
        if not _has_vars(slave) or not _is_standby_slave(slave):
            continue
        out.append(_normalize(slave, "slave", None))
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
        shard_id = shard.get("shard_id", sid)
        if _has_vars(shard.get("master")):
            out.append(_normalize(shard["master"], "master", shard_id))
        for slave in _slaves_of(shard):
            if _has_vars(slave):
                out.append(_normalize(slave, "slave", shard_id))
    return out


def _ha_pairs(
    instances: List[Dict],
    *,
    should_skip: Optional[Callable[[str], bool]] = None,
    high_impact_keys: Optional[Iterable[str]] = None,
    bool_keys: Optional[Iterable[str]] = None,
    check_absent_keys: Optional[Iterable[str]] = None,
    semantic_normalize: bool = False,
) -> List[Dict]:
    masters = [inst for inst in instances if inst["role"] == "master" and not _is_spider(inst)]
    slaves = [inst for inst in instances if inst["role"] == "slave" and not _is_spider(inst)]
    raw: List[Dict] = []
    for master in masters:
        for slave in slaves:
            mismatches = diff_variables(
                master["variables"],
                slave["variables"],
                should_skip=should_skip,
                high_impact_keys=high_impact_keys,
                bool_keys=bool_keys,
                check_absent_keys=check_absent_keys,
                semantic_normalize=semantic_normalize,
            )
            if mismatches:
                raw.append(
                    {
                        "scope": "master_slave",
                        "master": master["address"],
                        "slave": slave["address"],
                        "mismatches": mismatches,
                    }
                )
    return _aggregate(raw, "master_slave")


def _cluster_shard_pairs(
    instances: List[Dict],
    *,
    should_skip: Optional[Callable[[str], bool]] = None,
    high_impact_keys: Optional[Iterable[str]] = None,
    bool_keys: Optional[Iterable[str]] = None,
    check_absent_keys: Optional[Iterable[str]] = None,
    semantic_normalize: bool = False,
) -> List[Dict]:
    masters = [inst for inst in instances if inst["role"] == "master" and not _is_spider(inst)]
    slaves = [inst for inst in instances if inst["role"] == "slave" and not _is_spider(inst)]
    shard_ids = sorted(
        {inst["shard_id"] for inst in masters + slaves if inst["shard_id"] is not None},
        key=lambda val: str(val),
    )
    raw: List[Dict] = []
    for sid in shard_ids:
        shard_masters = [m for m in masters if m["shard_id"] == sid]
        shard_slaves = [s for s in slaves if s["shard_id"] == sid]
        inner: List[Dict] = []
        for master in shard_masters:
            for slave in shard_slaves:
                mismatches = diff_variables(
                    master["variables"],
                    slave["variables"],
                    should_skip=should_skip,
                    high_impact_keys=high_impact_keys,
                    bool_keys=bool_keys,
                    check_absent_keys=check_absent_keys,
                    semantic_normalize=semantic_normalize,
                )
                if mismatches:
                    inner.append(
                        {
                            "scope": "shard",
                            "shard_id": sid,
                            "master": master["address"],
                            "slave": slave["address"],
                            "mismatches": mismatches,
                        }
                    )
        for item in _aggregate(inner, "master_slave"):
            item["scope"] = "shard"
            item["shard_id"] = sid
            if "master" not in item:
                item["master"] = shard_masters[0]["address"] if shard_masters else None
            item.setdefault("slave", None)
            raw.append(item)
    return _aggregate(raw, "shard")


def _collect_spider_nodes(data: Dict, exclude_spider_slave: bool = True) -> List[Dict]:
    by_addr: Dict[str, Dict] = {}
    for node in _as_list(data.get("spiders")):
        if not _has_vars(node):
            continue
        if exclude_spider_slave and _is_spider_slave(node):
            continue
        inst = _normalize(node, "spider", None)
        if _is_spider(inst) and inst.get("address"):
            by_addr[inst["address"]] = inst
    return list(by_addr.values())


def _spider_group_key(inst: Dict) -> str:
    """按 Spider 角色成组；默认排除 spider_slave，仅同角色节点彼此对比。"""
    role = (inst.get("instance_role") or "").lower().strip()
    return role or "spider"


def _diff_node_group_variables(
    members: List[Dict],
    *,
    should_skip: Optional[Callable[[str], bool]] = None,
    high_impact_keys: Optional[Iterable[str]] = None,
    bool_keys: Optional[Iterable[str]] = None,
    check_absent_keys: Optional[Iterable[str]] = None,
    semantic_normalize: bool = False,
) -> List[Dict]:
    """组内多节点变量一致性对比；支持布尔/语义归一化及指定键的部分缺失(ABSENT)检测。"""
    if len(members) < 2:
        return []
    skip_fn = should_skip or _default_should_skip
    high_set = _lower_set(HIGH_IMPACT_KEYS if high_impact_keys is None else high_impact_keys)
    bool_set = _lower_set(bool_keys)
    absent_set = _lower_set(check_absent_keys)

    key_sets = [set((member.get("variables") or {}).keys()) for member in members]
    candidate_keys = set.intersection(*key_sets) if key_sets else set()
    if absent_set:
        union_keys = set.union(*key_sets) if key_sets else set()
        for key in union_keys - candidate_keys:
            if key.lower() in absent_set:
                candidate_keys.add(key)

    mismatches: List[Dict] = []
    for key in sorted(candidate_keys):
        if skip_fn(key):
            continue
        buckets: OrderedDict = OrderedDict()
        for member in members:
            addr = str(member.get("address") or "")
            if not addr:
                continue
            vars_map = member.get("variables") or {}
            if key in vars_map:
                cmp_val = _normalize_compare_value(key, vars_map[key], bool_set, semantic_normalize=semantic_normalize)
            else:
                cmp_val = ABSENT_VALUE
            buckets.setdefault(cmp_val, []).append(addr)
        if len(buckets) <= 1:
            continue
        mismatches.append(
            {
                "variable_name": key,
                "severity": "high" if key.lower() in high_set else "warn",
                "by_value": {val: sorted(addrs) for val, addrs in buckets.items()},
            }
        )
    return mismatches


def _build_spider_groups(
    data: Dict,
    *,
    should_skip: Optional[Callable[[str], bool]] = None,
    high_impact_keys: Optional[Iterable[str]] = None,
    bool_keys: Optional[Iterable[str]] = None,
    check_absent_keys: Optional[Iterable[str]] = None,
    exclude_spider_slave: bool = True,
    semantic_normalize: bool = False,
) -> List[Dict]:
    """Spider 按角色成组做一致性检查；默认忽略 spider_slave，仅返回存在参数差异的组。"""
    nodes = [
        node for node in _collect_spider_nodes(data, exclude_spider_slave=exclude_spider_slave) if _is_spider(node)
    ]
    if not nodes:
        return []
    grouped: Dict[str, List[Dict]] = OrderedDict()
    for node in nodes:
        grouped.setdefault(_spider_group_key(node), []).append(node)

    out: List[Dict] = []
    for group_name, members in grouped.items():
        members = sorted(members, key=lambda item: str(item.get("address") or ""))
        uniq: OrderedDict = OrderedDict()
        for member in members:
            addr = str(member.get("address") or "")
            if addr and addr not in uniq:
                uniq[addr] = member
        member_list = list(uniq.values())
        if len(member_list) < 2:
            continue
        mismatches = _diff_node_group_variables(
            member_list,
            should_skip=should_skip,
            high_impact_keys=high_impact_keys,
            bool_keys=bool_keys,
            check_absent_keys=check_absent_keys,
            semantic_normalize=semantic_normalize,
        )
        if not mismatches:
            continue
        out.append({"group": group_name, "mismatches": mismatches})
    return out


def _build_remote_master_mismatches(
    instances: List[Dict],
    *,
    should_skip: Optional[Callable[[str], bool]] = None,
    high_impact_keys: Optional[Iterable[str]] = None,
    bool_keys: Optional[Iterable[str]] = None,
    check_absent_keys: Optional[Iterable[str]] = None,
    semantic_normalize: bool = False,
) -> List[Dict]:
    """跨分片 remote_master 组内一致性检查。"""
    masters = [inst for inst in instances if inst["role"] == "master" and not _is_spider(inst)]
    uniq: OrderedDict = OrderedDict()
    for inst in sorted(masters, key=lambda item: str(item.get("address") or "")):
        addr = str(inst.get("address") or "")
        if addr and addr not in uniq:
            uniq[addr] = inst
    return _diff_node_group_variables(
        list(uniq.values()),
        should_skip=should_skip,
        high_impact_keys=high_impact_keys,
        bool_keys=bool_keys,
        check_absent_keys=check_absent_keys,
        semantic_normalize=semantic_normalize,
    )


def build_spider_version(
    data: Dict,
    exclude_spider_slave: bool = True,
    *,
    prefer_runtime_version: bool = False,
    skip_missing_vars: bool = False,
) -> Dict[str, Any]:
    """紧凑版本摘要：consistent + by_version（版本 → 地址列表）；默认忽略 spider_slave。

    prefer_runtime_version=True 时优先使用实例运行时 SHOW GLOBAL VARIABLES 返回的 version（空时兜底元数据）；
    skip_missing_vars=True 时跳过 variables 非 dict 的失联节点。
    """
    by_version: OrderedDict = OrderedDict()
    for node in _as_list(data.get("spiders")):
        if not isinstance(node, dict):
            continue
        if exclude_spider_slave and _is_spider_slave(node):
            continue
        if skip_missing_vars and not _has_vars(node):
            continue
        addr = str(node.get("address") or "").strip()
        if not addr:
            continue
        inst = _normalize(node, "spider", None)
        ver = _instance_version(inst, prefer_runtime=prefer_runtime_version) or ""
        by_version.setdefault(ver, []).append(addr)
    for ver in list(by_version.keys()):
        by_version[ver] = sorted(by_version[ver])
    ordered = OrderedDict((ver, by_version[ver]) for ver in sorted(by_version.keys()))
    return {"consistent": len(ordered) <= 1, "by_version": dict(ordered)}


def build_tendbha_variable_diff(
    runtime_data: Dict,
    cluster_domain: str = "",
    *,
    should_skip: Optional[Callable[[str], bool]] = None,
    high_impact_keys: Optional[Iterable[str]] = None,
    bool_keys: Optional[Iterable[str]] = None,
    check_absent_keys: Optional[Iterable[str]] = None,
    semantic_normalize: bool = False,
) -> Dict:
    """纯函数：基于 cluster_runtime_variables 形态数据产出 HA 差异。"""
    pairs = _ha_pairs(
        _collect_tendbha(runtime_data),
        should_skip=should_skip,
        high_impact_keys=high_impact_keys,
        bool_keys=bool_keys,
        check_absent_keys=check_absent_keys,
        semantic_normalize=semantic_normalize,
    )
    return {
        "cluster_type": "tendbha",
        "cluster_domain": cluster_domain,
        "replication_pairs": pairs,
    }


def build_tendbcluster_variable_diff(
    runtime_data: Dict,
    cluster_domain: str = "",
    *,
    spider_should_skip: Optional[Callable[[str], bool]] = None,
    shard_should_skip: Optional[Callable[[str], bool]] = None,
    spider_high_impact_keys: Optional[Iterable[str]] = None,
    shard_high_impact_keys: Optional[Iterable[str]] = None,
    bool_keys: Optional[Iterable[str]] = None,
    spider_check_absent_keys: Optional[Iterable[str]] = None,
    shard_check_absent_keys: Optional[Iterable[str]] = None,
    include_remote_master_group: bool = False,
    prefer_runtime_spider_version: bool = False,
    semantic_normalize: bool = False,
) -> Dict:
    """纯函数：基于 cluster_runtime_variables 形态数据产出 Cluster 差异（紧凑结构）。"""
    shard_instances = _collect_tendbcluster_shards(runtime_data)
    result = {
        "cluster_type": "tendbcluster",
        "cluster_domain": cluster_domain,
        "spider_version": build_spider_version(
            runtime_data,
            exclude_spider_slave=True,
            prefer_runtime_version=prefer_runtime_spider_version,
            skip_missing_vars=prefer_runtime_spider_version,
        ),
        "spider_groups": _build_spider_groups(
            runtime_data,
            should_skip=spider_should_skip,
            high_impact_keys=spider_high_impact_keys,
            bool_keys=bool_keys,
            check_absent_keys=spider_check_absent_keys,
            exclude_spider_slave=True,
            semantic_normalize=semantic_normalize,
        ),
        "shard_pairs": _cluster_shard_pairs(
            shard_instances,
            should_skip=shard_should_skip,
            high_impact_keys=shard_high_impact_keys,
            bool_keys=bool_keys,
            check_absent_keys=shard_check_absent_keys,
            semantic_normalize=semantic_normalize,
        ),
    }
    if include_remote_master_group:
        result["remote_master_mismatches"] = _build_remote_master_mismatches(
            shard_instances,
            should_skip=shard_should_skip,
            high_impact_keys=shard_high_impact_keys,
            bool_keys=bool_keys,
            check_absent_keys=shard_check_absent_keys,
            semantic_normalize=semantic_normalize,
        )
    return result
