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

from django.utils.translation import gettext as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

# 默认编码
ENCODING = "utf-8"

# AES配置
AES_BLOCK_SIZE = 16
AES_PADDING = "\0"


class CipherPadding(str, StructuredEnum):
    """填充标志"""

    PKCS1 = EnumField("PKCS1", _("PKCS1"))
    PKCS1_OAEP = EnumField("PKCS1_OAEP", _("PKCS1_OAEP"))


class KeyObjType(str, StructuredEnum):
    """密钥对象类型"""

    PRIVATE_KEY_OBJ = EnumField("private_key_obj", _("私钥对象"))
    PUBLIC_KEY_OBJ = EnumField("public_key_obj", _("公钥对象"))


class AsymmetricCipherKeyType(str, StructuredEnum):
    """密钥类型"""

    PRIVATE_KEY = EnumField("PRIVATE_KEY", _("私钥"))
    PUBLIC_KEY = EnumField("PUBLIC_KEY", _("公钥"))


class AsymmetricCipherConfigType(str, StructuredEnum):
    """
    系统配置的非对称加密类型
    一般在不同场景进行加密传输时，需要对应不同的密钥对
    """

    PASSWORD = EnumField("password", _("平台密码的非对称秘钥"))
    PROXYPASS = EnumField("proxypass", _("透传接口的非对称秘钥"))
    CLOUD = EnumField("cloud", _("云区域服务的非对称秘钥"))

    @classmethod
    def get_cipher_cloud_name(cls, bk_cloud_id: int):
        return f"{cls.CLOUD.value}-{bk_cloud_id}"


class AsymmetricCipherType(str, StructuredEnum):
    """非对称加密算法类型"""

    RSA = EnumField("RSA", _("RSA"))
    SM2 = EnumField("SM2", _("SM2"))


class SymmetricCipherType(str, StructuredEnum):
    """对称加密算法类型"""

    AES = EnumField("AES", _("AES"))
    SM4 = EnumField("SM4", _("SM4"))
