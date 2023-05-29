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

POLICY_DATA = {
    "min_length": 8,
    "max_length": 15,
    "lowercase": True,
    "uppercase": True,
    "numbers": True,
    "symbols": True,
    "follow": {"limit": 5, "repeats": True, "keyboards": True, "numbers": True, "letters": True, "symbols": True},
}

VALID_PASSWORD_LIST = ["9uH;2sxkkkk", "8sk9USM,;", "[]8IK<>s0KMXks"]

INVALID_PASSWORD_LIST = [
    "",
    "21d9qdq23",
    "91kkkkkk",
    "yyY;p123456",
    "abCdEfGHi12;/",
    "!@#$%^&*(*&U%j7",
    "1qaz5tgbl,K25",
    "9sandJKS8kd;'dsa32dw32239",
    "qwRtYuIoA,45",
]

ACCOUNT = {"user": "admin", "password": "helloworld"}

ACCOUNT_RULE = {"access_db": "datamain"}
