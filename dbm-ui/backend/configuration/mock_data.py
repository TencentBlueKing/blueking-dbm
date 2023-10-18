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
    "id": 3,
    "name": "password",
    "rule": {
        "max_length": 25,
        "min_length": 6,
        "include_rule": {"numbers": True, "symbols": True, "lowercase": True, "uppercase": True},
        "exclude_continuous_rule": {
            "limit": 3,
            "letters": True,
            "numbers": True,
            "repeats": True,
            "symbols": True,
            "keyboards": True,
        },
    },
    "creator": "admin",
    "create_time": "2023-09-13 10:08:23",
    "operator": "admin",
    "update_time": "2023-09-18 19:51:14",
}

CREATE_IP_WHITELIST_DATA = {"bk_biz_id": 1, "remark": "123", "ips": ["127.0.0.1", "127.0.0.2"]}

VERIFY_PASSWORD_DATA = {
    "is_strength": False,
    "password_verify_info": {
        "lowercase_valid": False,
        "uppercase_valid": False,
        "numbers_valid": False,
        "symbols_valid": False,
        "repeats_valid": True,
        "follow_letters_valid": True,
        "follow_symbols_valid": True,
        "follow_keyboards_valid": True,
        "follow_numbers_valid": True,
        "min_length_valid": True,
        "max_length_valid": True,
    },
}

MYSQL_ADMIN_PASSWORD_DATA = [
    {
        "id": 0,
        "ip": "127.0.0.1",
        "port": 25000,
        "username": "ADMIN",
        "password": "UjY0ZGNbXT8xMk94eGsx",
        "component": "mysql",
        "lock_until": "2023-09-19 19:25:33",
        "operator": "admin",
        "update_time": "2023-09-19 13:02:38",
    }
]
BIZ_SETTINGS_DATA = {
    "key1": "value1",
    "key2": "value2",
    "...": "....",
    # 开区变量表
    "OPEN_AREA_VARS": [{"desc": "test1", "name": "test1"}, {"desc": "test2", "name": "test2"}],
}
