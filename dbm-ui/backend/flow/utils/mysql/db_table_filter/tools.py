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
import re
from typing import List

from django.utils.translation import ugettext_lazy as _

from .exception import DbTableFilterValidateException


def contain_glob(p: str) -> bool:
    return "*" in p or "?" in p or "%" in p


def glob_check(patterns: List[str]):
    r1 = re.compile(r"^[%?]+$")
    r2 = re.compile(r"^\*+$")

    for p in patterns:
        if contain_glob(p):
            if len(patterns) > 1:
                raise DbTableFilterValidateException(msg=_("使用通配符时, 只能有一个模式: {}").format(patterns))

            if ("%" in p or "?" in p) and r1.match(p):
                raise DbTableFilterValidateException(msg=_("% ? 不能独立使用"))

            if "*" in p and not r2.match(p):
                raise DbTableFilterValidateException(msg=_("* 只能独立使用"))


def replace_glob(p: str) -> str:
    return p.replace("*", ".*").replace("%", ".*").replace("?", ".")


def _build_regexp(parts: List[str], template: str) -> str:
    if parts:
        return template.format("|".join(parts))


def build_include_regexp(parts: List[str]) -> str:
    return _build_regexp(parts, r"(?=(?:({})))")


def build_exclude_regexp(parts: List[str]) -> str:
    return _build_regexp(parts, r"(?!(?:({})))")
