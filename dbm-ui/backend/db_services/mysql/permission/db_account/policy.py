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

import itertools
from typing import Dict, List, Union

from password_validation import PasswordPolicy
from password_validation.calculate import Classifier
from password_validation.character_pool import CharacterPool
from password_validation.funcs import less_than_or_equal_to
from password_validation.password import Password
from password_validation.policy import MakePasswordRequirement, PasswordRequirement


class DBCharacterPool(CharacterPool):
    """
    自定义密码字符池
    """

    def __init__(self):
        super().__init__()

        # 为密码池添加连续的字母序，数字序，特殊字符序和键盘序
        self.follow_numbers = "0123456789"
        self.follow_letters = "abcdefghijklmnopqrstuvwxyz"
        self.follow_symbols = "~!@#$%^&*()_+"
        self.follow_keyboard_row = ["qwertyuiop[]\\", "asdfghjkl;'", "zxcvbnm,./"]
        self.follow_keyboard_col = ["1qaz", "2wsx", "3edc", "4rfv", "5tgb", "6yhn", "7ujm", "8ik,", "9ol.", "0p;/"]


class DBPassword(Password):
    """
    自定义密码类，增加其他密码判断属性
    """

    def __init__(self, password: str, character_pool: CharacterPool = None):
        super().__init__(password, character_pool)

        self.pool = DBCharacterPool()
        self.lower_password = self.password.lower()

        # 设置匹配连续键盘序的数量，默认连续出现4个连续字符以上才计入答案
        self.follow_keyboards = 0
        for keyboard_row in self.pool.follow_keyboard_row:
            lcs_len = self._find_longest_common_substr(keyboard_row, self.lower_password)
            if lcs_len > 3:
                self.follow_keyboards += lcs_len

        for keyboard_col in self.pool.follow_keyboard_col:
            if keyboard_col in self.lower_password:
                self.follow_keyboards += 4

        # 设置连续匹配字母，数字，字符串的数量
        self.follow_letters = self._find_longest_common_substr(self.pool.follow_letters, self.lower_password)
        self.follow_numbers = self._find_longest_common_substr(self.pool.follow_numbers, self.password)
        self.follow_symbols = self._find_longest_common_substr(self.pool.follow_symbols, self.password)

        # 设置重复字符的数量(注意password可能为空)
        repeat_count_list = [len(list(str_list)) for _, str_list in itertools.groupby(self.lower_password)]
        self.repeat = max(repeat_count_list or [0])

    @staticmethod
    def _find_longest_common_substr(str1: str, str2: str) -> int:
        """
        寻找str1和str2的最长公共子串
        """

        if len(str1) > len(str2):
            str1, str2 = str2, str1

        max_lcs_len = 0
        for str_index in range(len(str1)):
            if str1[str_index - max_lcs_len : str_index + 1] in str2:
                max_lcs_len += 1

        return max_lcs_len


class DBPasswordPolicy(PasswordPolicy):
    """
    自定义密码强度校验策略
    """

    def __init__(
        self,
        lowercase: int = 0,
        uppercase: int = 0,
        symbols: int = 0,
        numbers: int = 0,
        follow_repeats: int = 0,
        follow_keyboards: int = 0,
        follow_numbers: int = 0,
        follow_letters: int = 0,
        follow_symbols: int = 0,
        whitespace: int = 0,
        other: int = 0,
        min_length: int = 12,
        max_length: int = 128,
        min_entropy: Union[int, float] = 1,
        forbidden_words: list = None,
        character_pool: CharacterPool = None,
        requirement_cls: PasswordRequirement = None,
        classifier: Classifier = None,
    ):
        """
        :param lowercase: 密码至少包含小写字母的数量
        :param uppercase: 密码至少包含大写字母的数量
        :param symbols: 密码至少包含特殊字符的数量
        :param numbers: 密码至少应该包含数字的数量
        :param follow_repeats: 密码最多允许重复的字符数量
        :param follow_keyboards: 密码最多允许连续键盘序的数量
        :param follow_numbers: 密码最多允许连续数字序的数量
        :param follow_letters: 密码最多允许连续字母序的数量
        :param follow_symbols: 密码最多允许连续特殊字符的数量
        :param whitespace: 密码至少包含空格的数量
        :param other: 密码至少包含其他字符的数量
        :param min_length: 密码的最小长度
        :param max_length: 密码的最大长度
        :param min_entropy: 密码的最小熵
        :param forbidden_words: 密码中不应该出现的字符
        :param character_pool: 密码字符池
        :param requirement_cls: 密码校验类
        :param classifier: 评价区分器
        """
        super().__init__(
            lowercase,
            uppercase,
            symbols,
            numbers,
            whitespace,
            other,
            min_length,
            max_length,
            min_entropy,
            forbidden_words,
            character_pool,
            requirement_cls,
            classifier,
        )

        self.pool = DBCharacterPool()
        self.validity_map = {}

        # 设置重复字符校验
        self.repeats = follow_repeats
        self.repeats_requirement = MakePasswordRequirement(
            "the maximum number of repeatable characters",
            self.repeats,
            func=less_than_or_equal_to,
            cls=requirement_cls,
        )

        # 设置连续键盘序校验
        self.follow_keyboards = follow_keyboards
        self.follow_keyboards_requirement = MakePasswordRequirement(
            "the maximum number of sequential keyboard sequence characters",
            self.follow_keyboards,
            func=less_than_or_equal_to,
            cls=requirement_cls,
        )

        # 设置连续数字序校验
        self.follow_numbers = follow_numbers
        self.follow_numbers_requirement = MakePasswordRequirement(
            "the maximum number of consecutive number characters",
            self.follow_numbers,
            func=less_than_or_equal_to,
            cls=requirement_cls,
        )

        # 设置连续字母序校验
        self.follow_letters = follow_letters
        self.follow_letters_requirement = MakePasswordRequirement(
            "the maximum number of consecutive alphabetical characters",
            self.follow_letters,
            func=less_than_or_equal_to,
            cls=requirement_cls,
        )

        # 设置连续特殊字符序校验
        self.follow_symbols = follow_symbols
        self.follow_symbols_requirement = MakePasswordRequirement(
            "the maximum number of consecutive symbols characters",
            self.follow_symbols,
            func=less_than_or_equal_to,
            cls=requirement_cls,
        )

    def test_password(self, password: str, failures_only: bool = True) -> List[int]:
        """
        - 校验密码强度
        :param password: 待测试代码
        :param failures_only: 是否只展示错误结果
        """

        password = DBPassword(password)
        self.validity_map = {
            "lowercase_valid": bool(self.lowercase_requirement(password.lowercase)),
            "uppercase_valid": bool(self.uppercase_requirement(password.uppercase)),
            "numbers_valid": bool(self.numbers_requirement(password.numbers)),
            "symbols_valid": bool(self.symbols_requirement(password.symbols)),
            "repeats_valid": bool(self.repeats_requirement(password.repeat)),
            "follow_letters_valid": bool(self.follow_letters_requirement(password.follow_letters)),
            "follow_symbols_valid": bool(self.follow_symbols_requirement(password.follow_symbols)),
            "follow_keyboards_valid": bool(self.follow_keyboards_requirement(password.follow_keyboards)),
            "follow_numbers_valid": bool(self.follow_numbers_requirement(password.follow_numbers)),
            "min_length_valid": bool(self.min_length_requirement(password.length)),
            "max_length_valid": bool(self.max_length_requirement(password.length)),
        }

        return (
            [i for i in list(self.validity_map.values()) if not i]
            if failures_only
            else list(self.validity_map.values())
        )

    def get_validity_map(self) -> Dict:
        """
        获取校验相关信息，一般和test_password搭配使用
        """

        return self.validity_map
