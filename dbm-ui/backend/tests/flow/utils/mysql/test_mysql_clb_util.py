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
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.flow.plugins.components.collections.name_service.mysql_clb_comp import (
    ClbOperationType,
    MySQLClbServiceOperation,
)
from backend.flow.utils.mysql.mysql_clb_util import build_mysql_clb_apply_subs


class TestBuildMysqlClbApplySubs(SimpleTestCase):
    def test_apply_clb_false_returns_empty(self):
        subs = build_mysql_clb_apply_subs(
            root_id="root",
            data={"bk_biz_id": 1},
            bk_biz_id=1,
            domain_name="gamedb.test.db",
            creator="admin",
            apply_clb=False,
        )
        self.assertEqual(subs, [])

    def test_apply_clb_true_builds_three_acts(self):
        domain = "gamedb.test.db"
        captured = []

        with patch("backend.flow.utils.mysql.mysql_clb_util.SubBuilder") as mock_sub_builder_cls:
            mock_sub = MagicMock()
            mock_sub_builder_cls.return_value = mock_sub
            mock_sub.build_sub_process.return_value = MagicMock(name="clb_sub")
            mock_sub.add_act.side_effect = lambda **kw: captured.append(kw["kwargs"])

            subs = build_mysql_clb_apply_subs(
                root_id="root",
                data={"bk_biz_id": 1, "uid": "1"},
                bk_biz_id=1,
                domain_name=domain,
                creator="admin",
                apply_clb=True,
                spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
            )

        self.assertEqual(len(subs), 1)
        self.assertEqual(len(captured), 3)
        for kwargs in captured:
            self.assertEqual(kwargs["bk_biz_id"], 1)
            self.assertEqual(kwargs["domain_name"], domain)
            self.assertEqual(kwargs["creator"], "admin")
            self.assertEqual(kwargs["role"], TenDBClusterSpiderRole.SPIDER_MASTER.value)
            self.assertIsNone(kwargs["cluster_id"])
        op_types = [kwargs["name_service_operation_type"] for kwargs in captured]
        self.assertEqual(
            op_types,
            [
                ClbOperationType.CREATE_CLB.value,
                ClbOperationType.ADD_CLB_INFO_TO_META.value,
                ClbOperationType.ADD_CLB_DOMAIN_TO_DNS.value,
            ],
        )


class TestMysqlClbServiceDomainResolve(SimpleTestCase):
    @patch(
        "backend.flow.plugins.components.collections.name_service.mysql_clb_comp.mysql_clb.create_lb_and_register_target"
    )
    @patch("backend.flow.plugins.components.collections.name_service.mysql_clb_comp.Cluster")
    def test_resolve_cluster_id_from_domain(self, mock_cluster_model, mock_create_clb):
        mock_cluster_model.objects.get.return_value = MagicMock(id=98)
        mock_create_clb.return_value = {"code": 0, "message": "ok", "data": {}}

        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "name_service_operation_type": ClbOperationType.CREATE_CLB.value,
                "creator": "admin",
                "role": None,
                "cluster_id": None,
                "bk_biz_id": 20,
                "domain_name": "gamedb.test.db",
                "set_trans_data_dataclass": "TransDataKwargs",
            },
            "trans_data": "${trans_data}",
        }[key]
        data.outputs = {}

        service = MySQLClbServiceOperation()
        self.assertTrue(service._execute(data))
        mock_cluster_model.objects.get.assert_called_once_with(bk_biz_id=20, immute_domain="gamedb.test.db")
        mock_create_clb.assert_called_once_with(cluster_id=98, role=None)
