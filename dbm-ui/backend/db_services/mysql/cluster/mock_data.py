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

FIND_RELATED_CLUSTERS_BY_ID_REQUEST_DATA = {"cluster_ids": [1, 2]}

FIND_RELATED_CLUSTERS_BY_ID_RESPONSE_DATA = [
    {"cluster_id": 1, "cluster_info": {}, "related_clusters": []},
    {"cluster_id": 2, "cluster_info": {}, "related_clusters": []},
]

FIND_RELATED_CLUSTERS_BY_INSTANCE_REQUEST_DATA = {
    "instances": [
        {"bk_host_id": 1, "bk_cloud_id": 0, "ip": "127.0.0.1", "port": 20000},
        {"bk_host_id": 2, "bk_cloud_id": 0, "ip": "127.0.0.2", "port": 20001},
    ]
}

FIND_RELATED_CLUSTERS_BY_INSTANCE_RESPONSE_DATA = [
    {"bk_host_id": 1, "cluster_info": {}, "related_clusters": []},
    {"bk_host_id": 2, "cluster_info": {}, "related_clusters": []},
]

QUERY_CLUSTERS_REQUEST_DATA = {
    "cluster_filters": [
        {"immute_domain": "test.db1"},
        {"immute_domain": "test.db2"},
    ]
}

QUERY_CLUSTERS_RESPONSE_DATA = [
    {"id": 1, "immute_domain": "test.db1", "...": "..."},
    {"id": 2, "immute_domain": "test.db2", "...": "..."},
]

GET_INTERSECTED_SLAVE_MACHINES_RESPONSE_DATA = [
    {"ip": "1.1.1.1", "bk_host_id": 1, "bk_cloud_id": 0, "bk_biz_id": 2000522222},
    {"ip": "1.1.1.2", "bk_host_id": 2, "bk_cloud_id": 0, "bk_biz_id": 2000522222},
]

GET_TENDB_RELATED_MACHINES_RESPONSE_DATA = [
    {
        "cluster_id": 28,
        "remote_machines": [
            {
                "remote_master": {
                    "creator": "admin",
                    "updater": "",
                    "ip": "127.0.0.1",
                    "bk_biz_id": 3,
                    "db_module_id": 4,
                    "access_layer": "storage",
                    "machine_type": "remote",
                    "cluster_type": "tendbcluster",
                    "...": "...",
                    "spec_id": 89,
                    "spec_config": {},
                },
                "remote_slave": {
                    "creator": "admin",
                    "updater": "",
                    "ip": "127.0.0.1",
                    "bk_biz_id": 3,
                    "db_module_id": 4,
                    "access_layer": "storage",
                    "machine_type": "remote",
                    "cluster_type": "tendbcluster",
                    "...": "...",
                    "spec_id": 89,
                    "spec_config": {},
                },
            }
        ],
    }
]

GET_TENDB_REMOTE_PAIRS_RESPONSE_DATA = [
    {
        "cluster_id": 29,
        "remote_pairs": [
            {
                "remote_db": {
                    "name": "",
                    "ip": "127.0.0.1",
                    "port": 20001,
                    "instance": "127.0.0.1:20001",
                    "status": "running",
                    "phase": "online",
                    "bk_instance_id": 1945,
                    "bk_host_id": 231,
                    "bk_cloud_id": 0,
                    "spec_config": {},
                    "bk_biz_id": 3,
                },
                "remote_dr": {
                    "name": "",
                    "ip": "127.0.0.2",
                    "port": 20001,
                    "instance": "127.0.0.2:20001",
                    "status": "running",
                    "phase": "online",
                    "bk_instance_id": 1944,
                    "bk_host_id": 232,
                    "bk_cloud_id": 0,
                    "spec_config": {},
                    "bk_biz_id": 3,
                },
            }
        ],
    },
    {"cluster_id": 30, "remote_pairs": ["..."]},
]
