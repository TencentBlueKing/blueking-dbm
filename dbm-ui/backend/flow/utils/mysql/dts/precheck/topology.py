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
from backend.flow.utils.mysql.dts.precheck.base import CheckItem, CheckLevel, CheckResult
from backend.flow.utils.mysql.dts.sync_scope_overlap import (
    ScopeObjectSet,
    landing_object_set,
    objects_overlap,
    source_object_set,
)

SOURCE_LANDING = "source_landing"
ROUTE_COVERAGE = "route_coverage"

SOURCE_LANDING_ITEM = CheckItem(code=SOURCE_LANDING, name=_("多源落点冲突"), run=lambda _ctx: [])
ROUTE_COVERAGE_ITEM = CheckItem(code=ROUTE_COVERAGE, name=_("路由覆盖"), run=lambda _ctx: [])


def _passed(code: str, message: str) -> CheckResult:
    return CheckResult(ok=True, code=code, message=message, level=CheckLevel.FAIL)


def _failed(code: str, message: str) -> CheckResult:
    return CheckResult(ok=False, code=code, message=message, level=CheckLevel.FAIL)


def _object_text(key: tuple[str, str]) -> str:
    return f"{key[0]}.{key[1]}"


def landing_conflicts(pairs: list[dict]) -> dict[str, list[CheckResult]]:
    """many_to_one：多个源落到同一个目标时，落地库表不能重叠。"""
    parsed = [(pair, landing_object_set(_parse_sync_scope(pair.get("sync_scope") or {}))) for pair in pairs]
    results = {}
    for pair, left in parsed:
        overlapped = []
        for other, right in parsed:
            if other["pair_key"] == pair["pair_key"]:
                continue
            if objects_overlap(left, right):
                overlapped.append(str(other["source_cluster_id"]))
        if overlapped:
            results[pair["pair_key"]] = [
                _failed(
                    "source_landing.overlap",
                    _("与源集群 {} 落到同一目标库表").format("、".join(overlapped)),
                )
            ]
        else:
            results[pair["pair_key"]] = [_passed("source_landing.ok", _("多个源的落地库表不重叠"))]
    return results


def _covers(left: tuple[str, str], right: tuple[str, str]) -> bool:
    return objects_overlap(
        ScopeObjectSet(includes=frozenset([left])),
        ScopeObjectSet(includes=frozenset([right])),
    )


def route_coverage(pairs: list[dict]) -> dict[str, list[CheckResult]]:
    """one_to_many：没有路由时同一范围复制到每个目标；有路由时源对象不能被多条路由覆盖。"""
    results = {}
    for pair in pairs:
        parsed = _parse_sync_scope(pair.get("sync_scope") or {})
        if not parsed.table_routes:
            results[pair["pair_key"]] = [_passed("route_coverage.replicated", _("未配置 table_routes，同一同步范围复制到每个目标"))]
            continue
        source_keys = sorted(source_object_set(parsed).includes)
        route_keys = [(route.source_schema(), route.source_table_name()) for route in parsed.table_routes]
        doubled = [
            _object_text(key)
            for key in source_keys
            if sum(1 for route_key in route_keys if _covers(key, route_key)) > 1
        ]
        if doubled:
            results[pair["pair_key"]] = [
                _failed("route_coverage.overlap", _("源对象被多条路由覆盖: {}").format("、".join(doubled[:20])))
            ]
            continue
        results[pair["pair_key"]] = [_passed("route_coverage.ok", _("路由没有把同一源对象分到多处"))]
    return results


def topology_results(topology: str, pairs: list[dict]) -> tuple[CheckItem, dict[str, list[CheckResult]]]:
    if topology == MigrateTopology.MANY_TO_ONE.value:
        return SOURCE_LANDING_ITEM, landing_conflicts(pairs)
    if topology == MigrateTopology.ONE_TO_MANY.value:
        return ROUTE_COVERAGE_ITEM, route_coverage(pairs)
    return SOURCE_LANDING_ITEM, {}
