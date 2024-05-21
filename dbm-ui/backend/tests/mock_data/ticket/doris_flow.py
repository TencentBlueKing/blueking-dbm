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

from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.machine_type import MachineType
from backend.ticket.constants import TicketType

BK_BIZ_ID = 1
DB_MODULE_ID = 1
CLUSTER_ID = 1
BK_USERNAME = "admin"

# doris 上架请求单据
DORIS_APPLY_TICKET_DATA = {
    "ticket_type": TicketType.DORIS_APPLY,
    "bk_biz_id": BK_BIZ_ID,
    "remark": "xxx",
    "details": {
        "ip_source": "resource_pool",
        "query_port": 5001,
        "http_port": 5002,
        "db_version": "2.0.4",
        "cluster_name": "doristest1",
        "cluster_alias": "test1",
        "city_code": "深圳",
        "bk_cloud_id": 0,
        "db_app_abbr": "dba-test",
        "resource_spec": {"follower": {"spec_id": 1, "count": 3}, "observer": {}, "hot": {"spec_id": 3, "count": 2}},
    },
}


# DORIS 资源申请
DORIS_SOURCE_APPLICATION_DATA = [
    {
        "hot": [
            {
                "bk_biz_id": BK_BIZ_ID,
                "ip": "127.0.0.1",
                "bk_cloud_id": 0,
                "bk_host_id": 1,
                "bk_cpu": 4,
                "bk_disk": 147,
                "bk_mem": 15741,
                "storage_device": {"/data": {"size": 30, "disk_id": "", "disk_type": "ALL", "file_type": ""}},
                "city": "",
                "sub_zone": "",
                "sub_zone_id": "",
                "rack_id": "",
                "device_class": "",
            },
            {
                "bk_biz_id": BK_BIZ_ID,
                "ip": "127.0.0.2",
                "bk_cloud_id": 0,
                "bk_host_id": 2,
                "bk_cpu": 4,
                "bk_disk": 147,
                "bk_mem": 15741,
                "storage_device": {"/data": {"size": 30, "disk_id": "", "disk_type": "ALL", "file_type": ""}},
                "city": "",
                "sub_zone": "",
                "sub_zone_id": "",
                "rack_id": "",
                "device_class": "",
            },
        ],
        "follower": [
            {
                "bk_biz_id": BK_BIZ_ID,
                "ip": "127.0.0.3",
                "bk_cloud_id": 0,
                "bk_host_id": 3,
                "bk_cpu": 8,
                "bk_disk": 98,
                "bk_mem": 31844,
                "storage_device": {"/data": {"size": 30, "disk_id": "", "disk_type": "ALL", "file_type": ""}},
                "city": "",
                "sub_zone": "",
                "sub_zone_id": "",
                "rack_id": "",
                "device_class": "",
            },
            {
                "bk_biz_id": BK_BIZ_ID,
                "ip": "127.0.0.4",
                "bk_cloud_id": 0,
                "bk_host_id": 4,
                "bk_cpu": 8,
                "bk_disk": 98,
                "bk_mem": 31892,
                "storage_device": {"/data": {"size": 30, "disk_id": "", "disk_type": "ALL", "file_type": ""}},
                "city": "",
                "sub_zone": "",
                "sub_zone_id": "",
                "rack_id": "",
                "device_class": "",
            },
            {
                "bk_biz_id": BK_BIZ_ID,
                "ip": "127.0.0.5",
                "bk_cloud_id": 0,
                "bk_host_id": 5,
                "bk_cpu": 4,
                "bk_disk": 147,
                "bk_mem": 15741,
                "storage_device": {"/data": {"size": 30, "disk_id": "", "disk_type": "ALL", "file_type": ""}},
                "city": "",
                "sub_zone": "",
                "sub_zone_id": "",
                "rack_id": "",
                "device_class": "",
            },
        ],
    }
]

# DORIS 规格初始化
DORIS_SPEC_DATA = [
    {
        "spec_id": 1,
        "spec_name": "2核_2G_30G",
        "cpu": {"max": 256, "min": 2},
        "mem": {"max": 256, "min": 2},
        "storage_spec": [{"size": 30, "type": "ALL", "mount_point": "/data"}],
        "spec_cluster_type": ClusterType.Doris.value,
        "spec_machine_type": MachineType.DORIS_FOLLOWER.value,
        "device_class": [-1],
        "qps": {"max": 0, "min": 0},
        "enable": 1,
    },
    {
        "spec_id": 2,
        "spec_name": "2核_2G_30G",
        "cpu": {"max": 256, "min": 2},
        "mem": {"max": 256, "min": 2},
        "storage_spec": [{"size": 30, "type": "ALL", "mount_point": "/data"}],
        "spec_cluster_type": ClusterType.Doris.value,
        "spec_machine_type": MachineType.DORIS_OBSERVER.value,
        "device_class": [-1],
        "qps": {"max": 0, "min": 0},
        "enable": 1,
    },
    {
        "spec_id": 3,
        "spec_name": "2核_2G_30G",
        "cpu": {"max": 256, "min": 2},
        "mem": {"max": 256, "min": 2},
        "storage_spec": [{"size": 30, "type": "ALL", "mount_point": "/data"}],
        "spec_cluster_type": ClusterType.Doris.value,
        "spec_machine_type": MachineType.DORIS_BACKEND.value,
        "device_class": [-1],
        "qps": {"max": 0, "min": 0},
        "enable": 1,
    },
]
