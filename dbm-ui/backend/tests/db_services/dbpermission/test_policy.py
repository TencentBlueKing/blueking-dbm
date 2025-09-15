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
from backend.db_services.dbpermission.db_account.policy import DBCharacterPool, DBPassword, DBPasswordPolicy


class TestDBCharacterPool:
    """测试 DBCharacterPool 类"""

    def test_init(self):
        """测试初始化"""
        pool = DBCharacterPool()
        assert pool.follow_numbers == "0123456789"
        assert pool.follow_letters == "abcdefghijklmnopqrstuvwxyz"
        assert len(pool.follow_keyboard_row) == 3
        assert len(pool.follow_keyboard_col) == 10


class TestDBPassword:
    """测试 DBPassword 类"""

    def test_init_simple(self):
        """测试初始化 - 简单密码"""
        password = DBPassword("Test123")
        assert password.password == "Test123"
        assert password.lower_password == "test123"

    def test_follow_keyboards_row(self):
        """测试键盘序检测 - 横向"""
        password = DBPassword("qwerty123")
        assert password.follow_keyboards >= 4

    def test_follow_keyboards_col(self):
        """测试键盘序检测 - 纵向"""
        password = DBPassword("1qaz2wsx")
        assert password.follow_keyboards >= 4

    def test_follow_letters(self):
        """测试连续字母检测"""
        password = DBPassword("abcdef123")
        assert password.follow_letters >= 4

    def test_follow_numbers(self):
        """测试连续数字检测"""
        password = DBPassword("abc123456")
        assert password.follow_numbers >= 4

    def test_follow_symbols(self):
        """测试连续特殊字符检测"""
        password = DBPassword("test~!@#$")
        assert password.follow_symbols >= 4

    def test_repeat(self):
        """测试重复字符检测"""
        password = DBPassword("aaaa123")
        assert password.repeat == 4

    def test_find_longest_common_substr(self):
        """测试最长公共子串"""
        lcs_len = DBPassword._find_longest_common_substr("abcdef", "cdefgh")
        assert lcs_len == 4

    def test_find_longest_common_substr_no_match(self):
        """测试最长公共子串 - 无匹配"""
        lcs_len = DBPassword._find_longest_common_substr("abc", "xyz")
        assert lcs_len == 0


class TestDBPasswordPolicy:
    """测试 DBPasswordPolicy 类"""

    def test_init_default(self):
        """测试初始化 - 默认参数"""
        policy = DBPasswordPolicy()
        assert policy.min_length == 12
        assert policy.max_length == 128

    def test_init_custom(self):
        """测试初始化 - 自定义参数"""
        policy = DBPasswordPolicy(
            lowercase=1,
            uppercase=1,
            numbers=1,
            symbols=1,
            min_length=8,
            max_length=64,
            follow_repeats=3,
            follow_keyboards=4,
        )
        assert policy.lowercase == 1
        assert policy.repeats == 3

    def test_password_strong(self):
        """测试密码强度 - 强密码"""
        policy = DBPasswordPolicy(
            lowercase=1,
            uppercase=1,
            numbers=1,
            symbols=1,
            min_length=8,
            follow_repeats=10,
            follow_keyboards=10,
            follow_numbers=10,
            follow_letters=10,
            follow_symbols=10,
        )
        failures = policy.test_password("Test@1a2b3c4d")
        assert len(failures) == 0

    def test_password_weak_short(self):
        """测试密码强度 - 太短"""
        policy = DBPasswordPolicy(min_length=12)
        failures = policy.test_password("Test@123")
        assert len(failures) > 0

    def test_password_weak_no_lowercase(self):
        """测试密码强度 - 缺少小写字母"""
        policy = DBPasswordPolicy(lowercase=1)
        failures = policy.test_password("TEST@123456")
        assert len(failures) > 0

    def test_password_weak_no_uppercase(self):
        """测试密码强度 - 缺少大写字母"""
        policy = DBPasswordPolicy(uppercase=1)
        failures = policy.test_password("test@123456")
        assert len(failures) > 0

    def test_password_weak_no_numbers(self):
        """测试密码强度 - 缺少数字"""
        policy = DBPasswordPolicy(numbers=1)
        failures = policy.test_password("Test@abcdefg")
        assert len(failures) > 0

    def test_password_weak_no_symbols(self):
        """测试密码强度 - 缺少特殊字符"""
        policy = DBPasswordPolicy(symbols=1)
        failures = policy.test_password("Test12345678")
        assert len(failures) > 0

    def test_password_weak_too_many_repeats(self):
        """测试密码强度 - 重复字符过多"""
        policy = DBPasswordPolicy(follow_repeats=2)
        failures = policy.test_password("Teaaaaast123")
        assert len(failures) > 0

    def test_password_weak_keyboard_sequence(self):
        """测试密码强度 - 键盘序过多"""
        policy = DBPasswordPolicy(follow_keyboards=3)
        failures = policy.test_password("Test@qwerty")
        assert len(failures) > 0

    def test_password_weak_number_sequence(self):
        """测试密码强度 - 连续数字过多"""
        policy = DBPasswordPolicy(follow_numbers=3)
        failures = policy.test_password("Test@1234567")
        assert len(failures) > 0

    def test_password_weak_letter_sequence(self):
        """测试密码强度 - 连续字母过多"""
        policy = DBPasswordPolicy(follow_letters=3)
        failures = policy.test_password("Test@abcdefg")
        assert len(failures) > 0

    def test_password_weak_symbol_sequence(self):
        """测试密码强度 - 连续特殊字符过多"""
        policy = DBPasswordPolicy(follow_symbols=3)
        failures = policy.test_password("Test~!@#$123")
        assert len(failures) > 0

    def test_test_password_failures_only(self):
        """测试密码 - 仅返回失败项"""
        policy = DBPasswordPolicy(lowercase=1)
        failures = policy.test_password("TEST123456", failures_only=True)
        assert all(not f for f in failures)

    def test_test_password_all_results(self):
        """测试密码 - 返回所有结果"""
        policy = DBPasswordPolicy(lowercase=1)
        results = policy.test_password("test123456", failures_only=False)
        assert len(results) == len(policy.validity_map)

    def test_get_validity_map(self):
        """测试获取校验映射"""
        policy = DBPasswordPolicy(lowercase=1, uppercase=1)
        policy.test_password("Test123456")
        validity_map = policy.get_validity_map()
        assert "lowercase_valid" in validity_map
        assert "uppercase_valid" in validity_map
