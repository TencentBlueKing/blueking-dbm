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
import typing

from bkcrypto.contrib.django.ciphers import AsymmetricCipherManager as BkAsymmetricCipherManager
from bkcrypto.contrib.django.ciphers import symmetric_cipher_manager
from bkcrypto.contrib.django.init_configs import CipherInitConfig


class AsymmetricCipherManager(BkAsymmetricCipherManager):
    """自定义非对称加密的cipher manager"""

    def _cipher(self, using: typing.Optional[str] = None, cipher_type: typing.Optional[str] = None):
        # 因为后台需要支持多个密钥对，覆写_cipher方法，废弃缓存
        cipher_type: str = cipher_type or self._get_cipher_type_from_settings()
        init_config: CipherInitConfig = self._get_init_config(using=using)
        return self._get_cipher(cipher_type, init_config)


asymmetric_cipher_manager = AsymmetricCipherManager()

symmetric_cipher_manager = symmetric_cipher_manager
