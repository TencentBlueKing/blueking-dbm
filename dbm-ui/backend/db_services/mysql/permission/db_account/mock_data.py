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

CREATE_ACCOUNT_REQUEST = {"user": "admin", "password": "0dKD9,;{s1"}

DELETE_ACCOUNT_REQUEST = {"account_id": 1}

UPDATE_ACCOUNT_REQUEST = {"account_id": 1, "password": "288ok,12.;[D"}

ADD_MYSQL_ACCOUNT_RULE_REQUEST = {
    "account_id": 31,
    "access_db": "sword_user",
    "privilege": {"dml": ["select", "update", "delete"], "ddl": ["create"], "glob": ["REPLICATION SLAVE"]},
}

MODIFY_MYSQL_ACCOUNT_RULE_REQUEST = {
    "account_id": 15,
    "access_db": "datamain, mating",
    "privilege": {"dml": "select,update", "ddl": "create", "global": "REPLICATION SLAVE"},
    "rule_id": 1,
}

DELETE_MYSQL_ACCOUNT_RULE_REQUEST = {"rule_id": 1}

LIST_MYSQL_ACCOUNT_RULE_RESPONSE = {
    "count": 1,
    "items": [
        {
            "account": {
                "bk_biz_id": 1,
                "user": "admin",
                "creator": "admin",
                "create_time": "2022-09-06 20:20:17",
                "account_id": 31,
                "id": 1,
            },
            "rules": [
                {
                    "account_id": 31,
                    "bk_biz_id": 1,
                    "creator": "",
                    "create_time": "2022-09-06 20:22:17",
                    "id": 24,
                    "dbname": "datamain",
                    "priv": "select,update,delete,create",
                }
            ],
        }
    ],
}

CHECK_PASSWORD_STRENGTH_REQUEST = {"password": "This is an encrypted password"}

VERIFY_PASSWORD_STRENGTH_INFO_RESPONSE = {
    "is_strength": False,
    "password_verify_info": {
        "lowercase_valid": True,
        "uppercase_valid": True,
        "numbers_valid": False,
        "symbols_valid": False,
        "repeats_valid": False,
        "follow_letters_valid": True,
        "follow_symbols_valid": True,
        "follow_keyboards_valid": True,
        "follow_numbers_valid": False,
        "min_length_valid": False,
        "max_length_valid": True,
    },
}
