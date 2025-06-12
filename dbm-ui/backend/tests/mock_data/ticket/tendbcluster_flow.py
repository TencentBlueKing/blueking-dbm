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
from backend.tests.mock_data import constant

BK_USERNAME = "admin"
BK_BIZ_ID = constant.BK_BIZ_ID
CLUSTER_ID = 177


TENDBCLUSTER_FULL_BACKUP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "backup_type": "logical",
        "file_tag": "DBFILE1M",
        "infos": [{"cluster_id": CLUSTER_ID, "backup_local": "master"}],
    },
    "remark": "",
    "ticket_type": "TENDBCLUSTER_FULL_BACKUP",
}

TENDBCLUSTER_DB_TABLE_BACKUP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "backup_local": "remote",
                "db_patterns": ["*"],
                "table_patterns": ["*"],
                "ignore_dbs": [],
                "ignore_tables": [],
            }
        ]
    },
    "remark": "",
    "ticket_type": "TENDBCLUSTER_DB_TABLE_BACKUP",
}

TENDBCLUSTER_CHECKSUM_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "data_repair": {"is_repair": True, "mode": "manual"},
        "is_sync_non_innodb": True,
        "remark": "",
        "runtime_hour": 24,
        "timing": "2026-06-20T23:59:59+08:00",
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "checksum_scope": "all",
                "backup_infos": [
                    {
                        "slave": "",
                        "master": "",
                        "db_patterns": ["*"],
                        "table_patterns": ["*"],
                        "ignore_dbs": [],
                        "ignore_tables": [],
                    }
                ],
            }
        ],
    },
    "remark": "",
    "ticket_type": "TENDBCLUSTER_CHECKSUM",
}

TENDBCLUSTER_APPLY_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "default",
        "cluster_alias": "",
        "cluster_name": "7899",
        "cluster_shard_num": 1,
        "db_app_abbr": "1",
        "db_module_id": 0,
        "disaster_tolerance_level": "NONE",
        "remote_shard_num": 1,
        "resource_spec": {
            "backend_group": {
                "affinity": "NONE",
                "capacity": "",
                "count": 1,
                "future_capacity": "",
                "location_spec": {"city": "default"},
                "spec_id": 234,
                "spec_info": {
                    "cluster_capacity": 5,
                    "cluster_shard_num": 1,
                    "machine_pair": 1,
                    "qps": {"max": 0, "min": 0},
                    "spec_name": "1核_1G_10G",
                },
            },
            "spider": {
                "count": 2,
                "spec_id": 235,
                "cpu": {"max": 256, "min": 1},
                "mem": {"max": 2048, "min": 1},
                "qps": {"max": 0, "min": 0},
                "spec_name": "1核_1G",
                "storage_spec": [],
                "affinity": "NONE",
                "location_spec": {"city": "default"},
            },
        },
        "spider_port": 20000,
        "sub_zone_ids": [],
        "city_name": "无限制",
    },
    "remark": "",
    "ticket_type": "TENDBCLUSTER_APPLY",
}

TENDBCLUSTER_ROLLBACK_CLUSTER_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "backup_source": "remote",
                "cluster_id": CLUSTER_ID,
                "databases": ["*"],
                "databases_ignore": [],
                "rollback_time": "2025-06-18T23:59:59+08:00",
                "rollback_type": "REMOTE_AND_TIME",
                "tables": ["*"],
                "tables_ignore": [],
                "target_cluster_id": CLUSTER_ID,
            }
        ],
        "rollback_cluster_type": "BUILD_INTO_METACLUSTER",
    },
    "remark": "",
    "ticket_type": "TENDBCLUSTER_ROLLBACK_CLUSTER",
}

TENDBCLUSTER_SPIDER_SLAVE_APPLY_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "resource_spec": {
                    "spider_slave_ip_list": {
                        "creator": "",
                        "updater": "",
                        "spec_id": 234,
                        "spec_name": "16核_32G_1000G",
                        "spec_cluster_type": "tendbcluster",
                        "spec_machine_type": "backend",
                        "cpu": {"max": 256, "min": 1},
                        "mem": {"max": 256, "min": 1},
                        "device_class": [],
                        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
                        "desc": "",
                        "enable": True,
                        "instance_num": 0,
                        "qps": {},
                        "count": 1,
                        "id": 410,
                        "name": "无限制",
                    }
                },
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "TENDBCLUSTER_SPIDER_SLAVE_APPLY",
}

TENDBCLUSTER_SPIDER_SWITCH_NODES_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "is_safe": True,
        "infos": [
            {
                "row_key": "109551_1750318406460_432182",
                "cluster_id": CLUSTER_ID,
                "resource_spec": {"spider_master_5.5.5.5": {"count": 1, "labels": [], "spec_id": 234}},
                "spider_old_ip_list": [{"bk_cloud_id": 0, "bk_host_id": 123, "ip": "5.5.5.5", "port": 20001}],
                "switch_spider_role": "spider_master",
            }
        ],
        "ip_source": "resource_pool",
        "old_nodes": {"spider_master": [{"bk_cloud_id": 0, "bk_host_id": 123, "ip": "5.5.5.5"}], "spider_slave": []},
    },
    "remark": "",
    "ticket_type": "TENDBCLUSTER_SPIDER_SWITCH_NODES",
}

TENDBCLUSTER_CLUSTER_DATA = {
    "id": CLUSTER_ID,
    "creator": BK_USERNAME,
    "updater": BK_USERNAME,
    "name": "dev-ygctest-tendbcluster",
    "alias": "",
    "bk_biz_id": BK_BIZ_ID,
    "cluster_type": ClusterType.TenDBCluster,
    "db_module_id": 42,
    "immute_domain": "spider.dev-ygctest-tendbcluster.dba.db",
    "major_version": "MySQL-5.7",
    "phase": "online",
    "status": "normal",
    "bk_cloud_id": 0,
    "region": "",
    "time_zone": "+08:00",
    "disaster_tolerance_level": "NONE",
}

TENDBCLUSTER_STORAGE_INSTANCE = [
    {
        "id": 1138,
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "version": "5.7.20",
        "port": 20001,
        "machine_id": 125,
        "db_module_id": 2,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": "remote",
        "instance_role": "remote_master",
        "instance_inner_role": "master",
        "cluster_type": "tendbcluster",
        "status": "running",
        "phase": "online",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7878,
        "is_stand_by": "1",
    }
]

TENDBCLUSTER_MACHINE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "5.5.5.5",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": MachineType.SPIDER.value,
        "cluster_type": ClusterType.TenDBCluster,
        "bk_host_id": 123,
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
        "spec_config": '{"id": 234, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, '
        '"qps": {"max": 0, "min": 0}, "name": "1核_1G_10G", "count": 1, "device_class": [],'
        ' "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 234,
        "bk_agent_id": "",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "5.5.5.3",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": MachineType.SPIDER.value,
        "cluster_type": ClusterType.TenDBCluster,
        "bk_host_id": 124,
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
        "spec_config": '{"id": 235, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, '
        '"qps": {"max": 0, "min": 0}, "name": "1核_1G_10G", "count": 1, "device_class": [],'
        ' "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 235,
        "bk_agent_id": "",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "5.5.5.4",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "storage",
        "machine_type": MachineType.REMOTE.value,
        "cluster_type": ClusterType.TenDBCluster,
        "bk_host_id": 125,
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
        "spec_config": '{"id": 236, "cpu": {"max": 256, "min": 1}, "mem": {"max": 256, "min": 1}, '
        '"qps": {"max": 0, "min": 0}, "name": "1核_1G_10G", "count": 1, "device_class": [],'
        ' "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}]}',
        "spec_id": 236,
        "bk_agent_id": "",
    },
]

TENDBCLUSTER_PROXYINSTANCE_DATA = [
    {
        "id": 274,
        "creator": "admin",
        "create_at": "2025-02-10 12:28:23.315607",
        "updater": "",
        "update_at": "2025-02-10 12:28:23.315633",
        "version": "3.7.8",
        "port": 20001,
        "admin_port": 26000,
        "db_module_id": 42,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "proxy",
        "machine_type": "spider",
        "cluster_type": "tendbcluster",
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 11553,
        "machine_id": 123,
        "phase": "online",
    },
    {
        "id": 275,
        "creator": "admin",
        "create_at": "2025-02-10 12:28:23.315607",
        "updater": "",
        "update_at": "2025-02-10 12:28:23.315633",
        "version": "3.7.8",
        "port": 20001,
        "admin_port": 26000,
        "db_module_id": 42,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "proxy",
        "machine_type": "spider",
        "cluster_type": "tendbcluster",
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 11553,
        "machine_id": 124,
        "phase": "online",
    },
]

TENDBCLUSTER_SPEC_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "spec_id": 234,
        "spec_name": "无限制",
        "spec_cluster_type": "tendbcluster",
        "spec_machine_type": "backend",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "device_class": [],
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "desc": "111",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-15 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-15 11:14:48.433116",
        "spec_id": 235,
        "spec_name": "2c_4g_50g",
        "spec_cluster_type": "tendbcluster",
        "spec_machine_type": "backend",
        "cpu": {"max": 2, "min": 2},
        "mem": {"max": 4, "min": 3},
        "device_class": ["S5.MEDIUM4", "SA2.MEDIUM4", "S5t.MEDIUM4"],
        "storage_spec": [{"size": 50, "type": "ALL", "mount_point": "/data"}],
        "desc": "",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "spec_id": 236,
        "spec_name": "无限制",
        "spec_cluster_type": "tendbcluster",
        "spec_machine_type": "backend",
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "device_class": [],
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
        "desc": "111",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
]

TENDBCLUSTER_SPIDEREXT_DATA = [
    {"spider_role": "spider_master", "instance_id": 274},
    {"spider_role": "spider_master", "instance_id": 275},
]
