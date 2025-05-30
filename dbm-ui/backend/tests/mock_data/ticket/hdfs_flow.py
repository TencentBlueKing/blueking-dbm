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
from backend.tests.mock_data import constant

BK_USERNAME = "admin"
BK_BIZ_ID = constant.BK_BIZ_ID
CLUSTER_ID = 92


HDFS_APPLY_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "default",
        "cluster_alias": "",
        "cluster_name": "testhdfs",
        "db_app_abbr": "1",
        "db_version": "2.6.0-cdh5.4.11-tendataV0.2",
        "disaster_tolerance_level": "MAX_EACH_ZONE_EQUAL",
        "http_port": 50070,
        "ip_source": "resource_pool",
        "resource_spec": {
            "datanode": {
                "count": 2,
                "spec_id": 394,
                "cpu": {"max": 256, "min": 1},
                "mem": {"max": 256, "min": 1},
                "qps": {},
                "spec_name": "1核_1G_10G",
                "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data", "_X_ROW_KEY": "row_93"}],
                "affinity": "MAX_EACH_ZONE_EQUAL",
                "location_spec": {"city": "default"},
            },
            "namenode": {
                "count": 2,
                "spec_id": 395,
                "cpu": {"max": 256, "min": 1},
                "mem": {"max": 256, "min": 1},
                "qps": {},
                "spec_name": "1核_1G_10G",
                "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data", "_X_ROW_KEY": "row_53"}],
                "affinity": "MAX_EACH_ZONE_EQUAL",
                "location_spec": {"city": "default"},
            },
            "zookeeper": {
                "count": 3,
                "spec_id": 395,
                "cpu": {"max": 256, "min": 1},
                "mem": {"max": 256, "min": 1},
                "qps": {},
                "spec_name": "1核_1G_10G",
                "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data", "_X_ROW_KEY": "row_69"}],
                "affinity": "MAX_EACH_ZONE_EQUAL",
                "location_spec": {"city": "default"},
            },
        },
        "rpc_port": 9000,
        "city_name": "无限制",
    },
    "remark": "",
    "ticket_type": "HDFS_APPLY",
}

HDFS_SCALE_UP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "cluster_id": CLUSTER_ID,
        "ext_info": {"datanode": {"expansion_disk": 10, "total_disk": None, "total_hosts": 2}},
        "ip_source": "resource_pool",
        "resource_spec": {"datanode": {"count": 1, "spec_id": 394}},
    },
    "ticket_type": "HDFS_SCALE_UP",
}

HDFS_SPEC_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "spec_id": 394,
        "spec_name": "1核_1G_10G",
        "spec_cluster_type": "hdfs",
        "spec_machine_type": "hdfs_datanode",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "device_class": [],
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "desc": "12",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-15 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-15 11:14:48.433116",
        "spec_id": 395,
        "spec_name": "1核_1G_10G",
        "spec_cluster_type": "hdfs",
        "spec_machine_type": "hdfs_master",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "device_class": [],
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "desc": "212112",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
]

HDFS_CLUSTER_DATA = {
    "id": CLUSTER_ID,
    "creator": BK_USERNAME,
    "updater": BK_USERNAME,
    "name": "randpass",
    "alias": "randpass",
    "bk_biz_id": BK_BIZ_ID,
    "cluster_type": ClusterType.Hdfs,
    "db_module_id": 0,
    "immute_domain": "hdfs.randpass.dba.db",
    "major_version": "2.6.0-cdh5.4.11-tendataV0.2",
    "phase": "online",
    "status": "normal",
    "bk_cloud_id": 0,
    "region": "",
    "time_zone": "+08:00",
    "disaster_tolerance_level": "NONE",
}
