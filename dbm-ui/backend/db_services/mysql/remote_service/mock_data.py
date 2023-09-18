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

SHOW_DATABASES_REQUEST_DATA = {"cluster_ids": [1, 2]}

SHOW_DATABASES_RESPONSE_DATA = [
    {"cluster_id": 1, "databases": ["db1", "db2"]},
    {"cluster_id": 2, "databases": ["db2", "db3"]},
]

SHOW_TABLES_RESPONSE_DATA = [{"cluster_id": 1, "table_data": {"db1": [], "db2": [], "db3": ["test1"]}}]

CHECK_CLUSTER_DATABASE_REQUEST_DATA = {"infos": [{"cluster_id": 1, "db_names": ["test1", "test2"]}]}

CHECK_CLUSTER_DATABASE_RESPONSE_DATA = [
    {"cluster_id": 63, "db_names": ["db1", "db2"], "check_info": {"db1": False, "db2": True}}
]

FLASHBACK_CHECK_DATA = [
    {
        "cluster_id": 63,
        "databases": ["kkjj"],
        "databases_ignore": [],
        "tables": [],
        "tables_ignore": [],
        "message": "this is a error message",
    },
    {
        "cluster_id": 63,
        "databases": [],
        "databases_ignore": [],
        "tables": ["iijkk"],
        "tables_ignore": [],
        "message": "this is a error message",
    },
    {"cluster_id": 63, "databases": [], "databases_ignore": [], "tables": [], "tables_ignore": [], "message": ""},
]
