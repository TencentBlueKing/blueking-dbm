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
from backend.ticket.constants import TicketType

BK_USERNAME = "admin"
BK_BIZ_ID = 1
CLUSTER_ID = 1

# mangos 扩容请求单据
MANGODB_ADD_MANGOS_TICKET_DATA = {
    "ticket_type": TicketType.MONGODB_ADD_MONGOS,
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {"cluster_id": CLUSTER_ID, "role": "mongos", "resource_spec": {"mongos": {"spec_id": 3, "count": 1}}}
        ]
    },
}

# mangos 扩容资源池数据
MANGOS_ADD_SOURCE_DATA = {
    "0_mongos": [
        {
            "bk_biz_id": BK_BIZ_ID,
            "ip": "127.0.0.1",
            "bk_cloud_id": 0,
            "bk_host_id": 3,
            "bk_cpu": 2,
            "bk_disk": 147,
            "bk_mem": 3663,
            "storage_device": {"/data": {"size": 50, "disk_id": "disk-01", "disk_type": "HDD", "file_type": "ext4"}},
            "city": "",
            "sub_zone": "",
            "sub_zone_id": "",
            "rack_id": "",
            "device_class": "",
        }
    ]
}

# mango 整机替换请求单据
MANGODB_CUTOFF_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": "MONGODB_CUTOFF",
    "details": {
        "ip_source": "resource_pool",
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "mongos": [{"ip": "1.1.1.3", "spec_id": 3, "bk_cloud_id": 0}],
                "mongodb": [{"ip": "1.1.1.4", "spec_id": 3, "bk_cloud_id": 0}],
                "mongo_config": [{"ip": "1.1.1.5", "spec_id": 3, "bk_cloud_id": 0}],
            }
        ],
    },
}

# mangos 缩容请求单据
MANGODB_REDUCE_MANGOS_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.MONGODB_REDUCE_MONGOS,
    "details": {
        "is_safe": True,
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "role": "mongos",
                "reduce_nodes": [{"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_host_id": 3}],
            }
        ],
    },
}

# mango 整机替换资源申请数据
MANGODB_SOURCE_APPLICATION_DATA = {
    "0_mongodb_1.1.1.4": [
        {
            "bk_biz_id": BK_BIZ_ID,
            "ip": "2.2.2.1",
            "bk_cloud_id": 0,
            "bk_host_id": 3,
            "bk_cpu": 2,
            "bk_disk": 147,
            "bk_mem": 3663,
            "storage_device": {"/data": {"size": 50, "disk_id": "disk-01", "disk_type": "HDD", "file_type": "ext4"}},
            "city": "",
            "sub_zone": "",
            "sub_zone_id": "",
            "rack_id": "",
            "device_class": "",
        }
    ],
    "0_mongos_1.1.1.3": [
        {
            "bk_biz_id": BK_BIZ_ID,
            "ip": "2.2.2.3",
            "bk_cloud_id": 0,
            "bk_host_id": 3,
            "bk_cpu": 2,
            "bk_disk": 147,
            "bk_mem": 3663,
            "storage_device": {"/data": {"size": 50, "disk_id": "disk-01", "disk_type": "HDD", "file_type": "ext4"}},
            "city": "",
            "sub_zone": "",
            "sub_zone_id": "",
            "rack_id": "",
            "device_class": "",
        }
    ],
    "0_mongo_config_1.1.1.5": [
        {
            "bk_biz_id": BK_BIZ_ID,
            "ip": "2.2.2.5",
            "bk_cloud_id": 0,
            "bk_host_id": 3,
            "bk_cpu": 2,
            "bk_disk": 147,
            "bk_mem": 3663,
            "storage_device": {"/data": {"size": 50, "disk_id": "disk-01", "disk_type": "HDD", "file_type": "ext4"}},
            "city": "",
            "sub_zone": "",
            "sub_zone_id": "",
            "rack_id": "",
            "device_class": "",
        }
    ],
}

# 初始化mongodb集群
MANGODB_CLUSTER_DATA = {
    "id": CLUSTER_ID,
    "creator": BK_USERNAME,
    "updater": BK_USERNAME,
    "name": "shard01",
    "alias": "shard01",
    "bk_biz_id": BK_BIZ_ID,
    "cluster_type": ClusterType.MongoShardedCluster,
    "db_module_id": 0,
    "immute_domain": "mongos.shard01.dba.db",
    "major_version": "3.4.20",
    "phase": "online",
    "status": "normal",
    "bk_cloud_id": 0,
    "region": "default",
    "time_zone": "+08:00",
    "disaster_tolerance_level": "NONE",
}

# mangodb集群规格数据
MANGODB_SPEC_DATA = [
    {
        "spec_id": 3,
        "spec_name": "1核_1G_10G",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "spec_cluster_type": ClusterType.MongoShardedCluster,
        "spec_machine_type": "mongos",
        "qps": {"max": 0, "min": 0},
        "enable": 1,
    },
    {
        "spec_id": 1,
        "spec_name": "1核_1G_10G",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "spec_cluster_type": ClusterType.MongoShardedCluster,
        "spec_machine_type": "mongos",
        "qps": {"max": 0, "min": 0},
        "enable": 1,
    },
    {
        "spec_id": 2,
        "spec_name": "2核_1G_10G",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "spec_cluster_type": ClusterType.MongoShardedCluster,
        "spec_machine_type": "mongos",
        "qps": {"max": 0, "min": 0},
        "enable": 1,
    },
]

# mongodb实例数据
MANGODB_PROXYINSTANCE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-14 01:36:51.626234",
        "updater": "",
        "update_at": "2024-03-14 01:36:51.626234",
        "version": "",
        "port": 10000,
        "admin_port": 20000,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7089,
        "machine_id": 3,
        "phase": "online",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.438115",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.438115",
        "version": "",
        "port": 10000,
        "admin_port": 20000,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7087,
        "machine_id": 130,
        "phase": "online",
    },
    {
        "creator": "",
        "create_at": "2024-03-12 04:52:46.603053",
        "updater": "",
        "update_at": "2024-03-12 04:52:46.603053",
        "version": "",
        "port": 10000,
        "admin_port": 20000,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7023,
        "machine_id": 1,
        "phase": "online",
    },
    {
        "creator": "",
        "create_at": "2024-03-12 04:52:46.598053",
        "updater": "",
        "update_at": "2024-03-12 04:52:46.598053",
        "version": "",
        "port": 10000,
        "admin_port": 20000,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7024,
        "machine_id": 2,
        "phase": "online",
    },
]

# mangodb 集群机器信息
MANGODB_MACHINE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "1.1.1.4",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "bk_host_id": 130,
        "bk_os_name": "linux centos",
        "bk_idc_area": "",
        "bk_idc_area_id": 0,
        "bk_sub_zone": "",
        "bk_sub_zone_id": 0,
        "bk_rack": "",
        "bk_rack_id": 0,
        "bk_svr_device_cls_name": "",
        "bk_idc_name": "",
        "bk_idc_id": 0,
        "bk_cloud_id": 0,
        "net_device_id": "",
        "bk_city_id": 0,
        "spec_config": '{"id": 3, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, '
        '"qps": {"max": 0, "min": 0}, "name": "1核_1G_10G", "count": 1, "device_class": [],'
        ' "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 3,
        "bk_agent_id": "",
    },
    {
        "creator": "",
        "create_at": "2024-03-12 04:52:46.559806",
        "updater": "",
        "update_at": "2024-03-12 04:52:46.560347",
        "ip": "1.1.1.5",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "bk_host_id": 2,
        "bk_os_name": "linux centos",
        "bk_idc_area": "",
        "bk_idc_area_id": 0,
        "bk_sub_zone": "",
        "bk_sub_zone_id": 0,
        "bk_rack": "",
        "bk_rack_id": 0,
        "bk_svr_device_cls_name": "",
        "bk_idc_name": "",
        "bk_idc_id": 0,
        "bk_cloud_id": 0,
        "net_device_id": "",
        "bk_city_id": 0,
        "spec_config": '{"id": 2, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, '
        '"qps": {"max": 0, "min": 0}, "name": "2核_1G_10G", "count": 2, "device_class": [],'
        '"storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 2,
        "bk_agent_id": "",
    },
    {
        "creator": "",
        "create_at": "2024-03-12 04:52:46.570057",
        "updater": "",
        "update_at": "2024-03-12 04:52:46.570057",
        "ip": "1.1.1.3",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "bk_host_id": 1,
        "bk_os_name": "linux centos",
        "bk_idc_area": "",
        "bk_idc_area_id": 0,
        "bk_sub_zone": "",
        "bk_sub_zone_id": 0,
        "bk_rack": "",
        "bk_rack_id": 0,
        "bk_svr_device_cls_name": "",
        "bk_idc_name": "",
        "bk_idc_id": 0,
        "bk_cloud_id": 0,
        "net_device_id": "",
        "bk_city_id": 0,
        "spec_config": '{"id": 2, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, '
        '"qps": {"max": 0, "min": 0}, "name": "2核_1G_10G", "count": 2, "device_class": [],'
        ' "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 2,
        "bk_agent_id": "",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-14 01:36:51.614034",
        "updater": "",
        "update_at": "2024-03-14 01:36:51.614034",
        "ip": "1.1.1.7",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "bk_host_id": 3,
        "bk_os_name": "linux centos",
        "bk_idc_area": "",
        "bk_idc_area_id": 0,
        "bk_sub_zone": "",
        "bk_sub_zone_id": 0,
        "bk_rack": "",
        "bk_rack_id": 0,
        "bk_svr_device_cls_name": "",
        "bk_idc_name": "",
        "bk_idc_id": 0,
        "bk_cloud_id": 0,
        "net_device_id": "",
        "bk_city_id": 0,
        "spec_config": '{"id": 3, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, '
        '"qps": {"max": 0, "min": 0}, "name": "1核_1G_10G", "count": 1, "device_class": [],'
        ' "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 3,
        "bk_agent_id": "",
    },
]

APPCACHE_DATA = {"bk_biz_id": BK_BIZ_ID, "db_app_abbr": "dba"}
