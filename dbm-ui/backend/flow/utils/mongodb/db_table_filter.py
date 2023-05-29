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

from backend.flow.utils.mysql.db_table_filter.exception import DbTableFilterValidateException


class MongoDbTableFilter(object):

    db_match_regex = re.compile(r"[*a-zA-Z0-9_-]{1,64}")
    table_match_regex = re.compile(r"[*a-zA-Z0-9_-]{1,255}")

    def __init__(
        self,
        include_db_patterns: List[str],
        include_table_patterns: List[str],
        exclude_db_patterns: List[str],
        exclude_table_patterns: List[str],
    ):
        self.include_db_patterns = include_db_patterns
        self.include_table_patterns = include_table_patterns
        self.exclude_db_patterns = exclude_db_patterns
        self.exclude_table_patterns = exclude_table_patterns

        self._validate()

    def _validate(self):
        # include 组不允许为空
        if not self.include_db_patterns or not self.include_table_patterns:
            raise DbTableFilterValidateException(msg=_("include patterns 不能为空"))

        # exclude 组要么同时为空，要么同时不为空
        if not (
            (self.exclude_table_patterns and self.exclude_table_patterns)
            or (not self.exclude_db_patterns and not self.exclude_table_patterns)
        ):
            raise DbTableFilterValidateException(msg=_("exclude patterns 要么同时为空, 要么都不为空"))

        # 校验库名合法
        self._regex_check(self.include_db_patterns, pattern="db")
        self._regex_check(self.exclude_table_patterns, pattern="db")

        # 校验表名合法
        self._regex_check(self.include_table_patterns, pattern="table")
        self._regex_check(self.exclude_table_patterns, pattern="table")

    def _regex_check(self, check_list, pattern):
        if not check_list:
            return
        # TODO: 库表名精确的时候是否需要校验存在性
        match_pattern = self.db_match_regex if pattern == "db" else self.table_match_regex
        for check in check_list:
            if not match_pattern.match(check):
                raise DbTableFilterValidateException(msg=_("{}校验不成功! 只能包含字母、数字或通配*且不超过最大长度").format(pattern))
