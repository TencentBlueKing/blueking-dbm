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

from django.utils.translation import gettext as _

from backend.flow.utils.mysql.dts.constants import MigrateTopology
from backend.flow.utils.mysql.dts.migrate_plan import _parse_sync_scope

_TOPOLOGY_BLOCK = {
    MigrateTopology.ONE_TO_ONE.value: "one_to_one",
    MigrateTopology.MANY_TO_ONE.value: "many_to_one",
    MigrateTopology.ONE_TO_MANY.value: "one_to_many",
}


def scope_label(raw: dict | None) -> str:
    """摘要里区分同一对集群上的不同同步范围。"""
    raw = raw or {}
    routes = [item for item in (raw.get("table_routes") or []) if isinstance(item, dict)]
    if routes:
        parts = []
        for route in routes:
            database = (route.get("source_db_pattern") or route.get("source_db") or "").strip()
            table = (route.get("source_table_pattern") or route.get("source_table") or "*").strip() or "*"
            if database:
                parts.append(f"{database}.{table}")
        return ",".join(parts) or "table_routes"
    databases = [item.strip() for item in (raw.get("db_patterns") or []) if isinstance(item, str) and item.strip()]
    tables = [item.strip() for item in (raw.get("table_patterns") or []) if isinstance(item, str) and item.strip()]
    return "{}/{}".format(",".join(databases) or "*", ",".join(tables) or "*")


def precheck_scope(raw: dict | None) -> dict:
    """把迁移单 sync_scope 收成预检查检查项已经在用的范围。"""
    parsed = _parse_sync_scope(raw or {})
    if not parsed.do_dbs and not parsed.table_routes:
        raise ValueError(_("同步范围为空，请填写 db_patterns / table_patterns 或 table_routes"))

    source_tables = []
    if parsed.table_routes:
        for route in parsed.table_routes:
            database = route.source_schema()
            if not database:
                continue
            table = route.source_table_name()
            entry = {"db": database}
            if table and table != "*":
                entry["tables"] = [table]
            source_tables.append(entry)
    else:
        tables = []
        for item in parsed.do_tables:
            name = str(item.get("table") or "").strip()
            if name and name not in tables:
                tables.append(name)
        for database in parsed.do_dbs:
            entry = {"db": database}
            if tables:
                entry["tables"] = list(tables)
            source_tables.append(entry)
    if not source_tables:
        raise ValueError(_("同步范围解析后没有可检查的源库"))

    return {
        "source_tables": source_tables,
        "do_dbs": list(parsed.do_dbs),
        "ignore_dbs": list(parsed.ignore_dbs),
        "do_tables": list(parsed.do_tables),
        "ignore_tables": list(parsed.ignore_tables),
        "table_routes": [
            {
                "source_db": route.source_schema(),
                "source_db_pattern": route.source_db_pattern,
                "source_table": route.source_table_name(),
                "source_table_pattern": route.source_table_pattern,
                "target_db": route.target_db,
                "target_table": route.target_table,
            }
            for route in parsed.table_routes
        ],
    }


def _cluster_id(side: dict | None, field_name: str) -> int:
    if not isinstance(side, dict) or side.get("cluster_id") in (None, ""):
        raise ValueError(_("{} 缺少 cluster_id").format(field_name))
    try:
        return int(side["cluster_id"])
    except (TypeError, ValueError) as exc:
        raise ValueError(_("{}.cluster_id 必须是整数").format(field_name)) from exc


def _address(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    try:
        ip, port_text = text.rsplit(":", 1)
        port = int(port_text)
    except (ValueError, TypeError) as exc:
        raise ValueError(_("{} 格式必须为 ip:port").format(field_name)) from exc
    if not ip or not 1 <= port <= 65535:
        raise ValueError(_("{} 格式必须为 ip:port").format(field_name))
    return f"{ip}:{port}"


def _pair(infos_index: int, topology: str, source: dict | None, target: dict | None) -> dict:
    source_id = _cluster_id(source, "source")
    target_id = _cluster_id(target, "target")
    if source_id == target_id:
        raise ValueError(_("源集群和目标集群不能相同: {}").format(source_id))
    source = source or {}
    target = target or {}
    if source.get("source_host") and source.get("source_instance_id"):
        raise ValueError(_("source_host 与 source_instance_id 不能同时指定"))
    raw_scope = source.get("sync_scope") or {}
    adapted = precheck_scope(raw_scope)
    return {
        "pair_key": f"{infos_index}:{source_id}:{target_id}",
        "infos_index": infos_index,
        "topology": topology,
        "source_cluster_id": source_id,
        "target_cluster_id": target_id,
        "source_host": _address(source.get("source_host") or "", "source_host"),
        "source_instance_id": source.get("source_instance_id"),
        "target_spider": _address(target.get("target_spider") or "", "target_spider"),
        "sync_scope": raw_scope,
        "scope_label": scope_label(raw_scope),
        "source_tables": adapted["source_tables"],
        "precheck_scope": adapted,
    }


def _migrates(details: dict):
    """与迁移单同一套入口：有 infos 就只用行内 migrate，否则用顶层 migrate。"""
    infos = details.get("infos") or []
    if infos:
        if details.get("dts_resource") or details.get("migrate"):
            raise ValueError(_("有 infos 时不要再传顶层 migrate / dts_resource"))
        for index, row in enumerate(infos):
            migrate = (row or {}).get("migrate") if isinstance(row, dict) else None
            if not isinstance(migrate, dict):
                raise ValueError(_("infos[{}] 缺少 migrate").format(index))
            topology = migrate.get("topology")
            if topology != MigrateTopology.ONE_TO_ONE.value:
                raise ValueError(_("infos[{}] 仅支持 one_to_one 拓扑，实际为 {}").format(index, topology))
            yield index, migrate
        return
    migrate = details.get("migrate")
    if isinstance(migrate, dict):
        yield 0, migrate
        return
    raise ValueError(_("必须提供migrate，或多行 infos"))


def expand_precheck_pairs(details: dict) -> list[dict]:
    """把迁移单的 migrate 展开成一对源/目标一行。

    入口与迁移单相同：infos 多行且只能是 one_to_one；否则用顶层 migrate。
    one_to_one 一行；many_to_one 每个源一行；one_to_many 每个目标一行。
    """
    pairs = []
    for index, migrate in _migrates(details or {}):
        topology = migrate.get("topology")
        block_name = _TOPOLOGY_BLOCK.get(topology)
        if block_name is None:
            raise ValueError(_("不支持的迁移拓扑: {}").format(topology))
        block = migrate.get(block_name) or {}
        if not isinstance(block, dict) or not block:
            raise ValueError(_("拓扑 {} 必须填写 migrate.{}").format(topology, block_name))
        if topology == MigrateTopology.MANY_TO_ONE.value:
            sources = block.get("sources") or []
            if not sources:
                raise ValueError(_("many_to_one 缺少 sources"))
            pairs.extend(_pair(index, topology, source, block.get("target")) for source in sources)
            continue
        if topology == MigrateTopology.ONE_TO_MANY.value:
            targets = block.get("targets") or []
            if not targets:
                raise ValueError(_("one_to_many 缺少 targets"))
            pairs.extend(_pair(index, topology, block.get("source"), target) for target in targets)
            continue
        pairs.append(_pair(index, topology, block.get("source"), block.get("target")))
    if not pairs:
        raise ValueError(_("必须提供migrate，或多行 infos"))
    return pairs
