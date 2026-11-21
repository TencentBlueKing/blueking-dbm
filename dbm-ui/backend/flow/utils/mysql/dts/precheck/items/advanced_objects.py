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

from dataclasses import asdict, dataclass, field

from django.utils.translation import gettext_lazy as _

from backend.flow.utils.mysql.dts.precheck.base import CheckContext, CheckLevel, CheckResult, register
from backend.flow.utils.mysql.dts.precheck.collector import InstanceCollector, PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.scope import resolve_schemas
from backend.flow.utils.mysql.dts.precheck.sqlutil import quote_str_list
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class ObjectKind(StrStructuredEnum):
    FUNCTION = EnumField("function", _("FUNCTION"))
    TRIGGER = EnumField("trigger", _("TRIGGER"))
    EVENT = EnumField("event", _("EVENT"))
    PROCEDURE = EnumField("procedure", _("PROCEDURE"))


@dataclass
class ObjectRow:
    schema: str
    name: str
    extra: dict = field(default_factory=dict)


OBJECT_SQL: dict[ObjectKind, str] = {
    ObjectKind.FUNCTION: (
        "SELECT ROUTINE_SCHEMA, ROUTINE_NAME "
        "FROM information_schema.ROUTINES "
        "WHERE ROUTINE_TYPE = 'FUNCTION' AND ROUTINE_SCHEMA IN {schemas}"
    ),
    ObjectKind.PROCEDURE: (
        "SELECT ROUTINE_SCHEMA, ROUTINE_NAME "
        "FROM information_schema.ROUTINES "
        "WHERE ROUTINE_TYPE = 'PROCEDURE' AND ROUTINE_SCHEMA IN {schemas}"
    ),
    ObjectKind.TRIGGER: (
        "SELECT TRIGGER_SCHEMA, TRIGGER_NAME, EVENT_OBJECT_TABLE "
        "FROM information_schema.TRIGGERS "
        "WHERE TRIGGER_SCHEMA IN {schemas}"
    ),
    ObjectKind.EVENT: (
        "SELECT EVENT_SCHEMA, EVENT_NAME " "FROM information_schema.EVENTS " "WHERE EVENT_SCHEMA IN {schemas}"
    ),
}

FORBIDDEN_KINDS = (
    ObjectKind.FUNCTION,
    ObjectKind.TRIGGER,
    ObjectKind.EVENT,
)
DISPLAY_LIMIT = 50


def _collect(
    collector: InstanceCollector,
    kind: ObjectKind,
    schemas: list[str],
) -> list[ObjectRow]:
    sql = OBJECT_SQL[kind].format(schemas=quote_str_list(schemas))
    rows = collector.query(sql)
    result = []
    for row in rows:
        if kind in (ObjectKind.FUNCTION, ObjectKind.PROCEDURE):
            schema, name = row.get("ROUTINE_SCHEMA"), row.get("ROUTINE_NAME")
            extra = {}
        elif kind == ObjectKind.TRIGGER:
            schema, name = row.get("TRIGGER_SCHEMA"), row.get("TRIGGER_NAME")
            extra = {"event_object_table": row.get("EVENT_OBJECT_TABLE")}
        else:
            schema, name = row.get("EVENT_SCHEMA"), row.get("EVENT_NAME")
            extra = {}
        result.append(ObjectRow(schema=schema or "", name=name or "", extra=extra))
    return result


def _forbid(rows: list[ObjectRow], kind: ObjectKind) -> CheckResult:
    total = len(rows)
    return CheckResult(
        ok=total == 0,
        code=f"advanced_objects.forbid_{kind.value}",
        message=(
            _("源端范围内不存在 {}").format(kind.value.upper())
            if total == 0
            else _("源端范围内存在 {} 个禁止同步的 {}").format(total, kind.value.upper())
        ),
        level=CheckLevel.FAIL,
        details={
            "kind": kind.value,
            "total": total,
            "displayed": [asdict(row) for row in rows[:DISPLAY_LIMIT]],
            "truncated": total > DISPLAY_LIMIT,
        },
    )


@register("advanced_objects", _("高级对象检查"))
def run(ctx: CheckContext) -> list[CheckResult]:
    schemas = resolve_schemas(ctx.scope, ctx.source.user_schemas())
    results = []
    for kind in FORBIDDEN_KINDS:
        try:
            rows = _collect(ctx.source, kind, schemas)
            results.append(_forbid(rows, kind))
        except PrecheckCollectError as exc:
            results.append(
                CheckResult(
                    ok=False,
                    code="advanced_objects.collect_error",
                    message=_("{} 采集失败: {}").format(kind.value, exc),
                    level=CheckLevel.FAIL,
                    details={"kind": kind.value},
                )
            )
        except Exception as exc:
            results.append(
                CheckResult(
                    ok=False,
                    code="advanced_objects.rule_error",
                    message=_("{} 判定失败: {}").format(kind.value, exc),
                    level=CheckLevel.FAIL,
                    details={"kind": kind.value},
                )
            )
    return results
