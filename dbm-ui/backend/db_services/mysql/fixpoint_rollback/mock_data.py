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

FIXPOINT_LOG_DATA = {
    "count": 10,
    "results": [
        {
            "databases": ["xxx123"],
            "databases_ignore": [],
            "tables": ["xxx1"],
            "tables_ignore": [],
            "source_cluster": {
                "id": 32,
                "name": "XXX-test-1",
                "immute_domain": "spider.XXX-test-1.dba.db",
            },
            "target_cluster": {
                "cluster_id": 1,
                "nodes": {
                    "spider": [
                        {"ip": "127.0.0.1", "xxx": "xxx"},
                        {"ip": "127.0.0.1", "xxx": "xxx"},
                    ],
                    "backend_group": [
                        {
                            "slave": {"ip": "127.0.0.1", "xxx": "xxx"},
                            "master": {"ip": "127.0.0.1", "xxx": "xxx"},
                        },
                        {
                            "slave": {"ip": "127.0.0.1", "xxx": "xxx"},
                            "master": {"ip": "127.0.0.1", "xxx": "xxx"},
                        },
                    ],
                },
            },
            "ticket_id": 324,
            "rollback_type": "REMOTE_AND_TIME",
            "rollback_time": "2023-07-31 12:12:01",
            "backupinfo": "",
        }
    ],
}
