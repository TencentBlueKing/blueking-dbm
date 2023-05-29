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
import itertools
from typing import List

from django.utils.translation import ugettext_lazy as _

from .exception import DbTableFilterValidateException
from .tools import build_exclude_regexp, build_include_regexp, glob_check, replace_glob


class DbTableFilter(object):
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

        self.system_table_parts = []
        self.system_db_parts = []

        self._validate()
        self._build_db_filter_regexp()
        self._build_table_filter_regexp()

    def _validate(self):
        if not self.include_db_patterns or not self.include_table_patterns:
            raise DbTableFilterValidateException(msg=_("include patterns 不能为空"))

        if not (
            (self.exclude_table_patterns and self.exclude_table_patterns)
            or (not self.exclude_db_patterns and not self.exclude_table_patterns)
        ):
            raise DbTableFilterValidateException(msg=_("exclude patterns 要么同时为空, 要么都不为空"))

        for patterns in [
            self.include_db_patterns,
            self.include_table_patterns,
            self.exclude_db_patterns,
            self.exclude_table_patterns,
        ]:
            glob_check(patterns)

    def _build_db_filter_regexp(self):
        include_parts = ["{}$".format(replace_glob(db)) for db in self.include_db_patterns]
        exclude_parts = ["{}$".format(replace_glob(db)) for db in self.exclude_db_patterns] + self.system_db_parts

        self.db_filter_include_regex = build_include_regexp(include_parts)
        self.db_filter_exclude_regex = build_exclude_regexp(exclude_parts)

    def _build_table_filter_regexp(self):
        include_parts = [
            r"{}\.{}$".format(replace_glob(ele[0]), replace_glob(ele[1]))
            for ele in itertools.product(self.include_db_patterns, self.include_table_patterns)
        ]

        exclude_parts = [
            r"{}\.{}$".format(replace_glob(ele[0]), replace_glob(ele[1]))
            for ele in itertools.product(self.exclude_db_patterns, self.exclude_table_patterns)
        ] + self.system_table_parts

        self.table_filter_include_regex = build_include_regexp(include_parts)
        self.table_filter_exclude_regex = build_exclude_regexp(exclude_parts)

    def table_filter_regexp(self) -> str:
        return r"^{}{}".format(self.table_filter_include_regex, self.table_filter_exclude_regex)

    def db_filter_regexp(self) -> str:
        return r"^{}{}".format(self.db_filter_include_regex, self.db_filter_exclude_regex)

    def table_filter_exclude_regexp_as_include(self) -> str:
        return self.table_filter_exclude_regex.replace("!", "=", 1)

    def db_filter_exclude_regexp_as_include(self) -> str:
        return self.db_filter_exclude_regex.replace("!", "=", 1)

    def inject_system_dbs(self, system_dbs: List[str]):
        self.system_table_parts = [r"{}\..*$".format(replace_glob(sd)) for sd in system_dbs]
        self.system_db_parts = [r"{}$".format(replace_glob(sd)) for sd in system_dbs]

        self._build_db_filter_regexp()
        self._build_table_filter_regexp()
