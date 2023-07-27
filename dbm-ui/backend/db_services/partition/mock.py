"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

PARTITION_LIST_DATA = {
    "count": 16,
    "results": [
        {
            "id": 1,
            "bk_biz_id": 3,
            "immute_domain": "spider.spidertest.abc.db",
            "port": 0,
            "bk_cloud_id": 0,
            "cluster_id": 28,
            "dblike": "kiodb",
            "tblike": "kiodb",
            "partition_columns": "b",
            "partition_column_type": "datetime",
            "reserved_partition": 300,
            "extra_partition": 15,
            "partition_time_interval": 1,
            "partition_type": 0,
            "expire_time": 300,
            "phase": "offline",
            "creator": "admin",
            "updator": "admin",
            "create_time": "2023-07-24T20:32:54+08:00",
            "update_time": "2023-07-24T20:32:54+08:00",
            "execute_time": "0001-01-01T00:00:00Z",
            "ticket_id": 0,
            "status": "",
            "ticket_status": "",
            "check_info": "",
        }
    ],
}

PARTITION_DRY_RUN_DATA = {
    "41": [
        {
            "ip": "127.0.0.1",
            "port": 20000,
            "shard_name": "SPT0",
            "execute_objects": [
                {
                    "config_id": 41,
                    "dblike": "test%_0",
                    "tblike": "test",
                    "init_partition": [
                        {"sql": "xxxx", "need_size": 98304},
                        {"sql": "xxxx", "need_size": 98304},
                    ],
                    "add_partition": [],
                    "drop_partition": [],
                }
            ],
        },
        {
            "ip": "127.0.0.2",
            "port": 20001,
            "shard_name": "SPT1",
            "execute_objects": [
                {
                    "config_id": 41,
                    "dblike": "test%_1",
                    "tblike": "test2",
                    "init_partition": [
                        {"sql": "xxxx", "need_size": 98304},
                        {"sql": "xxxx", "need_size": 98304},
                    ],
                    "add_partition": [],
                    "drop_partition": [],
                }
            ],
        },
    ],
    "100": "分区配置不存在",
    "1001": "分区配置不存在",
    "10002": "分区配置不存在",
}

PARTITION_LOG_DATA = {
    "count": 100,
    "results": [
        {
            "id": 2,
            "ticket_id": 0,
            "ticket_status": "",
            "execute_time": "2023-05-06T17:58:16+08:00",
            "check_info": "",
            "status": "",
        },
        {
            "id": 2,
            "ticket_id": 0,
            "ticket_status": "",
            "execute_time": "2023-05-06T15:48:00+08:00",
            "check_info": "partition error. create ticket fail: json unmarshal failed, err: invalid character '\u003c'",
            "status": "",
        },
        {
            "id": 2,
            "ticket_id": 0,
            "ticket_status": "",
            "execute_time": "2023-04-14T11:04:34+08:00",
            "check_info": "err info",
            "status": "",
        },
    ],
}

PARTITION_FIELD_VERIFY_DATA = {
    "result": False,
    "code": 8710002500,
    "data": None,
    "message": "【kio123】【kio1】分区字段title不满足属于主键部分或唯一键交集的要求（8710002500）",
    "errors": None,
}
