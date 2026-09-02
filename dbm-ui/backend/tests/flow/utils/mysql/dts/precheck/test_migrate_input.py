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

from backend.flow.utils.mysql.dts.precheck.migrate_input import expand_precheck_pairs


def _source(cluster_id, database):
    return {"cluster_id": cluster_id, "sync_scope": {"db_patterns": [database], "table_patterns": ["*"]}}


class ExpandPrecheckPairsTest(SimpleTestCase):
    def test_infos_one_to_one_uses_migrate_scope_names(self):
        pairs = expand_precheck_pairs(
            {
                "infos": [
                    {
                        "migrate": {
                            "topology": "one_to_one",
                            "one_to_one": {"source": _source(100, "db_a"), "target": {"cluster_id": 200}},
                        }
                    }
                ]
            }
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["pair_key"], "0:100:200")
        self.assertEqual(pairs[0]["scope_label"], "db_a/*")
        self.assertEqual(pairs[0]["source_tables"], [{"db": "db_a", "tables": ["*"]}])

    def test_many_to_one_is_one_row_per_source(self):
        pairs = expand_precheck_pairs(
            {
                "migrate": {
                    "topology": "many_to_one",
                    "many_to_one": {
                        "sources": [_source(100, "db_a"), _source(101, "db_b")],
                        "target": {"cluster_id": 200},
                    },
                }
            }
        )
        self.assertEqual([pair["source_cluster_id"] for pair in pairs], [100, 101])
        self.assertEqual({pair["target_cluster_id"] for pair in pairs}, {200})
        self.assertTrue(all(pair["topology"] == "many_to_one" for pair in pairs))

    def test_one_to_many_is_one_row_per_target(self):
        pairs = expand_precheck_pairs(
            {
                "migrate": {
                    "topology": "one_to_many",
                    "one_to_many": {
                        "source": _source(100, "db_a"),
                        "targets": [{"cluster_id": 200}, {"cluster_id": 201}],
                    },
                }
            }
        )
        self.assertEqual([pair["target_cluster_id"] for pair in pairs], [200, 201])
        self.assertEqual({pair["source_cluster_id"] for pair in pairs}, {100})

    def test_infos_rejects_top_level_migrate(self):
        with self.assertRaisesRegex(ValueError, "不要再传顶层 migrate"):
            expand_precheck_pairs(
                {
                    "infos": [
                        {
                            "migrate": {
                                "topology": "one_to_one",
                                "one_to_one": {"source": _source(100, "db_a"), "target": {"cluster_id": 200}},
                            }
                        }
                    ],
                    "migrate": {
                        "topology": "one_to_one",
                        "one_to_one": {"source": _source(100, "db_a"), "target": {"cluster_id": 200}},
                    },
                }
            )

    def test_infos_only_allows_one_to_one(self):
        with self.assertRaisesRegex(ValueError, "infos\\[0\\] 仅支持 one_to_one"):
            expand_precheck_pairs(
                {
                    "infos": [
                        {
                            "migrate": {
                                "topology": "many_to_one",
                                "many_to_one": {
                                    "sources": [_source(100, "db_a")],
                                    "target": {"cluster_id": 200},
                                },
                            }
                        }
                    ]
                }
            )
