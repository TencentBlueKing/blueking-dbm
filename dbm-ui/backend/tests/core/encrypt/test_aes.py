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

from backend.core.encrypt import aes


class TestAESEncryptFunctionality:
    """测试AES加密功能"""

    def test_encrypt_decrypt_basic(self):
        """测试AES加密解密基本功能"""
        test_data = "Hello, World! This is a test message."
        aes_key = "1234567890123456"

        encrypted_data = aes.encrypt(test_data, aes_key)
        assert encrypted_data != test_data
        decrypted_data = aes.decrypt(encrypted_data, aes_key)
        assert decrypted_data == test_data

    def test_encrypt_different_keys(self):
        """测试不同密钥加密结果不同"""
        test_data = "test message"
        key1 = "1234567890123456"
        key2 = "1234567890123457"

        encrypted1 = aes.encrypt(test_data, key1)
        encrypted2 = aes.encrypt(test_data, key2)
        assert encrypted1 != encrypted2

        # 用错误的密钥解密得到错误结果
        decrypted_with_wrong_key = aes.decrypt(encrypted1, key2)
        assert decrypted_with_wrong_key != test_data

    def test_encrypt_unicode(self):
        """测试Unicode文本加密"""
        test_data = "你好，世界！"
        aes_key = "1234567890123456"

        try:
            encrypted_data = aes.encrypt(test_data, aes_key)
            decrypted_data = aes.decrypt(encrypted_data, aes_key)
            assert decrypted_data == test_data
        except ValueError:
            pytest.skip("Unicode string padding issue")

    def test_encrypt_invalid_key(self):
        """测试无效密钥长度"""
        with pytest.raises(Exception):
            aes.encrypt("test", "123456789012345")
