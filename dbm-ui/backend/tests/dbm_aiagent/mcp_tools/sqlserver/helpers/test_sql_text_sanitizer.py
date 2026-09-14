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
import pytest

from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_text_sanitizer import (
    REDACTED,
    SANITIZE_FAILED,
    is_sp_executesql,
    sanitize_rows_sql_text,
    sanitize_sql_text,
)


class TestIsSpExecutesql:
    """is_sp_executesql：宽松判定，兼容 Language Event 与 RPC Event 两种形态"""

    @pytest.mark.parametrize(
        "text,expected",
        [
            # Language Event：EXEC 开头
            ("EXEC sp_executesql N'SELECT 1'", True),
            # RPC Event：无 EXEC 前缀，直接 sp_executesql 开头
            ("sp_executesql (@P1 int)SELECT 1", True),
            # 大小写不敏感
            ("EXEC SP_EXECUTESQL N'SELECT 1'", True),
            # 普通 SQL
            ("SELECT 1", False),
            ("EXEC my_proc @p1=1", False),
            (None, False),
            ("", False),
        ],
    )
    def test_judge(self, text, expected):
        assert is_sp_executesql(text) is expected


class TestSanitizeGeneralSql:
    """普通 SQL：仅脱敏高危模式（手机号/身份证/邮箱/secret KV），保留 SQL 字面量结构"""

    def test_phone_redacted(self):
        assert sanitize_sql_text("WHERE phone='13800138000'") == "WHERE phone='<REDACTED>'"

    def test_idcard_redacted(self):
        assert sanitize_sql_text("WHERE idcard='110101199001011234'") == "WHERE idcard='<REDACTED>'"

    def test_email_redacted(self):
        assert sanitize_sql_text("WHERE email='user@example.com'") == "WHERE email='<REDACTED>'"

    def test_password_kv_redacted(self):
        assert sanitize_sql_text("password='secret'") == "password=<REDACTED>"

    def test_no_sensitive_unchanged(self):
        sql = "SELECT * FROM t WHERE id=1"
        assert sanitize_sql_text(sql) == sql


class TestSanitizeSpCall:
    """SP 调用：实参全部打掉"""

    def test_named_params_redacted(self):
        result = sanitize_sql_text("EXEC my_proc @p1=1, @p2=N'xxx'")
        assert result == "EXEC my_proc @p1=<REDACTED>, @p2=<REDACTED>"

    def test_positional_params_redacted(self):
        result = sanitize_sql_text("EXEC my_proc 1, 'abc'")
        assert result == "EXEC my_proc <REDACTED>, <REDACTED>"


class TestRedactSpExecutesql:
    """sp_executesql：模板内硬编码敏感值也必须脱敏（问题 1 修复）"""

    def test_template_phone_redacted(self):
        # SQL 模板内硬编码手机号（'' 为 SQL 单引号转义）
        text = "EXEC sp_executesql N'SELECT * FROM u WHERE phone=''13800138000'''"
        result = sanitize_sql_text(text)
        assert "13800138000" not in result
        assert REDACTED in result

    def test_named_params_redacted_and_template_kept(self):
        text = "EXEC sp_executesql N'SELECT 1', N'@p1 int', @p1=1"
        result = sanitize_sql_text(text)
        # 命名实参 @p1=1 被打掉
        assert "@p1=<REDACTED>" in result
        # SQL 模板保留，便于 AI 分析语义
        assert "SELECT 1" in result


class TestRedactPositionalParams:
    """位置参数过程名无法规范解析时，降级为通用高危模式脱敏（问题 2 修复）"""

    def test_special_proc_name_fallback_redacted(self):
        # #temp_proc 含 #，无法按规范过程名解析，应降级脱敏手机号而非返回原文
        text = "EXEC #temp_proc '13800138000'"
        result = sanitize_sql_text(text)
        assert "13800138000" not in result
        assert REDACTED in result

    def test_normal_proc_positional_redacted(self):
        result = sanitize_sql_text("EXEC [db].[dbo].[my_proc] 1, 2")
        assert result == "EXEC [db].[dbo].[my_proc] <REDACTED>, <REDACTED>"


class TestSanitizeSqlTextDefensive:
    """防御性兜底：绝不因异常路径返回原文"""

    def test_none_returns_none(self):
        assert sanitize_sql_text(None) is None

    def test_empty_returns_empty(self):
        assert sanitize_sql_text("") == ""

    def test_non_str_returns_failed(self):
        assert sanitize_sql_text(b"SELECT 1") == SANITIZE_FAILED
        assert sanitize_sql_text({"sql": "SELECT 1"}) == SANITIZE_FAILED


class TestSanitizeRowsSqlText:
    """批量脱敏：按字段处理，单行/单字段失败不影响其他行"""

    def test_batch_default_field(self):
        rows = [
            {"sql_text": "WHERE phone='13800138000'"},
            {"sql_text": "SELECT 1"},
        ]
        sanitize_rows_sql_text(rows)
        assert rows[0]["sql_text"] == "WHERE phone='<REDACTED>'"
        assert rows[1]["sql_text"] == "SELECT 1"

    def test_batch_custom_field(self):
        rows = [{"event_info": "phone='13800138000'", "other": "keep"}]
        sanitize_rows_sql_text(rows, fields=("event_info",))
        assert "13800138000" not in rows[0]["event_info"]
        assert rows[0]["other"] == "keep"

    def test_batch_skip_non_dict(self):
        rows = ["not a dict", {"sql_text": "SELECT 1"}]
        sanitize_rows_sql_text(rows)
        assert rows[0] == "not a dict"
        assert rows[1]["sql_text"] == "SELECT 1"
