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
from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceInnerRole
from backend.flow.engine.bamboo.scene.mysql.validate.exception import TenDBHAUpgradeParamCheckFailedException
from backend.flow.engine.bamboo.scene.mysql.validate.mysql_upgrade_drs_check import (
    check_instance_upgrade,
    crosses_major_version,
    failures_from_drs,
    select_upgrade_checks,
)
from backend.flow.engine.bamboo.scene.mysql.validate.tendbha_upgrade_validator import TenDBHAUpgradeValidator
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse

V55 = mysql_version_parse("5.5.20")
V56 = mysql_version_parse("5.6.20")
V57 = mysql_version_parse("5.7.20")
V80 = mysql_version_parse("8.0.30")


def _codes(current, target):
    return [item["code"] for item in select_upgrade_checks(current, target)]


def _sql(current, target, code):
    for item in select_upgrade_checks(current, target):
        if item["code"] == code:
            return item["sql"]
    return ""


class TestSelectUpgradeChecks(SimpleTestCase):
    def test_upgrade_to_80_adds_80_checks_and_keywords(self):
        codes = _codes(V57, V80)
        self.assertIn("dictionary_name", codes)
        self.assertIn("partition_engine", codes)
        self.assertIn("shared_tablespace", codes)
        self.assertIn("fk_name", codes)
        self.assertIn("enum_set_length", codes)
        self.assertIn("view_column_length", codes)
        self.assertIn("udf", codes)
        self.assertNotIn("year2", codes)
        self.assertNotIn("old_password", codes)
        self.assertIn("CUME_DIST", _sql(V57, V80, "keyword_table"))
        self.assertIn("ExtractValue", _sql(V57, V80, "keyword_routine"))
        self.assertIn("> 263", _sql(V57, V80, "enum_set_length"))

    def test_upgrade_to_57_adds_password_partition_year_tokudb(self):
        codes = _codes(V56, V57)
        self.assertIn("old_password", codes)
        self.assertIn("partition_57", codes)
        self.assertIn("year2", codes)
        self.assertIn("tokudb", codes)
        self.assertNotIn("dictionary_name", codes)
        self.assertIn("GENERATED", _sql(V56, V57, "keyword_event"))

    def test_upgrade_to_56_only_adds_old_password(self):
        codes = _codes(V55, V56)
        self.assertIn("old_password", codes)
        self.assertNotIn("year2", codes)
        self.assertNotIn("dictionary_name", codes)
        self.assertIn("IO_AFTER_GTIDS", _sql(V55, V56, "keyword_trigger"))

    def test_same_major_is_not_a_cross(self):
        self.assertFalse(crosses_major_version("8.0.18-log", "8.0.32"))
        self.assertFalse(crosses_major_version("5.7.20", "5.7.44"))
        self.assertTrue(crosses_major_version("5.7.20-log", "8.0.30"))
        self.assertTrue(crosses_major_version("5.6.20", "5.7.20"))


class TestDrsFailures(SimpleTestCase):
    def test_empty_rows_pass(self):
        items = select_upgrade_checks(V57, V80)
        response = [{"error_msg": "", "cmd_results": [{"table_data": [], "error_msg": ""} for _item in items]}]
        self.assertEqual(failures_from_drs(items, response, "127.0.0.1:3306"), [])

    def test_rows_fail_with_the_check_title(self):
        items = [{"code": "keyword_table", "title": _("表名撞上目标版本保留字"), "sql": "select 1"}]
        response = [
            {
                "error_msg": "",
                "cmd_results": [{"table_data": [{"TABLE_NAME": "RANGE"}], "error_msg": ""}],
            }
        ]
        failures = failures_from_drs(items, response, "127.0.0.1:3306")
        self.assertEqual(len(failures), 1)
        self.assertIn("RANGE", failures[0])
        self.assertIn("127.0.0.1:3306", failures[0])

    def test_check_instance_sends_selected_sql_to_drs(self):
        calls = []

        def rpc(body):
            calls.append(body)
            if body["cmds"] == ["select version() as version"]:
                return [
                    {"error_msg": "", "cmd_results": [{"table_data": [{"version": "5.7.20-log"}], "error_msg": ""}]}
                ]
            items = select_upgrade_checks(V57, V80)
            return [{"error_msg": "", "cmd_results": [{"table_data": [], "error_msg": ""} for _item in items]}]

        failures = check_instance_upgrade("127.0.0.1:3306", 0, "8.0.30", rpc)
        self.assertEqual(failures, [])
        self.assertEqual(calls[0]["addresses"], ["127.0.0.1:3306"])
        self.assertEqual(calls[0]["bk_cloud_id"], 0)
        self.assertIn("CUME_DIST", calls[1]["cmds"][0])
        self.assertTrue(any("mysql.func" in cmd for cmd in calls[1]["cmds"]))

    def test_same_major_stops_after_reading_version(self):
        calls = []

        def rpc(body):
            calls.append(body)
            return [{"error_msg": "", "cmd_results": [{"table_data": [{"version": "8.0.18-log"}], "error_msg": ""}]}]

        failures = check_instance_upgrade("127.0.0.1:3306", 0, "8.0.32", rpc)
        self.assertEqual(failures, [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["cmds"], ["select version() as version"])


class TestMigrateUpgradeValidator(SimpleTestCase):
    def test_ticket_validation_fails_when_old_master_hits_a_keyword(self):
        cluster = MagicMock()
        cluster.bk_cloud_id = 0
        standby = MagicMock()
        standby.machine.ip = "127.0.0.2"
        standby.port = 3306
        slave_qs = MagicMock()
        slave_qs.filter.return_value.first.return_value = standby
        cluster.storageinstance_set.filter.return_value = slave_qs
        pkg = MagicMock()
        pkg.name = "mysql-8.0.30-linux-x86_64.tar.gz"
        module = "backend.flow.engine.bamboo.scene.mysql.validate.tendbha_upgrade_validator"

        def rpc(body):
            if body["cmds"] == ["select version() as version"]:
                return [
                    {"error_msg": "", "cmd_results": [{"table_data": [{"version": "5.7.20-log"}], "error_msg": ""}]}
                ]
            return [
                {
                    "error_msg": "",
                    "cmd_results": [{"table_data": [{"TABLE_NAME": "RANGE"}], "error_msg": ""}],
                }
            ]

        with patch.object(TenDBHAUpgradeValidator, "pre_check_charset_consistency", return_value=[]), patch.object(
            TenDBHAUpgradeValidator, "pre_check_upgrade_params", return_value=[]
        ), patch(f"{module}.Cluster.objects.get", return_value=cluster), patch(
            f"{module}.Package.objects.get", return_value=pkg
        ), patch(
            f"{module}.DRSApi.rpc", side_effect=rpc
        ):
            with self.assertRaises(TenDBHAUpgradeParamCheckFailedException) as caught:
                TenDBHAUpgradeValidator(
                    {"bk_biz_id": 1, "infos": [{"pkg_id": 9, "cluster_ids": [1], "new_db_module_id": 2}]}
                )

        self.assertIn("127.0.0.2:3306", str(caught.exception))
        self.assertIn("RANGE", str(caught.exception))

    def test_schema_check_uses_master_when_slave_is_missing(self):
        master = MagicMock()
        master.machine.ip = "127.0.0.1"
        master.port = 3306
        empty_slaves = MagicMock()
        empty_slaves.filter.return_value.first.return_value = None
        empty_slaves.first.return_value = None
        cluster = MagicMock()

        def filter_instances(**kwargs):
            if kwargs.get("instance_inner_role") == InstanceInnerRole.SLAVE.value:
                return empty_slaves
            masters = MagicMock()
            masters.first.return_value = master
            return masters

        cluster.storageinstance_set.filter.side_effect = filter_instances
        checker = object.__new__(TenDBHAUpgradeValidator)
        picked = checker._schema_check_instance(cluster)
        self.assertIs(picked, master)
