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

import base64
from functools import wraps
from typing import Any, List, Optional, Tuple, Union

from Crypto import Util
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_v1_5_cipher
from Crypto.Hash import SHA1
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_v1_5_sign

from backend.core.encrypt.constants import ENCODING, CipherPadding, KeyObjType


def key_obj_checker(key_obj_type: str):
    """
    密钥对象检查器
    :param key_obj_type: KeyObjType
    :return:
    """

    def decorate(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, key_obj_type):
                raise ValueError(f"{key_obj_type} must be set if you want to call {func.__name__}")
            return func(self, *args, **kwargs)

        return wrapper

    return decorate


class RSAUtil:
    """封装rsa的操作函数类"""

    public_key_obj: Optional[RSA.RsaKey] = None
    private_key_obj: Optional[RSA.RsaKey] = None

    @staticmethod
    def generate_keys() -> Tuple[str, str]:
        """
        生成公私钥密钥对
        :return:
        """

        private_key_obj = RSA.generate(2048)
        private_key = private_key_obj.exportKey()
        public_key = private_key_obj.publickey().exportKey()
        return private_key.decode(encoding=ENCODING), public_key.decode(encoding=ENCODING)

    @staticmethod
    def load_key(
        extern_key: Optional[Union[str, bytes]] = None, extern_key_file: Optional[str] = None
    ) -> Optional[RSA.RsaKey]:
        """
        导入rsa密钥
        :param extern_key: 密钥内容
        :param extern_key_file: 密钥文件，
        :return:
        """

        if not (extern_key or extern_key_file):
            return None

        if extern_key_file:
            try:
                with open(file=extern_key_file, mode="r") as extern_key_fs:
                    extern_key = extern_key_fs.read()
            except OSError as e:
                raise OSError(f"can't not read / open extern_key_file -> {extern_key_file}") from e

        return RSA.importKey(extern_key)

    @staticmethod
    def get_block_size(key_obj: RSA.RsaKey, is_encrypt: bool = True) -> int:
        """
        获取加解密最大片长度，用于分割过长的文本，单位：bytes
        :param key_obj:
        :param is_encrypt:
        :return:
        """

        block_size = Util.number.size(key_obj.n) / 8
        reserve_size = 11

        # 解密不需要考虑特殊位
        if not is_encrypt:
            reserve_size = 0

        return int(block_size - reserve_size)

    @staticmethod
    def block_list(lst: Union[str, bytes, List[Any]], block_size) -> Union[str, bytes, List[Any]]:
        """
        序列切片
        :param lst:
        :param block_size:
        :return:
        """
        for idx in range(0, len(lst), block_size):
            yield lst[idx : idx + block_size]

    def __init__(
        self,
        public_extern_key: Optional[Union[str, bytes]] = None,
        private_extern_key: Optional[Union[str, bytes]] = None,
        public_extern_key_file: Optional[str] = None,
        private_extern_key_file: Optional[str] = None,
        padding: str = CipherPadding.PKCS1.value,
    ):
        self.public_key_obj = self.load_key(public_extern_key, public_extern_key_file)
        self.private_key_obj = self.load_key(private_extern_key, private_extern_key_file)
        if padding == CipherPadding.PKCS1_OAEP.value:
            self.cipher_method = PKCS1_OAEP
        else:
            self.cipher_method = PKCS1_v1_5_cipher

    @key_obj_checker(KeyObjType.PUBLIC_KEY_OBJ.value)
    def encrypt(self, message: str) -> str:
        """
        加密
        :param message: 待加密的字符串
        :return: 密文
        """

        message_bytes = message.encode(encoding=ENCODING)
        encrypt_message_bytes = b""
        block_size = self.get_block_size(self.public_key_obj)
        cipher = self.cipher_method.new(self.public_key_obj)

        for block in self.block_list(message_bytes, block_size):
            encrypt_message_bytes += cipher.encrypt(block)

        encrypt_message = base64.b64encode(encrypt_message_bytes)
        return encrypt_message.decode(encoding=ENCODING)

    @key_obj_checker(KeyObjType.PRIVATE_KEY_OBJ.value)
    def decrypt(self, encrypt_message: str) -> str:
        """
        解密
        :param encrypt_message: 密文
        :return: 解密后的信息
        """

        decrypt_message_bytes = b""
        encrypt_message_bytes = base64.b64decode(encrypt_message)
        block_size = self.get_block_size(self.private_key_obj, is_encrypt=False)
        cipher = self.cipher_method.new(self.private_key_obj)

        for block in self.block_list(encrypt_message_bytes, block_size):
            decrypt_message_bytes += cipher.decrypt(block, "")

        return decrypt_message_bytes.decode(encoding=ENCODING)

    @key_obj_checker(KeyObjType.PRIVATE_KEY_OBJ.value)
    def sign(self, message: str) -> bytes:
        """
        根据私钥和需要发送的信息生成签名
        :param message: 需要发送给客户端的信息
        :return:
        """

        cipher = PKCS1_v1_5_sign.new(self.private_key_obj)
        sha = SHA1.new(message.encode(encoding=ENCODING))
        signature = cipher.sign(sha)

        return base64.b64encode(signature)

    @key_obj_checker(KeyObjType.PUBLIC_KEY_OBJ.value)
    def verify(self, message: str, signature: bytes):
        """
        使用公钥验证签名
        :param message: 客户端接受的信息
        :param signature: 签名
        :return:
        """

        signature = base64.b64decode(signature)
        cipher = PKCS1_v1_5_sign.new(self.public_key_obj)
        sha = SHA1.new(message.encode(encoding=ENCODING))

        return cipher.verify(sha, signature)
