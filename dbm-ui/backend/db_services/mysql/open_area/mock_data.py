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

OPENAREA_TEMPLATE_DATA = {
    "config_rules": [
        {
            "source_db": "test6",
            "schema_tblist": ["tb1", "tb2"],
            "data_tblist": ["tb1", "tb2"],
            "target_db_pattern": "DB_{APP}",
            "priv_data": [1, 2, 3],
        }
    ],
    "bk_biz_id": 3,
    "config_name": "test——config7",
    "source_cluster_id": 63,
}

OPENAREA_PREVIEW_DATA = {
    "config_data": [
        {
            "target_cluster": 63,
            "target_cluster_name": "test-lucky",
            "execute_objects": [
                {
                    "source_db": "testdb",
                    "target_db": "O_3_TEST",
                    "schema_tblist": ["test1", "test2"],
                    "data_tblist": ["test1", "test2"],
                }
            ],
        }
    ],
    "rules_set": [
        {
            "user": "admin",
            "source_ips": ["127.0.0.1"],
            "target_instances": ["spider.test-lucky.dba.db"],
            "dbname": ["ddddd", "test"],
            "cluster_type": "tendbcluster",
        },
        {
            "user": "dwq",
            "source_ips": ["127.0.0.1"],
            "target_instances": ["spider.test-lucky.dba.db"],
            "dbname": ["llo"],
            "cluster_type": "tendbcluster",
        },
    ],
}
