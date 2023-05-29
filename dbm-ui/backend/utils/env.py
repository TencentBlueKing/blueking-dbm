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
import logging
import os
from typing import Any

from config import django_env

logger = logging.getLogger("app")

"""
该工具用户获取环境变量相关的内容
"""


def get_env_list(env_prefix):
    """
    获取可以遍历的环境变量信息，并通过一个数组的方式返回
    例如，获取IP0 ~ IPn环境变量, 调用get_env_list(env_prefix="IP"), 返回["x.x.x.x", "x.x.x.x"]
    :param env_prefix: 环境变量前缀
    :return: ["info", "info"]
    """
    index = 0
    result = []
    while True:
        current_name = f"{env_prefix}{index}"
        current_value = os.getenv(current_name)

        # 此轮已经不能再获取新的变量了，可以返回
        # 此处，我们相信变量不存在跳跃的情况
        if current_value is None:
            break

        result.append(current_value)
        index += 1

    logger.info(f"env->[{env_prefix}] got total env count->[{index}]")
    return result


def get_type_env(key: str, default: Any = None, _type: type = str) -> Any:
    """
    获取环境变量并转为目标类型
    :param key: 变量名
    :param default: 默认值，若获取不到环境变量会默认使用该值
    :param _type: 环境变量需要转换的类型，不会转 default
    :return:
    """

    # 支持直接从local.env文件加载变量
    value = django_env.get_value(key, cast=_type, default=default)
    if value is not None:
        return value

    return default
