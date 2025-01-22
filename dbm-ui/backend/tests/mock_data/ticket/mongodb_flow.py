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
from backend.ticket.constants import TicketType

BK_USERNAME = "admin"
BK_BIZ_ID = constant.BK_BIZ_ID
CLUSTER_ID = 101


# Mongo执行脚本
MONGODB_EXEC_SCRIPT_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "cluster_ids": [CLUSTER_ID],
        "scripts": [
            {
                "name": "",
                "content": "var mongo = db;\r\n"
                'var thisdb = mongo.getSisterDB("test_db");\r\n'
                'thisdb.test_tb.insertOne({ name: "A", age: 1 });',
            }
        ],
        "mode": "manual",
    },
    "ticket_type": TicketType.MONGODB_EXEC_SCRIPT_APPLY,
}

# Mongo清档单据
MONGODB_REMOVE_NS_TICKET_DATA = {
    "remark": "username",
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.MONGODB_REMOVE_NS,
    "details": {
        "is_safe": True,
        "infos": [
            {
                "drop_index": True,
                "drop_type": "drop_collection",
                "cluster_ids": [CLUSTER_ID],
                "cluster_type": ClusterType.MongoReplicaSet,
                "ns_filter": {
                    "db_patterns": ["test_db"],
                    "ignore_dbs": [],
                    "table_patterns": ["test_tb"],
                    "ignore_tables": [],
                },
            }
        ],
    },
}


# mongos 扩容请求单据
MONGODB_ADD_MONGOS_TICKET_DATA = {
    "ticket_type": TicketType.MONGODB_ADD_MONGOS,
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {"cluster_id": CLUSTER_ID, "role": "mongos", "resource_spec": {"mongos": {"spec_id": 3, "count": 1}}}
        ]
    },
}

# mongos 缩容请求单据
MONGODB_REDUCE_MONGOS_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.MONGODB_REDUCE_MONGOS,
    "details": {
        "is_safe": True,
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "role": "mongos",
                "reduce_nodes": [{"ip": "2.1.1.4", "bk_cloud_id": 0, "bk_host_id": 1004}],
            }
        ],
    },
}

# mangodb 集群下架请求单据
MONGODB_DESTROY_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.MONGODB_DESTROY,
    "details": {"cluster_ids": [CLUSTER_ID]},
}

# mango 整机替换请求单据
MONGODB_CUTOFF_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": "MONGODB_CUTOFF",
    "details": {
        "ip_source": "resource_pool",
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "mongos": [{"ip": "2.1.1.3", "spec_id": 3, "bk_cloud_id": 0}],
                "mongodb": [{"ip": "2.1.1.1", "spec_id": 3, "bk_cloud_id": 0}],
                "mongo_config": [{"ip": "2.1.1.2", "spec_id": 3, "bk_cloud_id": 0}],
            }
        ],
    },
}

# 初始化mongodb集群
MONGODB_CLUSTER_DATA = {
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

# mongodb实例数据
MONGODB_PROXYINSTANCE_DATA = [
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
        "machine_id": 1004,
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
        "machine_id": 1001,
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
        "machine_id": 1002,
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
        "machine_id": 1003,
        "phase": "online",
    },
]

# mangodb 集群机器信息
MONGODB_MACHINE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "2.1.1.1",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "bk_host_id": 1001,
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
        "ip": "2.1.1.2",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "bk_host_id": 1002,
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
        "ip": "2.1.1.3",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "bk_host_id": 1003,
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
        "ip": "2.1.1.4",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": "mongos",
        "cluster_type": ClusterType.MongoShardedCluster,
        "bk_host_id": 1004,
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
