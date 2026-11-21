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
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.mysql.dts.precheck.mysql_dts_precheck import MysqlDtsPrecheckFlow
from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError


def _data(**overrides):
    data = {
        "bk_biz_id": 1,
        "migrate": {
            "topology": "one_to_one",
            "one_to_one": {
                "source": {
                    "cluster_id": 100,
                    "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]},
                },
                "target": {"cluster_id": 200},
            },
        },
    }
    data.update(overrides)
    return data


class MysqlDtsPrecheckFlowTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.precheck.mysql_dts_precheck.Cluster.objects.filter")
    def test_resolve_pairs_by_biz_and_cluster_id(self, mock_filter):
        mock_filter.return_value = [
            SimpleNamespace(id=100, immute_domain="source.db", cluster_type=ClusterType.TenDBHA.value),
            SimpleNamespace(id=200, immute_domain="target.db", cluster_type=ClusterType.TenDBCluster.value),
        ]
        data = _data()

        pairs = MysqlDtsPrecheckFlow(root_id="root-1", data=data).resolve_pairs()

        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["source_cluster_domain"], "source.db")
        self.assertEqual(pairs[0]["target_cluster_domain"], "target.db")
        self.assertEqual(pairs[0]["source_tables"], [{"db": "db_a", "tables": ["*"]}])
        self.assertEqual(mock_filter.call_args.kwargs["bk_biz_id"], 1)
        self.assertEqual(set(mock_filter.call_args.kwargs["id__in"]), {100, 200})

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.precheck.mysql_dts_precheck.Cluster.objects.filter")
    def test_unknown_cluster_raises_collection_error(self, mock_filter):
        mock_filter.return_value = [
            SimpleNamespace(id=100, immute_domain="source.db", cluster_type=ClusterType.TenDBHA.value),
        ]

        with self.assertRaisesRegex(PrecheckCollectError, "200"):
            MysqlDtsPrecheckFlow(root_id="root-1", data=_data()).resolve_pairs()

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.precheck.mysql_dts_precheck.Cluster.objects.filter")
    def test_unsupported_cluster_type_raises_collection_error(self, mock_filter):
        mock_filter.return_value = [
            SimpleNamespace(id=100, immute_domain="source.db", cluster_type=ClusterType.TenDBHA.value),
            SimpleNamespace(id=200, immute_domain="target.db", cluster_type=ClusterType.RedisInstance.value),
        ]

        with self.assertRaisesRegex(PrecheckCollectError, "不支持 DTS 预检查"):
            MysqlDtsPrecheckFlow(root_id="root-1", data=_data()).resolve_pairs()
