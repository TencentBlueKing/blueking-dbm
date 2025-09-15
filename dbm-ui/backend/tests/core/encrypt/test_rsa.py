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

from backend.core.encrypt import rsa


class TestRSAEncryptFunctionality:
    """测试RSA加密功能"""

    def test_rsa_encrypt_decrypt(self):
        """测试RSA加密解密"""
        private_key, public_key = rsa.RSAUtil.generate_keys()
        rsa_util = rsa.RSAUtil(public_extern_key=public_key, private_extern_key=private_key)

        test_message = "Hello, World! This is a test message."
        encrypted_message = rsa_util.encrypt(test_message)
        assert encrypted_message != test_message
        decrypted_message = rsa_util.decrypt(encrypted_message)
        assert decrypted_message == test_message

    def test_rsa_sign_verify(self):
        """测试RSA签名验证"""
        private_key, public_key = rsa.RSAUtil.generate_keys()
        rsa_util = rsa.RSAUtil(public_extern_key=public_key, private_extern_key=private_key)

        test_message = "Hello, World!"
        signature = rsa_util.sign(test_message)
        assert rsa_util.verify(test_message, signature) is True
        assert rsa_util.verify("Wrong message", signature) is False

    def test_rsa_encrypt_without_public_key(self):
        """测试没有公钥时加密抛出异常"""
        with pytest.raises(ValueError, match="public_key_obj must be set"):
            rsa.RSAUtil().encrypt("test")

    def test_rsa_decrypt_without_private_key(self):
        """测试没有私钥时解密抛出异常"""
        with pytest.raises(ValueError, match="private_key_obj must be set"):
            rsa.RSAUtil().decrypt("test")

    def test_rsa_sign_without_private_key(self):
        """测试没有私钥时签名抛出异常"""
        with pytest.raises(ValueError, match="private_key_obj must be set"):
            rsa.RSAUtil().sign("test")

    def test_rsa_verify_without_public_key(self):
        """测试没有公钥时验证抛出异常"""
        with pytest.raises(ValueError, match="public_key_obj must be set"):
            rsa.RSAUtil().verify("test", b"signature")
