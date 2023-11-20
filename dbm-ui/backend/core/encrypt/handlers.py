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
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from bkcrypto.asymmetric.ciphers import BaseAsymmetricCipher
from bkcrypto.contrib.django.ciphers import asymmetric_cipher_manager, symmetric_cipher_manager
from bkcrypto.symmetric.ciphers import BaseSymmetricCipher
from django.db import transaction
from django.utils.crypto import get_random_string

from backend import env
from backend.core.encrypt.constants import AsymmetricCipherConfigType, AsymmetricCipherKeyType
from backend.core.encrypt.models import AsymmetricCipherKey

logger = logging.getLogger("root")


class SymmetricHandler:
    """对称加密处理类"""

    symmetric_cipher: BaseSymmetricCipher = symmetric_cipher_manager.cipher(using="default")

    @classmethod
    def encrypt(cls, content):
        """
        对称算法加密
        @param content: 待加密内容
        """
        return cls.symmetric_cipher.encrypt(content)

    @classmethod
    def decrypt(cls, content):
        """
        对称算法解密
        @param content: 待解密内容
        """
        return cls.symmetric_cipher.decrypt(content)


class AsymmetricHandler:
    """非对称加密处理类"""

    asymmetric_cipher_pools: Dict[str, BaseAsymmetricCipher] = {}

    @classmethod
    def get_or_generate_cipher_instance(cls, name):
        """
        获取或生成非对称加密实例
        @param name: 密钥名称
        """
        if name in cls.asymmetric_cipher_pools:
            return cls.asymmetric_cipher_pools[name]

        # 实例化一个asymmetric_cipher
        asymmetric_cipher: BaseAsymmetricCipher = asymmetric_cipher_manager.cipher(using="default")
        # 获取/创建密钥对
        private_key, public_key = cls.get_or_generate_key_pair(asymmetric_cipher, name)
        # 对asymmetric_cipher载入公私钥
        asymmetric_cipher.config.private_key = asymmetric_cipher.load_private_key(key_str=private_key)
        asymmetric_cipher.config.public_key = asymmetric_cipher.load_public_key(key_str=public_key)

        # 缓存asymmetric_cipher实例，避免重复创建
        cls.asymmetric_cipher_pools[name] = asymmetric_cipher
        return asymmetric_cipher

    @classmethod
    def get_or_generate_key_pair(
        cls, asymmetric_cipher: BaseAsymmetricCipher, name: str, description: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        获取或生成非对称加密的私钥/密钥到DB
        @param asymmetric_cipher: 非对称加密实例
        @param name: 密钥名称
        @param description: 密钥描述
        """
        description = description or f"About {name}'s cipher keys"
        try:
            private_key = AsymmetricCipherKey.objects.get(
                name=name, type=AsymmetricCipherKeyType.PRIVATE_KEY.value, algorithm=env.ASYMMETRIC_CIPHER_TYPE
            ).content
            public_key = AsymmetricCipherKey.objects.get(
                name=name, type=AsymmetricCipherKeyType.PUBLIC_KEY.value, algorithm=env.ASYMMETRIC_CIPHER_TYPE
            ).content
        except AsymmetricCipherKey.DoesNotExist:
            private_key, public_key = asymmetric_cipher.generate_key_pair()
            # 公私钥的创建需保证原子性
            with transaction.atomic():
                asymmetric_keys = [
                    AsymmetricCipherKey(
                        name=name,
                        type=AsymmetricCipherKeyType.PRIVATE_KEY.value,
                        algorithm=env.ASYMMETRIC_CIPHER_TYPE,
                        description=f"Private Key::{description}",
                        content=private_key,
                    ),
                    AsymmetricCipherKey(
                        name=name,
                        type=AsymmetricCipherKeyType.PUBLIC_KEY.value,
                        algorithm=env.ASYMMETRIC_CIPHER_TYPE,
                        description=f"Public Key::{description}",
                        content=public_key,
                    ),
                ]
                AsymmetricCipherKey.objects.bulk_create(asymmetric_keys)

        return private_key, public_key

    @classmethod
    def fetch_public_keys(cls, names: List[str]) -> List[Dict[str, Any]]:
        """
        获取公钥列表，不支持模糊查询
        :param names: 公钥名称列表
        :return: 相关公钥信息
        """

        public_key_details: List[Dict[str, Any]] = AsymmetricCipherKey.objects.filter(
            type=AsymmetricCipherKeyType.PUBLIC_KEY.value, name__in=set(names), algorithm=env.ASYMMETRIC_CIPHER_TYPE
        ).values("name", "description", "content")

        hit_internal_rsa_key_names: Set[str] = set()
        public_key_infos: List[Dict[str, Any]] = []
        for public_key_detail in public_key_details:
            public_key_infos.append(public_key_detail)
            hit_internal_rsa_key_names.add(public_key_detail["name"])

        # 如果请求的内部密钥不存在，生成后返回
        query_internal_rsa_key_names = {name for name in names if name in AsymmetricCipherConfigType.get_values()}
        internal_rsa_key_names_to_be_created = query_internal_rsa_key_names - hit_internal_rsa_key_names

        for name in internal_rsa_key_names_to_be_created:
            cipher_instance = cls.get_or_generate_cipher_instance(name)
            public_key_infos.append(
                {
                    "name": name,
                    "description": name,
                    "content": cipher_instance.export_public_key(),
                }
            )

        return public_key_infos

    @classmethod
    def add_salt(cls, content: str) -> str:
        """
        对password进行加盐加密
        1. 随机对字符中插入字符串
        2. 以salt为秘钥进行aes加密
        @param content: 待加盐内容
        """
        salt = get_random_string(len(content))
        cross_salt_content = list(itertools.chain.from_iterable(zip(content, salt)))
        cross_salt_content = "".join(cross_salt_content)
        return SymmetricHandler.encrypt(content=cross_salt_content)

    @classmethod
    def remove_salt(cls, content: str):
        """
        对password进行解密解盐
        1. 以salt为秘钥进行aes解密
        2. 去掉随机字符串
        @param content: 待解密内容
        """
        cross_salt_content = SymmetricHandler.decrypt(content=content)
        plain_content = cross_salt_content[0:-1:2]
        return plain_content

    @classmethod
    def encrypt(cls, name: str, content: str, need_salt: bool = True) -> str:
        """
        对敏感内容进行非对称加密
        @param name: 内容的所属类型
        @param content: 待加密内容
        @param need_salt: 是否加盐
        """
        content = cls.add_salt(content) if need_salt else content
        asymmetric_cipher = cls.get_or_generate_cipher_instance(name)
        return asymmetric_cipher.encrypt(content)

    @classmethod
    def decrypt(cls, name: str, content: str, salted: bool = True) -> str:
        """
        对敏感内容进行非对称解密
        @param name: 内容的所属类型
        @param content: 待解密内容
        @param salted: 是否存在加盐
        """
        asymmetric_cipher = cls.get_or_generate_cipher_instance(name)
        plain_content = asymmetric_cipher.decrypt(content)
        plain_content = cls.remove_salt(plain_content) if salted else plain_content
        return plain_content

    @classmethod
    def encrypt_with_pubkey(cls, content: str, pubkey: str):
        """
        指定公钥对内容加密(这种来自外部的秘钥加密默认不适用于内部的加盐操作)
        @param content: 待加密内容
        @param pubkey: 公钥
        """
        temp_asymmetric_cipher: BaseAsymmetricCipher = asymmetric_cipher_manager.cipher(using="default")
        temp_asymmetric_cipher.config.public_key = temp_asymmetric_cipher.load_public_key(pubkey)
        return temp_asymmetric_cipher.encrypt(content)
