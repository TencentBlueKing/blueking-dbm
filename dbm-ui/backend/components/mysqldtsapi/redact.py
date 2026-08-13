# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

递归脱敏 MySQL DTS 请求里的 password 字段，供写操作日志使用。
"""

PASSWORD_PLACEHOLDER = "******"
_PASSWORD_KEY = "password"


def redact_passwords(value):
    """拷贝后把任意深度、大小写不敏感的 password 键换成占位符；其它值原样保留。"""
    if isinstance(value, dict):
        return {
            key: PASSWORD_PLACEHOLDER if str(key).lower() == _PASSWORD_KEY else redact_passwords(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_passwords(item) for item in value]
    return value
