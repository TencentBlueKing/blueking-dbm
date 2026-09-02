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

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from backend.flow.engine.bamboo.scene.mysql.dts.precheck import mysql_dts_precheck_subflow as subflow


class MysqlDtsPrecheckSubflowTest(SimpleTestCase):
    def test_target_schema_runs_before_the_parallel_stage(self):
        builder = MagicMock()
        with patch.object(subflow, "SubBuilder", return_value=builder):
            subflow.mysql_dts_precheck_subflow(root_id="root-1", data={"bk_biz_id": 3})

        self.assertEqual(builder.add_act.call_args.kwargs["kwargs"]["item_code"], "target_schema")
        acts = builder.add_parallel_acts.call_args.kwargs["acts_list"]
        self.assertEqual(
            [act["kwargs"]["item_code"] for act in acts],
            [
                "version",
                "advanced_objects",
                "binlog",
                "charset_collation",
                "instance_vars",
                "warnings",
            ],
        )
        self.assertEqual([name for name, _, _ in builder.mock_calls], ["add_act", "add_parallel_acts"])

    def test_single_enabled_item_stays_serial(self):
        builder = MagicMock()
        with patch.object(subflow, "SubBuilder", return_value=builder):
            subflow.mysql_dts_precheck_subflow(
                root_id="root-1",
                data={},
                enabled_codes=["version"],
            )

        builder.add_parallel_acts.assert_not_called()
        self.assertEqual(builder.add_act.call_args.kwargs["kwargs"]["item_code"], "version")

    def test_unassigned_item_is_rejected(self):
        with patch.object(subflow, "SubBuilder", return_value=MagicMock()):
            with self.assertRaises(ImproperlyConfigured):
                subflow.mysql_dts_precheck_subflow(
                    root_id="root-1",
                    data={},
                    enabled_codes=["version", "not_planned"],
                )
