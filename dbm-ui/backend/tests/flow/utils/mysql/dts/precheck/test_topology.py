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

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.precheck.topology import landing_conflicts, route_coverage


def _pair(pair_key, source_id, scope):
    return {"pair_key": pair_key, "source_cluster_id": source_id, "sync_scope": scope}


class LandingConflictTest(SimpleTestCase):
    def test_overlapping_sources_fail_and_disjoint_sources_pass(self):
        overlapped = landing_conflicts(
            [
                _pair("a", 100, {"db_patterns": ["db_a"], "table_patterns": ["*"]}),
                _pair("b", 101, {"db_patterns": ["db_a"], "table_patterns": ["t1"]}),
            ]
        )
        self.assertFalse(overlapped["a"][0].ok)
        self.assertIn("101", overlapped["a"][0].message)

        disjoint = landing_conflicts(
            [
                _pair("a", 100, {"db_patterns": ["db_a"], "table_patterns": ["*"]}),
                _pair("b", 101, {"db_patterns": ["db_b"], "table_patterns": ["*"]}),
            ]
        )
        self.assertTrue(disjoint["a"][0].ok)
        self.assertTrue(disjoint["b"][0].ok)


class RouteCoverageTest(SimpleTestCase):
    def test_without_routes_same_scope_is_replicated(self):
        results = route_coverage([_pair("a", 100, {"db_patterns": ["db_a"], "table_patterns": ["*"]})])
        self.assertTrue(results["a"][0].ok)
        self.assertIn("复制", results["a"][0].message)

    def test_overlapping_routes_fail(self):
        results = route_coverage(
            [
                _pair(
                    "a",
                    100,
                    {
                        "table_routes": [
                            {"source_db": "db_a", "source_table": "*"},
                            {"source_db": "db_a", "source_table": "t1"},
                        ]
                    },
                )
            ]
        )
        self.assertFalse(results["a"][0].ok)
        self.assertIn("db_a", results["a"][0].message)
