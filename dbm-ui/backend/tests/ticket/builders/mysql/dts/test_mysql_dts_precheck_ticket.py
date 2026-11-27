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
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.precheck.base import all_items
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.mysql.dts.precheck.mysql_dts_precheck import (
    MysqlDtsPrecheckDetailSerializer,
    MysqlDtsPrecheckFlowBuilder,
    MysqlDtsPrecheckFlowParamBuilder,
)
from backend.ticket.constants import TicketType


def _details(**overrides):
    data = {
        "infos": [
            {
                "migrate": {
                    "topology": "one_to_one",
                    "one_to_one": {
                        "source": {
                            "cluster_id": 100,
                            "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]},
                        },
                        "target": {"cluster_id": 200},
                    },
                }
            }
        ]
    }
    data.update(overrides)
    return data


class MysqlDtsPrecheckSerializerTest(SimpleTestCase):
    def test_minimal_input_enables_all_items(self):
        slz = MysqlDtsPrecheckDetailSerializer(data=_details())
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertEqual(
            set(slz.validated_data["enabled_codes"]),
            {item.code for item in all_items()},
        )

    def test_enabled_codes_choices_come_from_registry(self):
        """新增检查项无需改单据：候选值直接来自注册表。"""
        choices = MysqlDtsPrecheckDetailSerializer().fields["enabled_codes"].child.choices
        self.assertEqual(set(choices), {item.code for item in all_items()})

    def test_explicit_enabled_codes_preserved(self):
        slz = MysqlDtsPrecheckDetailSerializer(data=_details(enabled_codes=["version"]))
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertEqual(slz.validated_data["enabled_codes"], ["version"])

    def test_unknown_enabled_code_rejected(self):
        slz = MysqlDtsPrecheckDetailSerializer(data=_details(enabled_codes=["not_a_real_item"]))
        self.assertFalse(slz.is_valid())
        self.assertIn("enabled_codes", slz.errors)

    def test_empty_enabled_codes_rejected(self):
        slz = MysqlDtsPrecheckDetailSerializer(data=_details(enabled_codes=[]))
        self.assertFalse(slz.is_valid())
        self.assertIn("enabled_codes", slz.errors)

    def test_same_source_and_target_rejected(self):
        slz = MysqlDtsPrecheckDetailSerializer(
            data={
                "migrate": {
                    "topology": "one_to_one",
                    "one_to_one": {
                        "source": {
                            "cluster_id": 100,
                            "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]},
                        },
                        "target": {"cluster_id": 100},
                    },
                }
            }
        )
        self.assertFalse(slz.is_valid())
        self.assertIn("不能相同", str(slz.errors))

    def test_migrate_is_required(self):
        slz = MysqlDtsPrecheckDetailSerializer(data={})
        self.assertFalse(slz.is_valid())
        self.assertIn("必须提供migrate，或多行 infos", str(slz.errors))

    def test_many_to_one_expands_inside_validation(self):
        slz = MysqlDtsPrecheckDetailSerializer(
            data={
                "migrate": {
                    "topology": "many_to_one",
                    "many_to_one": {
                        "sources": [
                            {"cluster_id": 100, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}},
                            {"cluster_id": 101, "sync_scope": {"db_patterns": ["db_b"], "table_patterns": ["*"]}},
                        ],
                        "target": {"cluster_id": 200},
                    },
                }
            }
        )
        self.assertTrue(slz.is_valid(), slz.errors)

    def test_source_host_and_instance_id_conflict(self):
        details = _details()
        source = details["infos"][0]["migrate"]["one_to_one"]["source"]
        source["source_host"] = "127.0.0.1:3306"
        source["source_instance_id"] = 7
        slz = MysqlDtsPrecheckDetailSerializer(data=details)
        self.assertFalse(slz.is_valid())
        self.assertIn("不能同时指定", str(slz.errors))


class MysqlDtsPrecheckBuilderTest(SimpleTestCase):
    def test_builder_is_not_registered(self):
        self.assertNotIn(TicketType.MYSQL_DTS_PRECHECK, BuilderFactory.registry)

    def test_builder_wiring(self):
        self.assertEqual(MysqlDtsPrecheckFlowBuilder.serializer, MysqlDtsPrecheckDetailSerializer)
        self.assertEqual(MysqlDtsPrecheckFlowBuilder.inner_flow_builder, MysqlDtsPrecheckFlowParamBuilder)

    def test_flow_param_builder_controller(self):
        from backend.flow.engine.controller.mysql import MySQLController

        self.assertEqual(
            MysqlDtsPrecheckFlowParamBuilder.controller,
            MySQLController.mysql_dts_precheck_scene,
        )

    def test_precheck_skips_itsm_and_manual_confirm(self):
        """只读预检查不走审批与人工确认。"""
        builder = MysqlDtsPrecheckFlowBuilder(MagicMock(details=_details()))
        self.assertFalse(builder.need_itsm)
        self.assertFalse(builder.need_manual_confirm)

    def test_get_params_carries_uid_and_ticket_id(self):
        ticket = SimpleNamespace(
            id=18801,
            details=_details(enabled_codes=["version"]),
            ticket_type=TicketType.MYSQL_DTS_PRECHECK.value,
            creator="tester",
            bk_biz_id=1,
        )
        ticket_data = MysqlDtsPrecheckFlowParamBuilder(ticket).get_params()["ticket_data"]
        self.assertEqual(ticket_data["uid"], 18801)
        self.assertEqual(ticket_data["created_by"], "tester")
        self.assertEqual(ticket_data["bk_biz_id"], 1)
        self.assertEqual(ticket_data["enabled_codes"], ["version"])
