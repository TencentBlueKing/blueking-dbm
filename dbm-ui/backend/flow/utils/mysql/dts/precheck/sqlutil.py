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

from django.utils.translation import gettext as _

from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError

# MySQL 库名允许字母数字、下划线、美元符和连字符；作为字符串字面量拼进 IN (...)。
_MYSQL_IDENTIFIER = re.compile(r"^[0-9A-Za-z_$\-]{1,64}$")


def quote_str_list(names: list[str]) -> str:
    if not names:
        raise PrecheckCollectError(_("SQL IN 列表不能为空"))
    invalid = [name for name in names if not isinstance(name, str) or not _MYSQL_IDENTIFIER.fullmatch(name)]
    if invalid:
        raise PrecheckCollectError(_("非法 MySQL 库名: {!r}").format(invalid[0]))
    return "({})".format(", ".join(f"'{name}'" for name in names))
