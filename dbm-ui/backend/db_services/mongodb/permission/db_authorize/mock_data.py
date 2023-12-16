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

PRE_CHECK_AUTHORIZE_RULES_DATA = {
    "mongo_users": [{"user": "admin.test", "access_dbs": ["db1", "db2"]}],
    "target_instances": ["gamedb.test.blueking.db"],
    "cluster_type": "tendbha",
    "cluster_ids": [1],
}

PRE_CHECK_AUTHORIZE_RULES_RESPONSE_DATA = {
    "pre_check": True,
    "message": "ok",
    "authorize_uid": "c0e80efaxxxxx9e7c2afcf9e926b",
    "authorize_data": [
        {
            "cluster_ids": [1],
            "username": "test",
            "password": "password",
            "auth_db": "admin",
            "rule_sets": [{"db": "db", "privileges": ["read", "write"]}],
        }
    ],
}
