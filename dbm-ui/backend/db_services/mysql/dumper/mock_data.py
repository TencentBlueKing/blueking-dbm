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

DUMPER_INSTANCE_LIST_DATA = [
    {
        "id": 1,
        "creator": "xxx",
        "create_at": "2022-11-11 20:00:00",
        "updater": "xxx",
        "update_at": "2022-11-11 20:00:00",
        "bk_biz_id": 3,
        "cluster_id": 64,
        "bk_cloud_id": 0,
        "ip": "127.0.0.1",
        "proc_type": "tbinlogdumper",
        "version": "1.0",
        "listen_port": 10000,
        "need_transfer": True,
        "source_cluster": {
            "id": 64,
            "name": "fortest",
            "cluster_type": "tendbha",
            "immute_domain": "tendbha57db.xxx.dba.db",
            "major_version": "MySQL-5.7",
            "bk_cloud_id": 0,
            "region": " ",
        },
        "dumper_config": {
            "id": 1,
            "creator": "admin",
            "updater": "admin",
            "bk_biz_id": 3,
            "name": "dumper-1",
            "receiver_type": "redis",
            "receiver": "redis.com:123",
            "subscribe": {"db_name": "db1", "table_names": ["table1"]},
        },
        "dumper_id": 1,
        "area_name": 1,
    }
]
