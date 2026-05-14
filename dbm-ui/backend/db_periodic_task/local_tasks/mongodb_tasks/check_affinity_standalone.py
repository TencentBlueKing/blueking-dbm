#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB affinity offline checker (no Django dependency).

Workflow:
1) Export JSON snapshots from MySQL (read-only), **without** importing this repo:
   `dbm-ui/.cycscript/dump_affinity_json.sh` (uses `mysql` + `python3` stdlib only).
2) Run this script with the exported JSON files.

Run:
  python check_affinity_standalone.py \
    --cluster-defs-json cluster_defs.json \
    --cluster-nodes-json cluster_nodes.json \
    --subzones-json subzones.json \
    --cities-json cities.json

Affinity region uses **logical city name** only (`logical_city_name` in JSON; online: `BKCity.logical_city.name`).
IDC city names are not used for region comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from math import ceil
from pathlib import Path
from typing import Any

# 此处和from backend.configuration.constants import AffinityEnum保持一致
# 需要以standalone方式运行,所以这里重新定义一次

SAME_SUBZONE_CROSS_SWTICH = "SAME_SUBZONE_CROSS_SWTICH"
SAME_SUBZONE = "SAME_SUBZONE"
CROS_SUBZONE = "CROS_SUBZONE"
CROSS_RACK = "CROSS_RACK"
NONE = "NONE"
MAX_EACH_ZONE_EQUAL = "MAX_EACH_ZONE_EQUAL"
CROSS_SUBZONE_STRONG = "CROSS_SUBZONE_STRONG"
CROSS_SUBZONE_WEAK = "CROSS_SUBZONE_WEAK"
MAJORITY_ELECTION_DISTRI = "MAJORITY_ELECTION_DISTRI"
MONGO_BACKUP = "MONGO_BACKUP"

NORMAL = "normal"
WARNING = "warning"
ABNORMAL = "abnormal"


def err(code: str, message: str) -> str:
    return f"code={code} {message}"


def affinity_display_name(affinity: str) -> str:
    affinity_cn_map = {
        SAME_SUBZONE_CROSS_SWTICH: "指定园区",
        SAME_SUBZONE: "指定园区(无机架要求)",
        CROS_SUBZONE: "跨园区",
        CROSS_SUBZONE_STRONG: "跨园区(强)",
        CROSS_SUBZONE_WEAK: "跨园区(弱)",
        MAJORITY_ELECTION_DISTRI: "最少跨2个园区，园区内跨机架",
        MAX_EACH_ZONE_EQUAL: "每个subzone尽量均匀分布",
        CROSS_RACK: "不限园区",
        NONE: "无",
    }
    if affinity in affinity_cn_map:
        return f"{affinity}({affinity_cn_map[affinity]})"
    return affinity


def is_backup_role(value: str) -> bool:
    role = str(value or "").strip().upper()
    return role == "BACKUP" or MONGO_BACKUP in role


@dataclass
class ClusterEval:
    cluster_id: int
    domain: str
    cluster_type: str
    cluster_region: str
    has_single_node_tag: bool
    affinity: str
    zone_list: set[str] = field(default_factory=set)
    actual_sub_zones: set[str] = field(default_factory=set)
    actual_regions: set[str] = field(default_factory=set)
    actual_racks: set[str] = field(default_factory=set)
    component_details: list[dict[str, Any]] = field(default_factory=list)
    state: str = NORMAL
    reasons: list[str] = field(default_factory=list)


@dataclass
class ComponentEval:
    set_name: str
    sub_zones: set[str] = field(default_factory=set)
    regions: set[str] = field(default_factory=set)
    racks: set[str] = field(default_factory=set)
    nodes: list[dict[str, str]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def is_shardsvr_set(set_name: str) -> bool:
    return set_name not in {"mongos", "configsvr"}


def build_shardsvr_group_key(nodes: list[dict[str, str]]) -> str:
    machine_keys = sorted(
        {
            f"{str(node.get('bk_cloud_id', '') or '')}:{str(node.get('ip', '') or '')}"
            for node in nodes
            if str(node.get("ip", "") or "")
        }
    )
    return f"shardsvr_group:{'|'.join(machine_keys)}"


def dedup_nodes_by_machine(nodes: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped = {}
    for node in nodes:
        key = f"{str(node.get('bk_cloud_id', '') or '')}:{str(node.get('ip', '') or '')}"
        if key not in deduped:
            deduped[key] = node
    return list(deduped.values())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline MongoDB affinity checker (JSON input).")
    parser.add_argument("--cluster-defs-json", required=True, help="Path to cluster_defs.json")
    parser.add_argument("--cluster-nodes-json", required=True, help="Path to cluster_nodes.json")
    parser.add_argument("--subzones-json", required=True, help="Path to subzones.json")
    parser.add_argument("--cities-json", required=True, help="Path to cities.json")
    parser.add_argument("--summary-by-code", action="store_true", help="Print aggregated counts by error/warning code")
    return parser.parse_args()


def load_json_file(path: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    with file_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"json must be list: {path}")
    return data


def normalize_to_str_set(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        # compatible with dumped JSON string column like "[1,2]"
        try:
            parsed = json.loads(values)
            if isinstance(parsed, list):
                values = parsed
            else:
                values = [values]
        except json.JSONDecodeError:
            values = [values]
    if not isinstance(values, list):
        values = [values]
    return {str(value) for value in values if value not in [None, ""]}


def check_affinity_rules(  # noqa: C901
    disaster_tolerance_level: str,
    cluster_region: str,
    zone_list: set[str],
    actual_sub_zone_set: set[str],
    actual_region_set: set[str],
    actual_rack_set: set[str],
    component_nodes: list[dict[str, str]],
    zone_name_map: dict[str, str] | None = None,
    has_single_node_tag: bool = False,
) -> tuple[str, list[str]]:
    """Evaluate affinity for one component (sub_zone / region / rack / zone_list rules).

    When ``has_single_node_tag`` is True, skip **only** the minimum sub_zone **count**
    checks for: ``CROS_SUBZONE`` (>=2 zones), ``CROSS_SUBZONE_STRONG`` (>=3 zones),
    ``CROSS_SUBZONE_WEAK`` (>=2 zones), ``MAJORITY_ELECTION_DISTRI`` (>=2 zones).
    Zone tolerance, rack rules, region, zone_list, etc. still apply. Member-count checks
    are enforced in callers (``evaluate`` / ``CheckMongodbAffinityTask``), not here.
    """
    warnings = []
    errors = []
    is_none = disaster_tolerance_level == NONE
    affinity_name = affinity_display_name(disaster_tolerance_level)
    non_backup_nodes = [node for node in component_nodes if not is_backup_role(node.get("instance_role", ""))]
    non_backup_sub_zone_set = {
        node.get("actual_sub_zone", "") for node in non_backup_nodes if node.get("actual_sub_zone", "")
    }
    non_backup_rack_set = {node.get("actual_rack", "") for node in non_backup_nodes if node.get("actual_rack", "")}

    is_same_subzone = disaster_tolerance_level in [SAME_SUBZONE, SAME_SUBZONE_CROSS_SWTICH]

    if not is_none:
        if cluster_region:
            if actual_region_set != {cluster_region}:
                errors.append(
                    err(
                        "region_mismatch",
                        f"cluster region mismatch, expected={[cluster_region]}, actual={sorted(actual_region_set)}",
                    )
                )
        else:
            warnings.append(err("cluster_region_empty", "cluster.region is empty"))

    if not is_none and len(actual_region_set) != 1:
        errors.append(
            err(
                "multi_region_violation",
                f"affinity {affinity_name} requires single region, actual={sorted(actual_region_set)}",
            )
        )

    if is_same_subzone:
        expected_zone_set = (
            non_backup_sub_zone_set if disaster_tolerance_level == SAME_SUBZONE_CROSS_SWTICH else actual_sub_zone_set
        )
        if len(zone_list) != 1:
            errors.append(
                err(
                    "zone_list_required_single",
                    f"config_error: affinity {affinity_name} requires zone_list to have exactly 1 value, "
                    f"actual={sorted(zone_list)}",
                )
            )
        elif zone_list != expected_zone_set:
            errors.append(
                err(
                    "zone_list_mismatch",
                    f"zone_list mismatch, expected={sorted(zone_list)}, actual={sorted(expected_zone_set)}",
                )
            )
    elif not is_none:
        if zone_list and zone_list != actual_sub_zone_set:
            errors.append(
                err(
                    "zone_list_mismatch",
                    f"zone_list mismatch, expected={sorted(zone_list)}, actual={sorted(actual_sub_zone_set)}",
                )
            )

    zone_counter: dict[str, int] = {}
    zone_rack_counter: dict[str, dict[str, int]] = {}
    rack_counter: dict[str, int] = {}
    for node in component_nodes:
        zone = node.get("actual_sub_zone", "")
        rack = node.get("actual_rack", "")
        if not zone:
            continue
        zone_counter[zone] = zone_counter.get(zone, 0) + 1
        if rack:
            rack_counter[rack] = rack_counter.get(rack, 0) + 1
            zone_rack_counter.setdefault(zone, {})
            zone_rack_counter[zone][rack] = zone_rack_counter[zone].get(rack, 0) + 1
    node_num = sum(zone_counter.values())
    zone_name_map = zone_name_map or {}

    def display_zone_counts(counts: dict[str, int]) -> dict[str, int]:
        return {
            f"{zone_name_map.get(zone, zone)}({zone})" if zone_name_map.get(zone) else zone: cnt
            for zone, cnt in counts.items()
        }

    if disaster_tolerance_level == SAME_SUBZONE:
        if len(actual_sub_zone_set) != 1:
            errors.append(
                err(
                    "same_subzone_violation",
                    f"affinity {affinity_name} requires single sub_zone, actual={sorted(actual_sub_zone_set)}",
                )
            )
    elif disaster_tolerance_level == SAME_SUBZONE_CROSS_SWTICH:
        if len(non_backup_sub_zone_set) != 1:
            errors.append(
                err(
                    "same_subzone_cross_zone_violation",
                    f"affinity {affinity_name} requires single sub_zone for non-backup nodes, "
                    f"actual={sorted(non_backup_sub_zone_set)}",
                )
            )
        if len(non_backup_rack_set) < 2:
            errors.append(
                err(
                    "same_subzone_cross_rack_violation",
                    f"affinity {affinity_name} requires at least 2 racks for non-backup nodes, "
                    f"actual={sorted(non_backup_rack_set)}",
                )
            )
    elif disaster_tolerance_level == CROS_SUBZONE:
        if len(actual_sub_zone_set) < 2 and not has_single_node_tag:
            errors.append(
                err(
                    "cross_subzone_min_violation",
                    f"affinity {affinity_name} requires at least 2 sub_zones, actual={sorted(actual_sub_zone_set)}",
                )
            )
    elif disaster_tolerance_level == CROSS_SUBZONE_STRONG:
        zone_count_violation = len(actual_sub_zone_set) < 3 and not has_single_node_tag
        zone_tolerance_violation = node_num > 0 and max(zone_counter.values() or [0]) > ceil(node_num / 3)
        if zone_count_violation or zone_tolerance_violation:
            reasons = []
            if zone_count_violation:
                reasons.append("requires at least 3 sub_zones")
            if zone_tolerance_violation:
                reasons.append("zone tolerance(1/3) violated")
            errors.append(
                err(
                    "strong_zone_constraint_violation",
                    f"affinity {affinity_name} {' and '.join(reasons)}, "
                    f"actual={sorted(actual_sub_zone_set)}, zone_counts={display_zone_counts(zone_counter)}",
                )
            )
        rack_count_violation = node_num > 1 and len(rack_counter) < 2
        rack_tolerance_violation = node_num > 0 and max(rack_counter.values() or [0]) > ceil(node_num / 2)
        if rack_count_violation or rack_tolerance_violation:
            reasons = []
            if rack_count_violation:
                reasons.append("requires at least 2 racks")
            if rack_tolerance_violation:
                reasons.append("rack tolerance(1/2) violated")
            errors.append(
                err(
                    "strong_rack_constraint_violation",
                    f"affinity {affinity_name} {' and '.join(reasons)}, rack_counts={rack_counter}",
                )
            )
    elif disaster_tolerance_level == CROSS_SUBZONE_WEAK:
        zone_count_violation = len(actual_sub_zone_set) < 2 and not has_single_node_tag
        zone_tolerance_violation = node_num > 0 and max(zone_counter.values() or [0]) > ceil(node_num / 2)
        if zone_count_violation or zone_tolerance_violation:
            reasons = []
            if zone_count_violation:
                reasons.append("requires at least 2 sub_zones")
            if zone_tolerance_violation:
                reasons.append("zone tolerance(1/2) violated")
            errors.append(
                err(
                    "weak_zone_constraint_violation",
                    f"affinity {affinity_name} {' and '.join(reasons)}, "
                    f"actual={sorted(actual_sub_zone_set)}, zone_counts={display_zone_counts(zone_counter)}",
                )
            )
        rack_count_violation = node_num > 1 and len(rack_counter) < 2
        rack_tolerance_violation = node_num > 0 and max(rack_counter.values() or [0]) > ceil(node_num / 2)
        if rack_count_violation or rack_tolerance_violation:
            reasons = []
            if rack_count_violation:
                reasons.append("requires at least 2 racks")
            if rack_tolerance_violation:
                reasons.append("rack tolerance(1/2) violated")
            errors.append(
                err(
                    "weak_rack_constraint_violation",
                    f"affinity {affinity_name} {' and '.join(reasons)}, rack_counts={rack_counter}",
                )
            )
    elif disaster_tolerance_level == MAJORITY_ELECTION_DISTRI:
        if len(actual_sub_zone_set) < 2 and not has_single_node_tag:
            errors.append(
                err(
                    "majority_min_zone_violation",
                    f"affinity {affinity_name} requires at least 2 sub_zones, actual={sorted(actual_sub_zone_set)}",
                )
            )
        if node_num > 0 and max(zone_counter.values() or [0]) > ceil(node_num / 2):
            errors.append(
                err(
                    "majority_zone_violation",
                    f"affinity {affinity_name} zone majority violated, zone_counts={display_zone_counts(zone_counter)}",
                )
            )
        if max(rack_counter.values() or [0]) > 1:
            errors.append(
                err(
                    "majority_rack_unique_violation",
                    f"affinity {affinity_name} same rack cannot host more than 1 node, rack_counts={rack_counter}",
                )
            )
        if zone_counter:
            zone_values = sorted(zone_counter.values())
            if zone_values[-1] - zone_values[0] > 1:
                errors.append(
                    err(
                        "majority_balance_violation",
                        f"affinity {affinity_name} zone distribution should be near-even, "
                        f"zone_counts={display_zone_counts(zone_counter)}",
                    )
                )
    elif disaster_tolerance_level == CROSS_RACK:
        if len(actual_rack_set) < 2:
            errors.append(
                err(
                    "cross_rack_violation",
                    f"affinity {affinity_name} requires at least 2 racks, actual={sorted(actual_rack_set)}",
                )
            )
    elif disaster_tolerance_level == NONE:
        pass
    elif disaster_tolerance_level == MAX_EACH_ZONE_EQUAL:
        if zone_counter:
            zone_values = sorted(zone_counter.values())
            if zone_values[-1] - zone_values[0] > 1:
                errors.append(
                    err(
                        "zone_equal_violation",
                        f"affinity {affinity_name} requires near-equal zone distribution, "
                        f"zone_counts={display_zone_counts(zone_counter)}",
                    )
                )
    elif not disaster_tolerance_level:
        warnings.append(err("affinity_empty", "disaster_tolerance_level is empty"))
    else:
        warnings.append(
            err("affinity_unsupported", f"unsupported disaster_tolerance_level: {disaster_tolerance_level}")
        )

    if errors:
        return ABNORMAL, errors
    if warnings:
        return WARNING, warnings
    return NORMAL, []


def _build_logical_region_map(rows: list[dict[str, Any]], id_key: str) -> dict[str, str]:
    """Map id_key -> logical_city_name for rows with non-empty logical_city_name."""
    mapping: dict[str, str] = {}
    for row in rows:
        row_id = row.get(id_key)
        if row_id in [None, ""]:
            continue
        name = str(row.get("logical_city_name") or "").strip()
        if name:
            mapping[str(row_id)] = name
    return mapping


def build_city_logical_region_map(cities: list[dict[str, Any]]) -> dict[str, str]:
    """bk_city_id -> logical city name. Only rows with non-empty logical_city_name."""
    return _build_logical_region_map(cities, "bk_city_id")


def build_subzone_logical_region_map(subzones: list[dict[str, Any]]) -> dict[str, str]:
    """bk_sub_zone_id -> logical city name. Only rows with non-empty logical_city_name."""
    return _build_logical_region_map(subzones, "bk_sub_zone_id")


def evaluate(  # noqa: C901
    cluster_defs: list[dict[str, Any]],
    cluster_nodes: list[dict[str, Any]],
    subzones: list[dict[str, Any]],
    cities: list[dict[str, Any]],
) -> list[ClusterEval]:
    city_region_map = build_city_logical_region_map(cities)

    subzone_region_map = build_subzone_logical_region_map(subzones)
    subzone_name_map: dict[str, str] = {}
    for row in subzones:
        zone_id = row.get("bk_sub_zone_id")
        if zone_id in [None, ""]:
            continue
        subzone_name_map[str(zone_id)] = str(row.get("bk_sub_zone", "") or "")

    eval_map: dict[int, ClusterEval] = {}
    for row in cluster_defs:
        cluster_id = int(row.get("cluster_id"))
        eval_map[cluster_id] = ClusterEval(
            cluster_id=cluster_id,
            domain=str(row.get("immute_domain", "")),
            cluster_type=str(row.get("cluster_type", "")),
            cluster_region=str(row.get("cluster_region", "") or ""),
            has_single_node_tag=bool(row.get("has_single_node_tag", False)),
            affinity=str(row.get("disaster_tolerance_level", "") or ""),
            zone_list=normalize_to_str_set(row.get("zone_list")),
        )

    for row in cluster_nodes:
        raw_cluster_id = row.get("cluster_id")
        if raw_cluster_id is None:
            continue
        cluster_id = int(raw_cluster_id)
        if cluster_id not in eval_map:
            continue
        item = eval_map[cluster_id]
        set_name = str(row.get("set_name", "") or "unknown")
        city_id = row.get("bk_city_id")
        sub_zone = row.get("bk_sub_zone_id")
        rack = row.get("bk_rack_id")
        if not sub_zone:
            item.reasons.append(
                err(
                    "node_subzone_missing",
                    f"node {row.get('ip','')}:{row.get('port','')} set={row.get('set_name','')} has empty bk_sub_zone_id",
                )
            )
        if not rack:
            item.reasons.append(
                err(
                    "node_rack_missing",
                    f"node {row.get('ip','')}:{row.get('port','')} set={row.get('set_name','')} has empty bk_rack_id",
                )
            )
        resolved_region = ""
        if sub_zone:
            sub_zone_str = str(sub_zone)
            item.actual_sub_zones.add(sub_zone_str)
            # prefer subzone mapping first
            resolved_region = subzone_region_map.get(sub_zone_str, "")

        # fallback to machine city mapping when subzone mapping is unavailable
        if not resolved_region and city_id not in [None, ""]:
            resolved_region = city_region_map.get(str(city_id), "")

        if not resolved_region:
            item.reasons.append(
                err(
                    "node_region_mapping_missing",
                    f"node {row.get('ip','')}:{row.get('port','')} set={row.get('set_name','')} "
                    "has no logical_city_name mapping for bk_sub_zone_id or bk_city_id in subzones/cities json",
                )
            )
        else:
            item.actual_regions.add(resolved_region)
        if rack:
            item.actual_racks.add(str(rack))

    results = []
    for item in eval_map.values():
        cluster_rows = [row for row in cluster_nodes if int(row.get("cluster_id", -1)) == item.cluster_id]

        # replicaset/other: treat as one logical component; sharded: split by set_name
        components: dict[str, ComponentEval] = {}
        for row in cluster_rows:
            set_name = str(row.get("set_name", "") or "unknown")
            comp = components.setdefault(set_name, ComponentEval(set_name=set_name))

            city_id = row.get("bk_city_id")
            sub_zone = row.get("bk_sub_zone_id")
            rack = row.get("bk_rack_id")
            if not sub_zone:
                comp.reasons.append(
                    err(
                        "node_subzone_missing",
                        f"node {row.get('ip','')}:{row.get('port','')} has empty bk_sub_zone_id",
                    )
                )
            if not rack:
                comp.reasons.append(
                    err("node_rack_missing", f"node {row.get('ip','')}:{row.get('port','')} has empty bk_rack_id")
                )

            resolved_region = ""
            if sub_zone:
                sub_zone_str = str(sub_zone)
                comp.sub_zones.add(sub_zone_str)
                resolved_region = subzone_region_map.get(sub_zone_str, "")

            if not resolved_region and city_id not in [None, ""]:
                resolved_region = city_region_map.get(str(city_id), "")

            if not resolved_region:
                comp.reasons.append(
                    err(
                        "node_region_mapping_missing",
                        f"node {row.get('ip','')}:{row.get('port','')} has no logical_city_name in subzones/cities json",
                    )
                )
            else:
                comp.regions.add(resolved_region)

            if rack:
                comp.racks.add(str(rack))

            comp.nodes.append(
                {
                    "addr": f"{row.get('ip','')}:{row.get('port','')}",
                    "ip": str(row.get("ip", "") or ""),
                    "bk_cloud_id": str(row.get("bk_cloud_id", "") or ""),
                    "actual_sub_zone": str(sub_zone) if sub_zone not in [None, ""] else "",
                    "actual_rack": str(rack) if rack not in [None, ""] else "",
                    "instance_role": str(row.get("instance_role", "") or ""),
                }
            )

        if item.cluster_type == "MongoShardedCluster":
            grouped_components: dict[str, ComponentEval] = {}
            for set_name, comp in components.items():
                if not is_shardsvr_set(set_name):
                    grouped_components[set_name] = comp
                    continue
                group_key = build_shardsvr_group_key(comp.nodes)
                merged = grouped_components.setdefault(group_key, ComponentEval(set_name=group_key))
                merged.sub_zones.update(comp.sub_zones)
                merged.regions.update(comp.regions)
                merged.racks.update(comp.racks)
                merged.nodes.extend(comp.nodes)
                merged.reasons.extend(comp.reasons)
                merged.nodes = dedup_nodes_by_machine(merged.nodes)
            components = grouped_components

        component_states = []
        for set_name, comp in sorted(components.items()):
            if comp.reasons:
                component_states.append(ABNORMAL)
                item.reasons.append(f"[{set_name}] " + "; ".join(comp.reasons))
                item.component_details.append(
                    {
                        "set_name": set_name,
                        "zone_list": sorted(item.zone_list),
                        "actual_sub_zones": sorted(comp.sub_zones),
                        "actual_regions": sorted(comp.regions),
                        "actual_racks": sorted(comp.racks),
                        "nodes": comp.nodes,
                        "state": ABNORMAL,
                    }
                )
                continue

            if not item.has_single_node_tag:
                min_members = 2 if set_name == "mongos" else 3
                if len(comp.nodes) < min_members:
                    component_states.append(ABNORMAL)
                    item.reasons.append(
                        f"[{set_name}] "
                        + err(
                            "member_count_violation",
                            f"{set_name} requires at least {min_members} members, actual={len(comp.nodes)}",
                        )
                    )
                    item.component_details.append(
                        {
                            "set_name": set_name,
                            "zone_list": sorted(item.zone_list),
                            "actual_sub_zones": sorted(comp.sub_zones),
                            "actual_regions": sorted(comp.regions),
                            "actual_racks": sorted(comp.racks),
                            "nodes": comp.nodes,
                            "state": ABNORMAL,
                        }
                    )
                    continue

            # has_single_node_tag: skip min sub_zone count for CROS_SUBZONE / CROSS_SUBZONE_STRONG /
            # CROSS_SUBZONE_WEAK / MAJORITY_ELECTION_DISTRI (see check_affinity_rules docstring).
            comp_state, comp_reasons = check_affinity_rules(
                disaster_tolerance_level=item.affinity,
                cluster_region=item.cluster_region,
                zone_list=item.zone_list,
                actual_sub_zone_set=comp.sub_zones,
                actual_region_set=comp.regions,
                actual_rack_set=comp.racks,
                component_nodes=comp.nodes,
                zone_name_map=subzone_name_map,
                has_single_node_tag=item.has_single_node_tag,
            )
            component_states.append(comp_state)
            for reason in comp_reasons:
                item.reasons.append(f"[{set_name}] {reason}")
            item.component_details.append(
                {
                    "set_name": set_name,
                    "zone_list": sorted(item.zone_list),
                    "actual_sub_zones": sorted(comp.sub_zones),
                    "actual_regions": sorted(comp.regions),
                    "actual_racks": sorted(comp.racks),
                    "nodes": comp.nodes,
                    "state": comp_state,
                }
            )

        if ABNORMAL in component_states:
            item.state = ABNORMAL
        elif WARNING in component_states:
            item.state = WARNING
        else:
            item.state = NORMAL

        if not components:
            item.state = ABNORMAL
            item.reasons.append(err("component_missing", "no component nodes found"))

        results.append(item)
    return results


def extract_code(reason: str) -> str:
    if "code=" not in reason:
        return "unknown"
    return reason.split("code=", 1)[1].split(" ", 1)[0].strip()


def print_result(results: list[ClusterEval], summary_by_code: bool = False) -> int:
    total = len(results)
    success = sum(1 for item in results if item.state == NORMAL)
    warning = sum(1 for item in results if item.state == WARNING)
    abnormal = sum(1 for item in results if item.state == ABNORMAL)

    print("=== MongoDB Affinity Offline Check ===")
    print(f"total={total} success={success} warning={warning} abnormal={abnormal}")
    print("")

    if summary_by_code:
        code_counts: dict[str, int] = {}
        for item in results:
            for reason in item.reasons:
                code = extract_code(reason)
                code_counts[code] = code_counts.get(code, 0) + 1
        if code_counts:
            print("=== Summary By Code ===")
            for code, cnt in sorted(code_counts.items(), key=lambda kv: (-kv[1], kv[0])):
                print(f"{code}: {cnt}")
            print("")

    issue_items = [item for item in results if item.state in [WARNING, ABNORMAL]]
    if not issue_items:
        print("No warning/abnormal clusters.")
        return 0

    print("=== Warning/Abnormal Details ===")
    for item in sorted(issue_items, key=lambda row: row.cluster_id):
        print(
            f"- cluster_id={item.cluster_id} domain={item.domain} type={item.cluster_type} state={item.state} "
            f"affinity={item.affinity or 'EMPTY'} cluster_region={item.cluster_region or 'EMPTY'}"
        )
        print(
            f"  zone_list={sorted(item.zone_list)} actual_sub_zones={sorted(item.actual_sub_zones)} "
            f"actual_regions={sorted(item.actual_regions)} actual_racks={sorted(item.actual_racks)}"
        )
        details_to_print = item.component_details
        if item.cluster_type == "MongoShardedCluster":
            issue_components = [
                detail for detail in item.component_details if detail.get("state") in {WARNING, ABNORMAL}
            ]
            non_mongos_issue = [detail for detail in issue_components if detail.get("set_name") != "mongos"]
            if issue_components and not non_mongos_issue:
                details_to_print = [detail for detail in issue_components if detail.get("set_name") == "mongos"]
            elif issue_components:
                details_to_print = issue_components

        if details_to_print:
            print("  components:")
            for detail in details_to_print:
                print(
                    f"    - {detail['set_name']} "
                    f"zone_list={detail['zone_list']} "
                    f"actual_sub_zones={detail['actual_sub_zones']} "
                    f"actual_regions={detail['actual_regions']} "
                    f"actual_racks={detail['actual_racks']}"
                )
                for node in detail["nodes"]:
                    print(
                        f"      instance={node['addr']} "
                        f"actual_sub_zone={node['actual_sub_zone']} "
                        f"actual_rack={node.get('actual_rack', '')} "
                        f"instance_role={node.get('instance_role', '')}"
                    )
        for reason in item.reasons:
            print(f"  reason=[{item.domain}] {reason}")
    return 0 if abnormal == 0 else 2


def main() -> int:
    try:
        args = parse_args()
        cluster_defs = load_json_file(args.cluster_defs_json)
        cluster_nodes = load_json_file(args.cluster_nodes_json)
        subzones = load_json_file(args.subzones_json)
        cities = load_json_file(args.cities_json)
        results = evaluate(cluster_defs, cluster_nodes, subzones, cities)
        return print_result(results, summary_by_code=args.summary_by_code)
    except Exception as err:  # noqa: BLE001
        print(f"ERROR: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
