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
CLUSTER_ID = 29

# kafka 集群部署
KAFKA_APPLY_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "default",
        "cluster_alias": "",
        "cluster_name": "testkafka",
        "db_app_abbr": "1",
        "db_version": "2.4.0",
        "disaster_tolerance_level": "MAX_EACH_ZONE_EQUAL",
        "ip_source": "resource_pool",
        "no_security": 0,
        "partition_num": 1,
        "port": 9092,
        "replication_num": 2,
        "resource_spec": {
            "broker": {
                "count": 2,
                "spec_id": 240,
                "cpu": {"max": 256, "min": 1},
                "mem": {"max": 256, "min": 1},
                "qps": {},
                "spec_name": "1核_1G_10G",
                "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data", "_X_ROW_KEY": "row_387"}],
                "affinity": "MAX_EACH_ZONE_EQUAL",
                "location_spec": {"city": "default"},
            },
            "zookeeper": {
                "count": 3,
                "spec_id": 189,
                "cpu": {"max": 2, "min": 2},
                "mem": {"max": 4, "min": 4},
                "qps": {},
                "spec_name": "2核_4G_100G",
                "storage_spec": [{"size": 100, "type": "SSD", "mount_point": "/data", "_X_ROW_KEY": "row_371"}],
                "affinity": "MAX_EACH_ZONE_EQUAL",
                "location_spec": {"city": "default"},
            },
        },
        "retention_bytes": -1,
        "retention_hours": 4,
        "city_name": "无限制",
    },
    "remark": "",
    "ticket_type": "KAFKA_APPLY",
}

# kafka 扩容
KAFKA_SCALE_UP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "cluster_id": CLUSTER_ID,
        "ext_info": {"broker": {"expansion_disk": 10, "total_disk": None, "total_hosts": 1}},
        "ip_source": "resource_pool",
        "resource_spec": {"broker": {"count": 1, "spec_id": 240}},
    },
    "ticket_type": "KAFKA_SCALE_UP",
}

# kafka 禁用
KAFKA_DISABLE_DATA = {"bk_biz_id": BK_BIZ_ID, "details": {"cluster_id": CLUSTER_ID}, "ticket_type": "KAFKA_DISABLE"}

# 初始化redis集群
KAFKA_CLUSTER_DATA = {
    "id": CLUSTER_ID,
    "creator": BK_USERNAME,
    "updater": BK_USERNAME,
    "name": "testredis",
    "alias": "",
    "bk_biz_id": BK_BIZ_ID,
    "cluster_type": ClusterType.Kafka,
    "db_module_id": 0,
    "immute_domain": "kafka.testredis.dba.db",
    "major_version": "2.4.0",
    "phase": "online",
    "status": "normal",
    "bk_cloud_id": 0,
    "region": "",
    "time_zone": "+08:00",
    "disaster_tolerance_level": "NONE",
}

KAFKA_SPEC_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "spec_id": 189,
        "spec_name": "2核_4G_100G",
        "spec_cluster_type": "kafka",
        "spec_machine_type": "zookeeper",
        "cpu": {"max": 2, "min": 2},
        "mem": {"max": 4, "min": 4},
        "device_class": [],
        "storage_spec": [{"size": 100, "type": "SSD", "mount_point": "/data"}],
        "desc": "zookeeper规格",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-15 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-15 11:14:48.433116",
        "spec_id": 240,
        "spec_name": "1核_1G_10G",
        "spec_cluster_type": "kafka",
        "spec_machine_type": "broker",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "device_class": [],
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "desc": "",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
]
