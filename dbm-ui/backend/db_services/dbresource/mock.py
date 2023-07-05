# -*- coding:utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

SPEC_DATA = {
    "spec_id": 8,
    "creator": "admin",
    "create_at": "2023-04-24 17:36:45",
    "updater": "admin",
    "update_at": "2023-04-24 17:36:45",
    "spec_name": "test5",
    "spec_cluster_type": "kafka",
    "spec_machine_type": "zookeeper",
    "cpu": {"max": 100, "min": 1},
    "mem": {"max": 100, "min": 1},
    "device_class": ["VM1", "VM2"],
    "storage_spec": {"size": 500, "type": "ssd", "mount_point": "/data"},
    "desc": ".....",
}

RESOURCE_LIST_DATA = [
    {
        "bk_cloud_id": 0,
        "bk_biz_id": 2005000100,
        "bk_host_id": 2000012345,
        "ip": "127.0.0.1",
        "asset_id": "",
        "device_class": "",
        "svr_type_name": "",
        "storage_device": {
            "/data": {"size": 1000, "disk_id": 1, "disk_type": "SSD", "file_type": "dev"},
            "/data1": {"size": 2000, "disk_id": 2, "disk_type": "SSD", "file_type": "dev"},
        },
        "raid": "",
        "city_id": "",
        "city": "",
        "sub_zone": "",
        "sub_zone_id": "",
        "rack_id": "",
        "net_device_id": "",
        "label": "null",
        "status": "Unused",
        "consume_time": "1970-01-01T08:00:01+08:00",
        "update_time": "2023-05-15T11:10:05+08:00",
        "create_time": "2023-05-15T11:10:05+08:00",
        "bk_cloud_name": "default area",
        "agent_status": True,
        "bk_mem": 15,
        "bk_cpu": 8,
        "bk_disk": 0,
        "resource_types": ["influxdb"],
        "for_bizs": [{"bk_biz_id": 2005000100, "bk_biz_name": "xxxx"}],
    },
]

RECOMMEND_SPEC_DATA = [
    {
        "spec_id": 1,
        "creator": "admin",
        "create_at": "2023-06-26 16:30:22",
        "updater": "admin",
        "update_at": "2023-06-26 16:30:22",
        "spec_name": "mysql",
        "spec_cluster_type": "tendbsingle",
        "spec_machine_type": "backend",
        "cpu": {"max": 10000, "min": 1},
        "mem": {"max": 10000, "min": 1},
        "device_class": [],
        "storage_spec": [{"type": "", "max_size": 100000000, "min_size": 1, "mount_point": ""}],
        "desc": "mysql",
        "instance_num": 1,
    }
]
