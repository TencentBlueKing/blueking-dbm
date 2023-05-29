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

MYSQL_BACKUP_LOG_FROM_BKLOG = [
    {
        "backup_id": "c4676a9d-4841-11ee-8977-5254002c7706",
        "bill_id": "",
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "time_zone": "CST",
        "cluster_id": 22,
        "cluster_address": "mysql80db.xxxxx.dba.db",
        "shard_value": -1,
        "mysql_host": "127.0.0.1",
        "mysql_port": 20000,
        "master_host": "127.0.0.1",
        "master_port": 20000,
        "mysql_role": "master",
        "binlog_info": {
            "show_master_status": {
                "binlog_file": "binlog20000.000003",
                "binlog_pos": "226547225",
                "gtid": "",
                "master_host": "127.0.0.1",
                "master_port": 20000,
            },
            "show_slave_status": None,
        },
        "backup_begin_time": "2023-09-01 05:03:00",
        "backup_end_time": "2023-09-01 05:03:00",
        "data_schema_grant": "schema",
        "backup_type": "logical",
        "backup_time": "2023-09-01 05:03:00",
        "file_list": [
            "3_22_127.0.0.x_20000_20230901_050300_logical.index",
            "3_22_127.0.0.x_20000_20230901_050300_logical_0.tar",
        ],
        "file_list_details": [
            {
                "file_name": "3_22_127.0.0.x_20000_20230901_050300_logical.index",
                "size": 1063,
                "task_id": "1693515780268496841-0160387296-29220-0",
            },
            {
                "file_name": "3_22_127.0.0.x_20000_20230901_050300_logical_0.tar",
                "size": 3584,
                "task_id": "1693515780326947415-0160387296-29227-0",
            },
        ],
        "index": "3_22_127.0.0.x_20000_20230901_050300_logical.index",
    }
]

TENDBCLUSTER_BACKUP_LOG_FROM_BKLOG = [
    {
        "backup_id": "99ffaed9-4778-11ee-927d-5254000355cf",
        "bill_id": "",
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "time_zone": "CST",
        "cluster_id": 63,
        "cluster_address": "spider.lucky.dba.db",
        "mysql_role": "master",
        "backup_begin_time": "2023-08-31 05:04:00",
        "backup_end_time": "2023-08-31 05:04:00",
        "backup_time": "2023-08-31 05:04:00",
        "spider_node": {
            "backup_begin_time": "2023-08-31 05:04:00",
            "backup_end_time": "2023-08-31 05:04:00",
            "backup_time": "2023-08-31 05:04:00",
            "mysql_role": "spider_master",
            "host": "127.0.0.1",
            "port": 26000,
            "file_list_details": [
                {
                    "file_name": "3_63_127.0.0.x_26000_20230831_050400_logical.index",
                    "size": 1899,
                    "task_id": "1693429440429266047-0160208206-16030-0",
                },
            ],
            "index": {
                "file_name": "3_63_127.0.0.x_25000_20230831_050400_logical.index",
                "size": 1882,
                "task_id": "1693429440172235501-0160208206-15900-0",
            },
            "priv": {
                "file_name": "3_63_127.0.0.x_25000_20230831_050400_logical.priv",
                "size": 2164,
                "task_id": "1693429440216214985-0160208206-15906-0",
            },
        },
        "spider_slave": {},
        "remote_node": {
            "0": {
                "backup_begin_time": "2023-08-31 05:04:00",
                "backup_end_time": "2023-08-31 05:04:00",
                "backup_time": "2023-08-31 05:04:00",
                "mysql_role": "slave",
                "host": "127.0.0.2",
                "port": 20000,
                "file_list_details": [
                    {
                        "file_name": "3_63_127.0.0.x_20000_20230831_050400_logical.index",
                        "size": 1965,
                        "task_id": "1693429440284831420-0160210690-32194-0",
                    }
                ],
                "index": {
                    "file_name": "3_63_127.0.0.x_20000_20230831_050400_logical.index",
                    "size": 1965,
                    "task_id": "1693429440284831420-0160210690-32194-0",
                },
                "priv": {
                    "file_name": "3_63_127.0.0.x_20000_20230831_050400_logical.priv",
                    "size": 3206,
                    "task_id": "1693429440333168971-0160210690-32200-0",
                },
            },
            "1": {
                "backup_begin_time": "2023-08-31 05:04:00",
                "backup_end_time": "2023-08-31 05:04:00",
                "backup_time": "2023-08-31 05:04:00",
                "mysql_role": "slave",
                "host": "127.0.0.3",
                "port": 20001,
                "file_list_details": [
                    {
                        "file_name": "3_63_127.0.0.x_20001_20230831_050400_logical.index",
                        "size": 1965,
                        "task_id": "1693429440699256245-0160210690-32240-0",
                    }
                ],
                "index": {
                    "file_name": "3_63_127.0.0.x_20001_20230831_050400_logical.index",
                    "size": 1965,
                    "task_id": "1693429440699256245-0160210690-32240-0",
                },
                "priv": {
                    "file_name": "3_63_127.0.0.x_20001_20230831_050400_logical.priv",
                    "size": 3206,
                    "task_id": "1693429440750115729-0160210690-32247-0",
                },
            },
        },
    }
]
