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
from rest_framework import serializers

from backend.db_services.mysql.sql_import.constants import MAX_UPLOAD_SQL_FILE_NAME_LENGTH
from backend.db_services.mysql.sql_import.validators import validate_sql_file_name, validate_sql_file_name_field

# 语法检查 execute_objects[].sql_files 的页面占位符，字段级校验器必须放行
PLACEHOLDER_CASES = ["/", " / ", "  /  "]

# 放行的真实文件名（字段级校验器，不带后缀约束）
ALLOWED_NAMES = [
    "a.sql",
    "A.SQL",
    "update_user.sql",
    "update-user.sql",
    "update_user_01.sql",
    "v1.0.0.sql",
    "变更脚本.sql",
    "测试_01-02.sql",
    "员工表-2026.SQL",
    "123456.sql",
    "a",
    "README",
    " a.sql ",  # 前后空白会被 strip 掉，内部空白才拦截
]

# 拦截的文件名：(取值, 错误信息关键字)
REJECTED_NAMES = [
    ("", "不能为空"),
    ("   ", "不能为空"),
    (None, "不能为空"),
    ("a\\b.sql", "路径分隔符"),
    ("..\\a.sql", "路径分隔符"),
    ("../a.sql", "'..'"),
    ("a..sql", "'..'"),
    (".hidden.sql", "以 '.' 开头"),
    ("a b.sql", "空白或控制字符"),
    ("a\tb.sql", "空白或控制字符"),
    ("a\nb.sql", "空白或控制字符"),
    ("a\x00.sql", "空白或控制字符"),
    ("a/b.sql", "非法字符"),
    ("/etc/passwd", "非法字符"),
    ("/var/lib/a.sql", "非法字符"),
    ("a;b.sql", "非法字符"),
    ("a'b.sql", "非法字符"),
    ('a"b.sql', "非法字符"),
    ("$(whoami).sql", "非法字符"),
    ("a*.sql", "非法字符"),
    ("a?.sql", "非法字符"),
    ("a|b.sql", "非法字符"),
    ("a>b.sql", "非法字符"),
    ("a#b.sql", "非法字符"),
    ("a@b.sql", "非法字符"),
    ("a%b.sql", "非法字符"),
    ("a&b.sql", "非法字符"),
    ("a~b.sql", "非法字符"),
    ("sqlé.sql", "非法字符"),
    ("テスト.sql", "非法字符"),
    ("ａ.sql", "非法字符"),  # 全角字母
]

# 后缀校验：(取值, suffix, 是否放行)
SUFFIX_CASES = [
    ("a.sql", ".sql", True),
    ("A.SQL", ".sql", True),
    ("a.js", ".js", True),
    ("a.txt", ".sql", False),
    ("a.sql.bak", ".sql", False),
    ("a.sql", ".js", False),
]


class TestValidateSQLFileNameField:
    """字段级校验器：语法检查 execute_objects[].sql_files"""

    @pytest.mark.parametrize("value", PLACEHOLDER_CASES)
    def test_placeholder_is_allowed(self, value):
        """占位符 "/" 放行"""
        assert validate_sql_file_name_field(value) is None

    @pytest.mark.parametrize("value", ALLOWED_NAMES)
    def test_allowed_names(self, value):
        """常规文件名放行"""
        assert validate_sql_file_name_field(value) is None

    @pytest.mark.parametrize("value,error", REJECTED_NAMES)
    def test_rejected_names(self, value, error):
        """非法文件名拦截，错误信息可读"""
        with pytest.raises(serializers.ValidationError) as exc:
            validate_sql_file_name_field(value)
        assert error in str(exc.value)

    def test_length_boundary(self):
        """长度边界：120 个字符放行，121 个字符拦截"""
        limited = MAX_UPLOAD_SQL_FILE_NAME_LENGTH
        assert validate_sql_file_name_field("a" * (limited - 4) + ".sql") is None

        with pytest.raises(serializers.ValidationError) as exc:
            validate_sql_file_name_field("a" * (limited - 3) + ".sql")
        assert "超长" in str(exc.value)


class TestValidateSQLFileName:
    """通用文件名校验：suffix 为空时也拒绝占位符"""

    def test_placeholder_rejected_without_field_validator(self):
        """占位符只在字段级校验器放行，通用校验不认"""
        with pytest.raises(serializers.ValidationError) as exc:
            validate_sql_file_name("/")
        assert "非法字符" in str(exc.value)

    @pytest.mark.parametrize("value,suffix,allowed", SUFFIX_CASES)
    def test_suffix(self, value, suffix, allowed):
        """后缀校验：.sql 用于 MySQL/TenDBCluster，.js 用于 MongoDB"""
        if allowed:
            assert validate_sql_file_name(value, suffix)
        else:
            with pytest.raises(serializers.ValidationError) as exc:
                validate_sql_file_name(value, suffix)
            assert "必须以" in str(exc.value)

    def test_strip_return_value(self):
        """通用校验返回归一化后的文件名"""
        assert validate_sql_file_name("  a.sql  ") == "a.sql"
