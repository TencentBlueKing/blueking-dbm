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
from collections import namedtuple
from typing import Any, Dict, List, Optional, Set, Union

from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend import env
from backend.core.encrypt import aes
from backend.core.encrypt.constants import AES_BLOCK_SIZE, RSAConfigType, RSAKeyType
from backend.core.encrypt.exceptions import RSADecryptException, RSAEncryptException
from backend.core.encrypt.models import RSAKey
from backend.core.encrypt.rsa import RSAUtil


class RSAHandler:
    """rsa视图处理类"""

    RSA = namedtuple("RSA", ["rsa_util", "rsa_private_key", "rsa_public_key"])

    @classmethod
    def get_or_generate_rsa_in_db(
        cls, name: str, description: Optional[str] = None, return_rsa_util: bool = True
    ) -> "RSA":
        """
        获取或生成非对称加密的私钥/密钥到DB
        :param name: 密钥名称
        :param description: 密钥描述
        :param return_rsa_util: 是否返回工具对象
        :return: RSA对象
        """

        description = description or f"About {name}'s rsa keys"
        try:
            rsa_private_key = RSAKey.objects.get(name=name, rsa_type=RSAKeyType.PRIVATE_KEY.value)

            # 如果获取到了私钥，此时根据私钥生成或更新公钥
            private_key_obj = RSAUtil.load_key(extern_key=rsa_private_key.content)
            rsa_public_key, __ = RSAKey.objects.update_or_create(
                name=name,
                rsa_type=RSAKeyType.PUBLIC_KEY.value,
                defaults={
                    "description": description,
                    "content": private_key_obj.publickey().exportKey().decode("utf-8"),
                },
            )
        except RSAKey.DoesNotExist:
            private_key, public_key = RSAUtil.generate_keys()

            # 公私钥的更新需保证原子性
            with transaction.atomic():
                rsa_private_key = RSAKey.objects.create(
                    name=name, rsa_type=RSAKeyType.PRIVATE_KEY.value, description=description, content=private_key
                )
                rsa_public_key, __ = RSAKey.objects.update_or_create(
                    name=name,
                    rsa_type=RSAKeyType.PUBLIC_KEY.value,
                    defaults={"description": description, "content": public_key},
                )

        rsa_util = None
        if return_rsa_util:
            rsa_util = RSAUtil(public_extern_key=rsa_public_key.content, private_extern_key=rsa_private_key.content)

        return cls.RSA(rsa_util, rsa_private_key, rsa_public_key)

    @classmethod
    def fetch_public_keys(cls, names: List[str]) -> List[Dict[str, Any]]:
        """
        获取公钥列表，不支持模糊查询
        :param names: 公钥名称列表
        :return: 相关公钥信息
        """

        rsa_public_key_details: List[Dict[str, Any]] = RSAKey.objects.filter(
            rsa_type=RSAKeyType.PUBLIC_KEY.value, name__in=set(names)
        ).values("name", "description", "content")

        hit_internal_rsa_key_names: Set[str] = set()
        public_key_infos: List[Dict[str, Any]] = []
        for rsa_public_key_detail in rsa_public_key_details:
            public_key_infos.append(rsa_public_key_detail)
            hit_internal_rsa_key_names.add(rsa_public_key_detail["name"])

        # 如果请求的内部密钥不存在，生成后返回
        query_internal_rsa_key_names = {name for name in names if name in RSAConfigType.get_values()}
        internal_rsa_key_names_to_be_created = query_internal_rsa_key_names - hit_internal_rsa_key_names

        for name in internal_rsa_key_names_to_be_created:
            rsa_public_key = cls.get_or_generate_rsa_in_db(name=name, return_rsa_util=False).rsa_public_key
            public_key_infos.append(
                {
                    "name": rsa_public_key.name,
                    "description": rsa_public_key.description,
                    "content": rsa_public_key.content,
                }
            )

        return public_key_infos

    @classmethod
    def add_salt(cls, password: str, salt_key: str) -> str:
        """
        对password进行加盐加密
        1. 随机对字符中插入字符串
        2. 以salt为秘钥进行aes加密
        @param password: 待加盐密码
        @param salt_key: 作为aes加密的盐秘钥
        """

        pwd_len = len(password)
        salt = get_random_string(pwd_len)

        cross_salt_pwd = list(itertools.chain.from_iterable(zip(password, salt)))
        cross_salt_pwd = "".join(cross_salt_pwd)
        salt_key = aes.add_to_16(salt_key)[:AES_BLOCK_SIZE]

        return aes.encrypt(data=cross_salt_pwd, aes_key=salt_key)

    @classmethod
    def remove_salt(cls, password: str, salt_key: str):
        """
        对password进行解密解盐
        1. 以salt为秘钥进行aes解密
        2. 去掉随机字符串
        @param password: 待解密密码
        @param salt_key: 作为aes解密的盐秘钥
        """

        salt_key = aes.add_to_16(salt_key)[:AES_BLOCK_SIZE]
        cross_salt_pwd = aes.decrypt(data=password, aes_key=salt_key)
        password = cross_salt_pwd[0:-1:2]
        return password

    @classmethod
    def encrypt_password(cls, public_key: str, password: str, salt: Union[None, str] = env.SECRET_KEY) -> str:
        """
        - 根据公钥和password进行加密
        :param public_key: 公钥
        :param password: 待加密密码
        :param salt: 是否加盐, 默认为secret_key，如果为None，则不加盐
        """

        if salt:
            password = cls.add_salt(password, salt)

        try:
            cipher_password = RSAUtil(public_extern_key=public_key).encrypt(password)
            return cipher_password
        except Exception as e:  # pylint: disable=broad-except
            raise RSAEncryptException(_("密码加密失败: {}").format(e))

    @classmethod
    def decrypt_password(cls, private_key: str, password: str, salt: Union[str, None] = env.SECRET_KEY) -> str:
        """
        - 根据本地私钥和password进行解密
        :param private_key: 私钥
        :param password: 待解密密码
        :param salt: 是否加盐, 默认为secret_key，如果为None，则不加盐
        """

        try:
            plain_password = RSAUtil(private_extern_key=private_key).decrypt(password)
            if salt:
                plain_password = cls.remove_salt(plain_password, salt)
                return plain_password
            else:
                return plain_password
        except Exception as e:  # pylint: disable=broad-except
            raise RSADecryptException(_("密码解密失败: {}").format(e))
