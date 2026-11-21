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

from types import SimpleNamespace
from unittest import TestCase

from backend.flow.utils.mysql.dts.precheck.base import CheckContext, get_item, run_item
from backend.flow.utils.mysql.dts.precheck.collector import Endpoint, PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.items import version
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope


class VersionRuleTest(TestCase):
    def test_in_range_accepts_supported_versions_and_ignores_patch(self):
        for raw in ("5.5.0", "5.7.20-tmysql-3.4.2-log", "8.0.32"):
            with self.subTest(raw=raw):
                self.assertTrue(version._in_range(raw, cluster_id=1, side="source").ok)

    def test_in_range_rejects_unsupported_or_unparseable_versions(self):
        for raw in ("5.1.73", "8.1.0", "not-a-version"):
            with self.subTest(raw=raw):
                result = version._in_range(raw, cluster_id=1, side="source")
                self.assertFalse(result.ok)
                self.assertEqual(result.code, "version.in_range")

    def test_destination_comparison_does_not_compare_patch(self):
        self.assertTrue(version._dest_ge_source("5.7.44", "5.7.20").ok)
        self.assertTrue(version._dest_ge_source("5.7.20", "8.0.1").ok)

    def test_destination_downgrade_fails(self):
        result = version._dest_ge_source("8.0.32", "5.7.44")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "version.dest_ge_source")

    def test_collection_error_is_normalized_by_framework(self):
        class FailingCollector:
            endpoint = Endpoint("127.0.0.1", 3306, 0, 1)

            def mysql_version(self):
                raise PrecheckCollectError("DRS failed")

        ctx = CheckContext(
            source=FailingCollector(),
            target=SimpleNamespace(),
            scope=SyncScope(),
        )
        results = run_item(get_item("version"), ctx)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "version.collect_error")
