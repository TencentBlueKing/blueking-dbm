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

from django.utils.translation import gettext_lazy as _

from backend.flow.utils.mysql.dts.precheck.base import CheckContext, CheckLevel, CheckResult, register
from backend.flow.utils.mysql.dts.precheck.constants import DTS_PRECHECK_ONE_GB

_VAR_NAMES = ("max_allowed_packet", "character_set_server", "sql_mode")


def _as_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _mode_set(raw: str) -> set[str]:
    return {part.strip().upper() for part in str(raw or "").split(",") if part.strip()}


def _packet_gt_source(source_vars: dict[str, str], target_vars: dict[str, str]) -> CheckResult:
    source_value = _as_int(source_vars.get("max_allowed_packet", "0"))
    target_value = _as_int(target_vars.get("max_allowed_packet", "0"))
    ok = target_value >= source_value
    return CheckResult(
        ok=ok,
        code="warnings.max_allowed_packet_ge_source",
        message=_("目标端 max_allowed_packet 不小于源端") if ok else _("目标端 max_allowed_packet 小于源端"),
        level=CheckLevel.WARN,
        details={"source": source_value, "target": target_value},
    )


def _packet_gt_one_gb(target_vars: dict[str, str]) -> CheckResult:
    target_value = _as_int(target_vars.get("max_allowed_packet", "0"))
    ok = target_value > DTS_PRECHECK_ONE_GB
    return CheckResult(
        ok=ok,
        code="warnings.max_allowed_packet_gt_1gb",
        message=_("目标端 max_allowed_packet > 1GB") if ok else _("目标端 max_allowed_packet 未大于 1GB"),
        level=CheckLevel.WARN,
        details={"target": target_value, "required_gt": DTS_PRECHECK_ONE_GB},
    )


def _charset_same(source_vars: dict[str, str], target_vars: dict[str, str]) -> CheckResult:
    source_value = source_vars.get("character_set_server", "")
    target_value = target_vars.get("character_set_server", "")
    ok = bool(source_value) and source_value.lower() == target_value.lower()
    return CheckResult(
        ok=ok,
        code="warnings.character_set_server",
        message=_("源端与目标端 character_set_server 一致") if ok else _("源端与目标端 character_set_server 不一致"),
        level=CheckLevel.WARN,
        details={"source": source_value, "target": target_value},
    )


def _sql_mode_same(source_vars: dict[str, str], target_vars: dict[str, str]) -> CheckResult:
    source_value = source_vars.get("sql_mode", "")
    target_value = target_vars.get("sql_mode", "")
    ok = _mode_set(source_value) == _mode_set(target_value)
    return CheckResult(
        ok=ok,
        code="warnings.sql_mode",
        message=_("源端与目标端 sql_mode 一致") if ok else _("源端与目标端 sql_mode 不一致"),
        level=CheckLevel.WARN,
        details={"source": source_value, "target": target_value},
    )


@register("warnings", _("警告项检查"))
def run(ctx: CheckContext) -> list[CheckResult]:
    source_vars = ctx.source.global_variables(list(_VAR_NAMES))
    target_vars = ctx.target.global_variables(list(_VAR_NAMES))
    return [
        _packet_gt_source(source_vars, target_vars),
        # _packet_gt_one_gb(target_vars),  # 暂缓
        _charset_same(source_vars, target_vars),
        _sql_mode_same(source_vars, target_vars),
    ]
