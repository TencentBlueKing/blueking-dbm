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

from backend.configuration.constants import DBType
from backend.ticket.builders.mysql.mysql_import_sqlfile import MysqlSqlImportFlowBuilder


class TestPatchSqlfileGrammarCheckInfo:
    """单据 patch 语法检查需要按目标集群主版本传递 versions。"""

    @patch("backend.ticket.builders.mysql.mysql_import_sqlfile.SQLSimulationApi.grammar_check")
    @patch("backend.ticket.builders.mysql.mysql_import_sqlfile.Cluster.objects.filter")
    def test_pass_unique_cluster_major_versions(self, mock_filter, mock_grammar_check):
        mock_filter.return_value.values_list.return_value = ["TXSQL-8.0", "MySQL-5.7", "TXSQL-8.0"]
        check_info = {"a.sql": {"highrisk_warnings": []}}
        mock_grammar_check.return_value = check_info
        ticket = SimpleNamespace(
            details={
                "path": "mysql/sqlfile/1",
                "cluster_ids": [11, 22],
                "execute_objects": [
                    {"sql_files": ["a.sql", "b.sql"]},
                    {"sql_files": ["c.sql"]},
                ],
            }
        )

        MysqlSqlImportFlowBuilder.patch_sqlfile_grammar_check_info(ticket, DBType.MySQL)

        mock_filter.assert_called_once_with(id__in=[11, 22])
        mock_filter.return_value.values_list.assert_called_once_with("major_version", flat=True)
        params = mock_grammar_check.call_args.kwargs["params"]
        assert params["path"] == "mysql/sqlfile/1"
        assert set(params["files"]) == {"a.sql", "b.sql", "c.sql"}
        assert params["cluster_type"] == DBType.MySQL
        assert set(params["versions"]) == {"TXSQL-8.0", "MySQL-5.7"}
        assert len(params["versions"]) == 2
        assert ticket.details["grammar_check_info"] == check_info

    @patch("backend.ticket.builders.mysql.mysql_import_sqlfile.SQLSimulationApi.grammar_check")
    @patch("backend.ticket.builders.mysql.mysql_import_sqlfile.Cluster.objects.filter")
    def test_empty_cluster_ids_pass_empty_versions(self, mock_filter, mock_grammar_check):
        mock_filter.return_value.values_list.return_value = []
        mock_grammar_check.return_value = {}
        ticket = SimpleNamespace(
            details={
                "path": "mysql/sqlfile/1",
                "execute_objects": [{"sql_files": ["a.sql"]}],
            }
        )

        MysqlSqlImportFlowBuilder.patch_sqlfile_grammar_check_info(ticket, DBType.TenDBCluster)

        mock_filter.assert_called_once_with(id__in=[])
        params = mock_grammar_check.call_args.kwargs["params"]
        assert params["versions"] == []
        assert params["cluster_type"] == DBType.TenDBCluster
        assert params["files"] == ["a.sql"]
