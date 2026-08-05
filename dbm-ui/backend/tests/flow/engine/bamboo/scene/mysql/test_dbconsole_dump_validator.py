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

from backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator import DbConsoleDumpFlowValidator


def _make_validator(data: dict) -> DbConsoleDumpFlowValidator:
    """绕过 BaseValidator.__new__ 的立刻 __call__，便于单测私有方法。"""
    validator = object.__new__(DbConsoleDumpFlowValidator)
    validator.data = data
    return validator


class TestDbConsoleDumpFlowValidatorInject(SimpleTestCase):
    """覆盖 where 注入检查：命中拒绝 / 放行进 EXPLAIN / API 异常失败放行。"""

    def test_empty_where_skips_all_checks(self):
        with patch.object(DbConsoleDumpFlowValidator, "_check_where_inject") as mock_inject, patch.object(
            DbConsoleDumpFlowValidator, "_explain_all"
        ) as mock_explain:
            result = DbConsoleDumpFlowValidator({"where": "", "cluster_id": 1, "databases": ["db1"], "tables": ["t1"]})
            self.assertIsNone(result)
            mock_inject.assert_not_called()
            mock_explain.assert_not_called()

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.SQLSimulationApi.syntax_check_inject"
    )
    def test_union_where_rejected_by_inject(self, mock_inject):
        mock_inject.return_value = {"is_inject": True, "reason": "检测到 UNION 查询拼接"}
        validator = _make_validator({})
        err = validator._check_where_inject("111 union select * from t2", ("db1", "t1"))
        self.assertIsNotNone(err)
        self.assertEqual(err["field"], "where")
        self.assertIn("UNION", err["errors"])
        mock_inject.assert_called_once_with(
            params={
                "sql": "SELECT * FROM `db1`.`t1` WHERE (111 union select * from t2)",
                "judge_subquery_diff_table": True,
            }
        )

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.SQLSimulationApi.syntax_check_inject",
        return_value={"is_inject": False, "reason": ""},
    )
    @patch.object(DbConsoleDumpFlowValidator, "_explain_all", return_value=[])
    @patch.object(DbConsoleDumpFlowValidator, "_resolve_targets", return_value=([("db1", "t1")], []))
    @patch.object(DbConsoleDumpFlowValidator, "_get_read_address", return_value=("127.0.0.1:20000", 0))
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.Cluster.objects.get",
        return_value=MagicMock(),
    )
    def test_clean_where_passes_inject_then_explain(
        self, mock_cluster, mock_addr, mock_resolve, mock_explain, mock_inject
    ):
        result = DbConsoleDumpFlowValidator(
            {
                "where": "id > 1",
                "cluster_id": 1,
                "databases": ["db1"],
                "tables": ["t1"],
            }
        )
        self.assertIsNone(result)
        mock_inject.assert_called_once()
        mock_explain.assert_called_once()
        self.assertEqual(mock_explain.call_args[0][2], "id > 1")
        self.assertEqual(mock_explain.call_args[0][3], [("db1", "t1")])

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.SQLSimulationApi.syntax_check_inject",
        side_effect=RuntimeError("simulation down"),
    )
    @patch.object(DbConsoleDumpFlowValidator, "_explain_all", return_value=[])
    @patch.object(DbConsoleDumpFlowValidator, "_resolve_targets", return_value=([("db1", "t1")], []))
    @patch.object(DbConsoleDumpFlowValidator, "_get_read_address", return_value=("127.0.0.1:20000", 0))
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.Cluster.objects.get",
        return_value=MagicMock(),
    )
    def test_inject_api_error_fail_open(self, mock_cluster, mock_addr, mock_resolve, mock_explain, mock_inject):
        result = DbConsoleDumpFlowValidator(
            {
                "where": "id > 1",
                "cluster_id": 1,
                "databases": ["db1"],
                "tables": ["t1"],
            }
        )
        self.assertIsNone(result)
        mock_inject.assert_called_once()
        mock_explain.assert_called_once()
