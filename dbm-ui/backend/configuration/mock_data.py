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

PASSWORD_POLICY = {
    "account_type": "mysql",
    "policy": {
        "follow": {
            "limit": 4,
            "letters": True,
            "numbers": False,
            "repeats": False,
            "symbols": True,
            "keyboards": True,
        },
        "numbers": True,
        "symbols": True,
        "lowercase": True,
        "uppercase": False,
        "max_length": 20,
        "min_length": 10,
    },
}

CREATE_IP_WHITELIST_DATA = {"bk_biz_id": 1, "remark": "123", "ips": ["127.0.0.1", "127.0.0.2"]}
