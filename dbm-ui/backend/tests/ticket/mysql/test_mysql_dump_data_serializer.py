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

from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator import DbConsoleDumpFlowValidator
from backend.ticket.builders.mysql.mysql_dump_data import (
    MAX_SQL_CONTENT_SIZE,
    SQL_CONTENT_TRUNCATED_TIP,
    MySQLDumpDataDetailSerializer,
    MySQLDumpDataFlowBuilder,
)
from backend.ticket.builders.tendbcluster.tendb_dump_data import TendbClusterDumpDataDetailSerializer
from backend.ticket.constants import TicketType


class MySQLDumpDataSerializerTests(SimpleTestCase):
    def setUp(self):
        self.biz_id = 1
        self.context = {
            "request": SimpleNamespace(is_external=False),
            "ticket_type": TicketType.MYSQL_DUMP_DATA.value,
        }

    def _table_payload(self, **extra):
        payload = {
            "cluster_id": 11,
            "charset": "utf8",
            "databases": ["app"],
            "tables": ["t"],
            "dump_data": True,
            "dump_schema": False,
        }
        payload.update(extra)
        return payload

    def _sql_payload(self, **extra):
        payload = {
            "cluster_id": 11,
            "sql_path": BKREPO_SQLFILE_PATH.format(biz=self.biz_id),
            "sql_filename": "export.sql",
            "export_mode": "sql",
        }
        payload.update(extra)
        return payload

    def _errors(self, payload, with_biz=False):
        context = dict(self.context)
        if with_biz:
            context["bk_biz_id"] = self.biz_id
        serializer = MySQLDumpDataDetailSerializer(data=payload, context=context)
        self.assertFalse(serializer.is_valid())
        return str(serializer.errors)

    def test_table_mode_still_passes(self):
        with patch("backend.ticket.builders.mysql.base.Cluster.objects.filter", return_value=[]):
            serializer = MySQLDumpDataDetailSerializer(data=self._table_payload(), context=self.context)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["export_mode"], "table")

    def test_table_mode_requires_databases(self):
        payload = self._table_payload()
        payload.pop("databases")
        self.assertIn("databases", self._errors(payload))

    def _accept_sql(self, payload):
        context = dict(self.context)
        context["bk_biz_id"] = self.biz_id
        queryset = MagicMock()
        queryset.values_list.return_value = [self.biz_id]
        queryset.__iter__.return_value = iter([])
        with patch("backend.ticket.builders.mysql.base.Cluster.objects.filter", return_value=queryset), patch(
            "backend.ticket.builders.common.base.Cluster.objects.filter", return_value=queryset
        ), patch.object(DbConsoleDumpFlowValidator, "__new__", return_value=None):
            serializer = MySQLDumpDataDetailSerializer(data=payload, context=context)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            return serializer

    def test_sql_csv_requires_dump_center(self):
        cluster = SimpleNamespace(bk_cloud_id=0)
        queryset = MagicMock()
        queryset.first.return_value = cluster
        context = dict(self.context)
        context["bk_biz_id"] = self.biz_id
        with patch(
            "backend.ticket.builders.mysql.mysql_dump_data.Cluster.objects.filter", return_value=queryset
        ), patch("backend.ticket.builders.mysql.mysql_dump_data.DBExtension.get_latest_extension", return_value=None):
            serializer = MySQLDumpDataDetailSerializer(data=self._sql_payload(result_format="csv"), context=context)
            self.assertFalse(serializer.is_valid())
        self.assertIn("result_format", serializer.errors)
        self.assertIn("中转机", str(serializer.errors))

    def test_sql_csv_passes_when_dump_center_exists(self):
        cluster = SimpleNamespace(bk_cloud_id=0)
        queryset = MagicMock()
        queryset.first.return_value = cluster
        queryset.values_list.return_value = [self.biz_id]
        queryset.__iter__.return_value = iter([])
        context = dict(self.context)
        context["bk_biz_id"] = self.biz_id
        with patch(
            "backend.ticket.builders.mysql.mysql_dump_data.Cluster.objects.filter", return_value=queryset
        ), patch(
            "backend.ticket.builders.mysql.mysql_dump_data.DBExtension.get_latest_extension",
            return_value=SimpleNamespace(details={"ip": "127.0.0.1"}),
        ), patch(
            "backend.ticket.builders.mysql.base.Cluster.objects.filter", return_value=queryset
        ), patch(
            "backend.ticket.builders.common.base.Cluster.objects.filter", return_value=queryset
        ), patch.object(
            DbConsoleDumpFlowValidator, "__new__", return_value=None
        ):
            serializer = MySQLDumpDataDetailSerializer(data=self._sql_payload(result_format="csv"), context=context)
            self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_sql_mode_shape_passes(self):
        serializer = self._accept_sql(self._sql_payload())
        self.assertEqual(serializer.validated_data["export_mode"], "sql")
        self.assertNotIn("导出尚未启用", str(serializer.errors))

    def test_sql_filename_with_directory(self):
        errors = self._errors(self._sql_payload(sql_filename="../a.sql"), with_biz=True)
        self.assertIn("sql_filename", errors)
        self.assertNotIn("导出尚未启用", errors)

    def test_sql_path_dot_segments(self):
        parent = self._errors(self._sql_payload(sql_path="mysql/sqlfile/1/../2"), with_biz=True)
        self.assertIn("sql_path", parent)
        dotted = self._errors(self._sql_payload(sql_path="mysql/sqlfile/1/./dir"), with_biz=True)
        self.assertIn("sql_path", dotted)
        exact = self._accept_sql(self._sql_payload())
        self.assertEqual(exact.validated_data["sql_path"], "mysql/sqlfile/1")
        child = self._accept_sql(self._sql_payload(sql_path="mysql/sqlfile/1/sub/dir/"))
        self.assertEqual(child.validated_data["sql_path"], "mysql/sqlfile/1/sub/dir")
        errors = self._errors(self._sql_payload(sql_path="mysql/sqlfile/999"), with_biz=True)
        self.assertIn("sql_path", errors)
        self.assertNotIn("导出尚未启用", errors)

    def test_table_mode_ignores_csv_format(self):
        with patch("backend.ticket.builders.mysql.base.Cluster.objects.filter", return_value=[]):
            serializer = MySQLDumpDataDetailSerializer(
                data=self._table_payload(result_format="csv"), context=self.context
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_bad_result_format(self):
        self.assertIn("result_format", self._errors(self._sql_payload(result_format="xml"), with_biz=True))

    def test_need_itsm_for_sql_without_dump_data(self):
        builder = MySQLDumpDataFlowBuilder.__new__(MySQLDumpDataFlowBuilder)
        builder.ticket = SimpleNamespace(details={"export_mode": "sql"})
        self.assertTrue(builder.need_itsm)

    def test_tendbcluster_serializer_inherits_mysql(self):
        self.assertTrue(issubclass(TendbClusterDumpDataDetailSerializer, MySQLDumpDataDetailSerializer))
        with patch("backend.ticket.builders.mysql.base.Cluster.objects.filter", return_value=[]):
            serializer = TendbClusterDumpDataDetailSerializer(data=self._table_payload(), context=self.context)
            self.assertTrue(serializer.is_valid(), serializer.errors)

    def _builder(self, details):
        builder = MySQLDumpDataFlowBuilder.__new__(MySQLDumpDataFlowBuilder)
        builder.ticket = SimpleNamespace(details=details)
        return builder

    def _sql_details(self):
        return {
            "export_mode": "sql",
            "sql_path": BKREPO_SQLFILE_PATH.format(biz=self.biz_id),
            "sql_filename": "export.sql",
        }

    def test_fetch_sql_content_only_in_sql_mode(self):
        self.assertEqual(self._builder({"export_mode": "table"}).fetch_sql_content(), "")
        # 缺少sql文件路径时不读取制品库
        self.assertEqual(self._builder({"export_mode": "sql"}).fetch_sql_content(), "")

    def test_fetch_sql_content_returns_file_content(self):
        storage = MagicMock()
        storage.client.batch_download.return_value = SimpleNamespace(status_code=200, content=b"SELECT * FROM t1;")
        builder = self._builder(self._sql_details())
        with patch("backend.ticket.builders.mysql.mysql_dump_data.get_storage", return_value=storage):
            self.assertEqual(builder.fetch_sql_content(), "SELECT * FROM t1;")
        storage.client.batch_download.assert_called_once_with(["mysql/sqlfile/1/export.sql"])

    def test_fetch_sql_content_failed_returns_empty(self):
        builder = self._builder(self._sql_details())
        storage = MagicMock()
        storage.client.batch_download.return_value = SimpleNamespace(status_code=500, content=b"")
        with patch("backend.ticket.builders.mysql.mysql_dump_data.get_storage", return_value=storage):
            self.assertEqual(builder.fetch_sql_content(), "")
        storage.client.batch_download.side_effect = Exception("bkrepo down")
        with patch("backend.ticket.builders.mysql.mysql_dump_data.get_storage", return_value=storage):
            self.assertEqual(builder.fetch_sql_content(), "")

    def test_fetch_sql_content_truncated_when_too_large(self):
        storage = MagicMock()
        storage.client.batch_download.return_value = SimpleNamespace(
            status_code=200, content=b"a" * (MAX_SQL_CONTENT_SIZE + 10)
        )
        builder = self._builder(self._sql_details())
        with patch("backend.ticket.builders.mysql.mysql_dump_data.get_storage", return_value=storage):
            content = builder.fetch_sql_content()
        self.assertEqual(len(content), MAX_SQL_CONTENT_SIZE + len(str(SQL_CONTENT_TRUNCATED_TIP)))
        self.assertTrue(content.endswith(str(SQL_CONTENT_TRUNCATED_TIP)))

    def test_sql_charset_defaults_then_disabled(self):
        payload = self._sql_payload()
        context = dict(self.context)
        context["bk_biz_id"] = self.biz_id
        serializer = MySQLDumpDataDetailSerializer(data=payload, context=context)
        internal = serializer.to_internal_value(payload)
        self.assertEqual(internal["charset"], "default")
        serializer = self._accept_sql(payload)
        self.assertEqual(serializer.validated_data["charset"], "default")
