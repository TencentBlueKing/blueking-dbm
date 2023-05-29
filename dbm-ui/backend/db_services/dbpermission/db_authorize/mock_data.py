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
    "user": "admin",
    "access_dbs": ["user", "group"],
    "source_ips": [
        {"bk_host_id": 1, "ip": "1.1.1.1"},
        {"bk_host_id": 2, "ip": "2.2.2.2"},
    ],
    "target_instances": ["gamedb.privtest55.blueking.db"],
    "cluster_type": "tendbha",
}

PRE_CHECK_AUTHORIZE_RULES_RESPONSE_DATA = {
    "pre_check": True,
    "message": "ok",
    "authorize_uid": "c0e80efa2f5711ed99e7c2afcf9e926b",
    "authorize_data": {
        "user": "admin",
        "access_dbs": ["user", "group"],
        "source_ips": [
            {"bk_host_id": 1, "ip": "1.1.1.1"},
            {"bk_host_id": 2, "ip": "2.2.2.2"},
        ],
        "target_instances": ["gamedb.privtest55.blueking.db"],
        "cluster_type": "tendbha",
    },
}

PRE_CHECK_EXCEL_AUTHORIZE_RULES_DATA = {"authorize_file": "authorize_file.xlsx", "cluster_type": "tendbha"}

PRE_CHECK_EXCEL_AUTHORIZE_RULES_RESPONSE_DATA = {
    "pre_check": True,
    "authorize_uid": "c0e80efa2f5711ed99e7c2afcf9e926b",
    "excel_url": "https://example.com",
    "authorize_data_list": [
        {
            "user": "admin",
            "access_dbs": ["user1", "user2"],
            "source_ips": ["127.0.0.1", "127.0.0.2"],
            "target_instances": ["gamedb.privtest55.blueking.db"],
            "cluster_ids": [96],
            "cluster_type": "tendbha",
        },
    ],
}

ONLINE_MYSQL_RULES_DATA = [
    {
        "user": "admin",
        "source_ip": "127.0.0.1",
        "target_cluster": "admin-moduledb.user.blueking.db1",
        "access_db": "user",
        "authorize_rule": "select",
    },
    {
        "user": "admin",
        "source_ip": "127.0.0.1",
        "target_cluster": "admin-moduledb.user.blueking.db2",
        "access_db": "meta",
        "authorize_rule": "select,insert,drop",
    },
]
