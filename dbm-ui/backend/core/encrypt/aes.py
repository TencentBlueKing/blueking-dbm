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

from Crypto.Cipher import AES

from backend.core.encrypt.constants import AES_BLOCK_SIZE, AES_PADDING
from backend.utils.string import base64_encode


def pad_it(data):
    """
    加密的填充函数
    """
    return data + (AES_BLOCK_SIZE - len(data) % AES_BLOCK_SIZE) * chr(AES_BLOCK_SIZE - len(data) % AES_BLOCK_SIZE)


def add_to_16(text):
    """
    加密的填充函数
    """
    return text + AES_PADDING * (AES_BLOCK_SIZE - len(text) % AES_BLOCK_SIZE)


def encrypt(data: str, aes_key: str) -> str:
    """
    AES加密算法函数
    @param data: 需要加密数据结构体，str格式
    @param aes_key: 加密的key，目前算法key的长度必须是16，24，32
    """
    aes_key = aes_key.encode("utf-8")
    cipher = AES.new(aes_key, AES.MODE_CBC, aes_key)
    data = cipher.encrypt(pad_it(data).encode("utf-8"))
    return base64_encode(data)


def decrypt(data: str, aes_key: str) -> str:
    """
    AES 解密算法函数
    @param data: 需要加密数据结构体，str格式
    @param aes_key: 加密的key，目前算法key的长度必须是16，24，32
    """
    aes_key = aes_key.encode("utf-8")
    data = base64.b64decode(data.encode("utf-8"))
    cipher = AES.new(aes_key, AES.MODE_CBC, aes_key)
    msg = cipher.decrypt(data)
    padding_len = msg[len(msg) - 1]
    return msg[0:-padding_len].decode("utf-8")
