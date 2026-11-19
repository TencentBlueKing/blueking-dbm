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
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_services.mysql.toolbox.serializers import TdbctlUpgradeFlowParamBuilder
from backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl import UpgradeTdbctlFlow


def _ticket(details):
    return SimpleNamespace(
        id=1,
        details=details,
        ticket_type="TENDBCLUSTER_TDBCTL_UPGRADE",
        creator="tester",
        bk_biz_id=100,
    )


class TdbctlUpgradeParamTest(SimpleTestCase):
    def test_upgrade_all_keeps_pkg_only_infos(self):
        builder = TdbctlUpgradeFlowParamBuilder(
            _ticket(
                {
                    "bk_biz_id": 100,
                    "cluster_ids": [],
                    "pkg_id": 123,
                    "upgrade_all": True,
                }
            )
        )
        ticket_data = builder.get_params()["ticket_data"]
        self.assertEqual(ticket_data["infos"], [{"pkg_id": 123}])
        self.assertIs(ticket_data["update_all"], True)
        self.assertNotIn("upgrade_all", ticket_data)
        self.assertNotIn("cluster_ids", ticket_data)

    @patch("backend.db_meta.models.Cluster.objects.filter")
    def test_specified_clusters_keep_per_cluster_infos(self, mock_filter):
        mock_filter.return_value.first.return_value = SimpleNamespace(bk_cloud_id=8)
        builder = TdbctlUpgradeFlowParamBuilder(
            _ticket(
                {
                    "bk_biz_id": 100,
                    "cluster_ids": [1, 2],
                    "pkg_id": 123,
                    "upgrade_all": False,
                }
            )
        )
        ticket_data = builder.get_params()["ticket_data"]
        self.assertEqual(
            ticket_data["infos"],
            [
                {"cluster_id": 1, "pkg_id": 123},
                {"cluster_id": 2, "pkg_id": 123},
            ],
        )
        self.assertIs(ticket_data["update_all"], False)
        self.assertEqual(ticket_data["bk_cloud_id"], 8)
        self.assertNotIn("upgrade_all", ticket_data)
        mock_filter.assert_called_once_with(id=1)

    def test_empty_infos_raises_without_builder(self):
        flow = UpgradeTdbctlFlow(
            root_id="root-1",
            data={
                "bk_biz_id": 100,
                "bk_cloud_id": 0,
                "uid": "admin",
                "update_all": False,
                "infos": [],
            },
        )
        with patch("backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl.Builder") as mock_builder:
            with self.assertRaises(ValueError) as ctx:
                flow.run()
        self.assertEqual(str(ctx.exception), _("没有需要升级的集群"))
        mock_builder.assert_not_called()

    @patch("backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl.Cluster.objects.filter")
    def test_update_all_infos_carry_bk_cloud_id(self, mock_filter):
        rows = [
            {"id": 11, "bk_cloud_id": 3},
            {"id": 22, "bk_cloud_id": 7},
        ]

        def values(*fields):
            return [{field: row[field] for field in fields} for row in rows]

        queryset = MagicMock()
        queryset.values.side_effect = values
        mock_filter.return_value = queryset

        flow = UpgradeTdbctlFlow(
            root_id="root-1",
            data={
                "bk_biz_id": 100,
                "bk_cloud_id": 0,
                "uid": "admin",
                "update_all": True,
                "infos": [{"pkg_id": 123}],
            },
        )
        self.assertEqual(
            flow._get_upgrade_infos(),
            [
                {"cluster_id": 11, "pkg_id": 123, "bk_cloud_id": 3},
                {"cluster_id": 22, "pkg_id": 123, "bk_cloud_id": 7},
            ],
        )
        mock_filter.assert_called_once_with(bk_biz_id=100, cluster_type=ClusterType.TenDBCluster)
