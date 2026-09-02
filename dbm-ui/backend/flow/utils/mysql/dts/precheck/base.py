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

from dataclasses import dataclass, field
from typing import Callable

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from backend.flow.utils.mysql.dts.precheck.collector import InstanceCollector, PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class CheckLevel(StrStructuredEnum):
    FAIL = EnumField("fail", _("fail"))
    WARN = EnumField("warn", _("warn"))


@dataclass
class CheckResult:
    ok: bool
    code: str
    message: str
    level: CheckLevel = CheckLevel.FAIL
    details: dict = field(default_factory=dict)


@dataclass
class CheckContext:
    source: InstanceCollector
    target: InstanceCollector
    scope: SyncScope


@dataclass
class CheckItem:
    code: str
    name: str
    run: Callable[[CheckContext], list[CheckResult]]


_REGISTRY: dict[str, CheckItem] = {}


def collect_error_code(item_code: str) -> str:
    """采集失败在摘要里占用的行标识。重试成功后由摘要写入删掉这一行。"""
    return f"{item_code}.collect_error"


def register(code: str, name: str):
    """登记检查项。摘要里这个大项占一列，run 返回的 CheckResult 会收成通过、警告或失败。"""

    def deco(fn):
        if code in _REGISTRY:
            raise ImproperlyConfigured(f"duplicate precheck item: {code}")
        _REGISTRY[code] = CheckItem(code=code, name=name, run=fn)
        return fn

    return deco


def get_item(code: str) -> CheckItem:
    try:
        return _REGISTRY[code]
    except KeyError as exc:
        raise ImproperlyConfigured(f"unknown precheck item: {code}") from exc


def all_items() -> list[CheckItem]:
    return list(_REGISTRY.values())


def run_item(item: CheckItem, ctx: CheckContext) -> list[CheckResult]:
    try:
        return list(item.run(ctx))
    except PrecheckCollectError as exc:
        return [
            CheckResult(
                ok=False,
                code=collect_error_code(item.code),
                message=str(exc),
                level=CheckLevel.FAIL,
            )
        ]
