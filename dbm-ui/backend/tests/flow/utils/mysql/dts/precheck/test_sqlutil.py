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

from unittest import TestCase

from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.sqlutil import quote_str_list


class QuoteStrListTest(TestCase):
    def test_quotes_valid_names(self):
        self.assertEqual(quote_str_list(["db_1", "db$2", "bk-dbm"]), "('db_1', 'db$2', 'bk-dbm')")

    def test_rejects_dangerous_or_oversized_names(self):
        invalid_names = [
            "db'name",
            "db`name",
            "db;drop",
            "x" * 65,
        ]
        for name in invalid_names:
            with self.subTest(name=name), self.assertRaises(PrecheckCollectError):
                quote_str_list([name])

    def test_rejects_empty_list(self):
        with self.assertRaises(PrecheckCollectError):
            quote_str_list([])
