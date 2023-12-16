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

RESTORE_RECORD_DATA = {
    "count": 11,
    "limit": 10,
    "offset": 1,
    "data": [
        {
            "ns_filter": {},
            "source_cluster": {
                "id": 1,
                "name": "test-tmp",
                "bk_cloud_id": 0,
                "region": "sz",
                "cluster_type": "MongoReplicaSet",
                "immute_domain": "test-tmp.dba.db",
                "major_version": "1.0.0",
            },
            "target_cluster": {
                "id": 2,
                "name": "test2",
                "bk_cloud_id": 0,
                "region": "sz",
                "cluster_type": "MongoReplicaSet",
                "immute_domain": "test2.dba.db",
                "major_version": "1.0.0",
            },
            "target_nodes": ["127.0.0.1", "127.0.0.2"],
            "ticket_id": 1,
            "rollback_time": "2022-11-11T12:55:11+08:00",
            "backupinfo": {},
        }
    ],
}

CLUSTER_BACKUP_LOGS_DATA = {
    "19": [
        {
            "bk_cloud_id": 0,
            "bk_biz_id": 3,
            "app": "",
            "app_name": "",
            "cluster_domain": "m1.test1-xxx-s1.dba.db",
            "cluster_id": "19",
            "cluster_name": "test-test1-s1",
            "cluster_type": "MongoReplicaSet",
            "role_type": "mongo_backup",
            "meta_role": "mongo_backup",
            "server_ip": "127.0.0.1",
            "server_port": 27001,
            "set_name": "test-test1-s1",
            "report_type": "",
            "start_time": "2024-01-31T09:18:28+08:00",
            "end_time": "2024-01-31T09:18:28+08:00",
            "file_path": "/data/dbbak/mongodump-xxxx.tar",
            "file_name": "mongodump-xxxx.tar",
            "file_size": 10240,
            "bs_taskid": "xxxx",
            "bs_tag": "",
            "bs_status": "",
            "src": "bill",
            "pitr_fullname": "",
            "pitr_date": "",
            "pitr_file_type": "",
            "pitr_binlog_index": 0,
            "pitr_last_pos": 0,
            "releate_bill_id": "2024013101",
            "total_file_num": 1,
            "my_file_num": 1,
            "releate_bill_info": "todo",
        }
    ]
}
