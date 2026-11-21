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

_BINLOG_VARS = ("log_bin", "binlog_format", "binlog_row_image", "server_id")


def _is_on(value: str) -> bool:
    return value.strip().lower() in {"on", "1", "true"}


def _check_log_bin(variables: dict[str, str]) -> CheckResult:
    value = variables.get("log_bin", "")
    ok = _is_on(value)
    return CheckResult(
        ok=ok,
        code="binlog.log_bin",
        message=_("源端 log_bin=ON") if ok else _("源端 log_bin 未开启"),
        level=CheckLevel.FAIL,
        details={"side": "source", "log_bin": value},
    )


def _check_binlog_format(variables: dict[str, str]) -> CheckResult:
    value = variables.get("binlog_format", "")
    ok = value.strip().upper() == "ROW"
    return CheckResult(
        ok=ok,
        code="binlog.binlog_format",
        message=_("源端 binlog_format=ROW") if ok else _("源端 binlog_format 不是 ROW"),
        level=CheckLevel.FAIL,
        details={"side": "source", "binlog_format": value},
    )


def _check_binlog_row_image(variables: dict[str, str]) -> CheckResult:
    value = variables.get("binlog_row_image", "")
    ok = value.strip().upper() == "FULL"
    return CheckResult(
        ok=ok,
        code="binlog.binlog_row_image",
        message=_("源端 binlog_row_image=FULL") if ok else _("源端 binlog_row_image 不是 FULL"),
        level=CheckLevel.FAIL,
        details={"side": "source", "binlog_row_image": value},
    )


def _check_server_id(variables: dict[str, str]) -> CheckResult:
    value = variables.get("server_id", "")
    try:
        server_id = int(value)
    except (TypeError, ValueError):
        server_id = 0
    ok = server_id != 0
    return CheckResult(
        ok=ok,
        code="binlog.server_id",
        message=_("源端 server_id ≠ 0") if ok else _("源端 server_id 为 0 或无法解析"),
        level=CheckLevel.FAIL,
        details={"side": "source", "server_id": value},
    )


@register("binlog", _("binlog参数检查"))
def run(ctx: CheckContext) -> list[CheckResult]:
    variables = ctx.source.global_variables(list(_BINLOG_VARS))
    return [
        _check_log_bin(variables),
        _check_binlog_format(variables),
        _check_binlog_row_image(variables),
        _check_server_id(variables),
    ]
