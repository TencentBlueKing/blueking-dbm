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

CLUSTER_ID = 130
BK_USERNAME = "admin"
BK_BIZ_ID = constant.BK_BIZ_ID


# redis 集群部署
REDIS_CLUSTER_APPLY_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "bk_cloud_id": 0,
        "cap_key": "",
        "city_code": "default",
        "cluster_alias": "",
        "cluster_name": "redis-test",
        "cluster_type": "PredixyRedisCluster",
        "db_app_abbr": "1",
        "db_version": "Redis-5",
        "disaster_tolerance_level": "CROSS_RACK",
        "ip_source": "resource_pool",
        "proxy_port": 55556,
        "proxy_pwd": "UIVCVSo;xxe-m;oyK#KK7L;a%3wW#b=j",
        "resource_spec": {
            "backend_group": {
                "affinity": "CROSS_RACK",
                "count": 3,
                "location_spec": {"city": "default"},
                "spec_id": 333,
                "spec_info": {"cluster_capacity": 3, "cluster_shard_num": 3, "machine_pair": 3, "spec_name": "无限制"},
            },
            "proxy": {
                "count": 2,
                "spec_id": 338,
                "cpu": {"max": 2, "min": 2},
                "mem": {"max": 4, "min": 3},
                "qps": {},
                "spec_name": "2c_4g_50g",
                "storage_spec": [{"size": 50, "type": "ALL", "mount_point": "/data", "_X_ROW_KEY": "row_107"}],
                "affinity": "CROSS_RACK",
                "location_spec": {"city": "default"},
                "spec_cluster_type": "PredixyRedisCluster",
                "spec_machine_type": "TwemproxyRedisInstance",
            },
        },
        "sub_zone_ids": [],
        "city_name": "无限制",
        "cluster_shard_num": 3,
    },
    "remark": "",
    "ticket_type": "REDIS_CLUSTER_APPLY",
}

# redis 主从节点部署
REDIS_INS_APPLY_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "default",
        "cluster_type": "RedisInstance",
        "db_app_abbr": "1",
        "db_version": "Redis-5",
        "disaster_tolerance_level": "CROSS_RACK",
        "infos": [{"cluster_name": "testttredis", "databases": 2}],
        "ip_source": "resource_pool",
        "port": 30000,
        "redis_pwd": "vMF@is8s#RBl4EnF5jTaHALjWKWBqAhr",
        "resource_spec": {
            "backend_group": {
                "count": 1,
                "spec_id": 335,
                "cpu": {"max": 2, "min": 2},
                "mem": {"max": 4, "min": 3},
                "qps": {},
                "spec_name": "2c_4g_50gb",
                "storage_spec": [{"size": 50, "type": "ALL", "mount_point": "/data"}],
                "affinity": "CROSS_RACK",
                "location_spec": {"city": "default"},
            }
        },
        "sub_zone_ids": [],
        "append_apply": False,
    },
    "remark": "",
    "ticket_type": "REDIS_INS_APPLY",
}

# redis 数据复制

REDIS_CLUSTER_DATA_COPY_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "data_check_repair_setting": {
            "execution_frequency": "once_after_replication",
            "type": "data_check_and_repair",
        },
        "dts_copy_type": "one_app_diff_cluster",
        "infos": [{"dst_cluster": CLUSTER_ID, "key_black_regex": "", "key_white_regex": "*", "src_cluster": 131}],
        "sync_disconnect_setting": {"reminder_frequency": "once_daily", "type": "keep_sync_with_reminder"},
        "write_mode": "delete_and_write_to_redis",
    },
    "remark": "",
    "ticket_type": "REDIS_CLUSTER_DATA_COPY",
    "ignore_duplication": True,
}

# redis 销毁构造实例
REDIS_STRUCTURE_TASK_DELETE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "bk_cloud_id": 0,
                "cluster_id": CLUSTER_ID,
                "display_info": {"temp_cluster_proxy": "2.2.3.3:50000"},
                "related_rollback_bill_id": 2551,
            }
        ]
    },
    "ticket_type": "REDIS_DATA_STRUCTURE_TASK_DELETE",
    "ignore_duplication": True,
}

# redis 重建从库单据
REDIS_REBUILD_SLAVE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "bk_cloud_id": 0,
                "cluster_ids": [CLUSTER_ID],
                "pairs": [
                    {
                        "redis_master": {"bk_cloud_id": 0, "bk_host_id": 493, "ip": "5.5.5.3"},
                        "redis_slave": {"count": 1, "old_slave_ip": "5.5.5.5", "spec_id": 333},
                    }
                ],
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "REDIS_CLUSTER_ADD_SLAVE",
}

# redis 整机替换
REDIS_CLUSTER_CUTOFF_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "bk_cloud_id": 0,
                "cluster_ids": [CLUSTER_ID],
                "proxy": [],
                "redis_master": [{"bk_host_id": 493, "ip": "5.5.5.3", "spec_id": 333}],
                "redis_slave": [],
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "REDIS_CLUSTER_CUTOFF",
}

# redis 主从替换
REDIS_MASTER_SLAVE_SWITCH_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "force": True,
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID],
                "online_switch_type": "user_confirm",
                "pairs": [{"redis_master": "5.5.5.3", "redis_slave": "5.5.5.5"}],
            }
        ],
    },
    "remark": "",
    "ticket_type": "REDIS_MASTER_SLAVE_SWITCH",
}

# redis 迁移
REDIS_MIGRATE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "display_info": {"db_version": ["redis-6.2.14"], "instance": "5.5.5.5:30000"},
                "old_nodes": {
                    "master": [
                        {
                            "bk_biz_id": BK_BIZ_ID,
                            "bk_cloud_id": 0,
                            "bk_host_id": 493,
                            "ip": "5.5.5.3",
                            "port": 30000,
                        }
                    ],
                    "slave": [
                        {
                            "bk_biz_id": BK_BIZ_ID,
                            "bk_cloud_id": 0,
                            "bk_host_id": 495,
                            "ip": "5.5.5.5",
                            "port": 30000,
                        }
                    ],
                },
                "resource_spec": {"backend_group": {"count": 1, "spec_id": 333}},
            }
        ]
    },
    "remark": "",
    "ticket_type": "REDIS_CLUSTER_INS_MIGRATE",
}

# redis 版本升级
REDIS_VERSION_UPDATE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "node_type": "Backend",
                "cluster_ids": [CLUSTER_ID],
                "target_version": "redis-6.2.14",
                "current_versions": ["redis-4.0.11-t-v1"],
            }
        ]
    },
    "remark": "",
    "ticket_type": "REDIS_VERSION_UPDATE_ONLINE",
}

# redis 构造实例数据回写
REDIS_CLUSTER_ROLLBACK_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "dts_copy_type": "copy_from_rollback_instance",
        "infos": [
            {
                "dst_cluster": CLUSTER_ID,
                "key_black_regex": "",
                "key_white_regex": "*",
                "recovery_time_point": "2024-05-19T00:00:00+08:00",
                "src_cluster": "2.2.3.3:50000",
            }
        ],
        "write_mode": "delete_and_write_to_redis",
    },
    "remark": "",
    "ticket_type": "REDIS_CLUSTER_ROLLBACK_DATA_COPY",
}

# redis 集群数据构造
REDIS_DATA_STRUCTURE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "bk_cloud_id": 0,
                "cluster_id": 130,
                "master_instances": [
                    "5.5.5.3:30000",
                    "5.5.5.3:30001",
                    "5.5.5.3:30002",
                    "5.5.5.3:30003",
                ],
                "recovery_time_point": "2025-06-19T04:00:00+08:00",
                "resource_spec": {"redis": {"count": 1, "spec_id": 333}},
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "REDIS_DATA_STRUCTURE",
}

# redis 集群扩容
REDIS_PROXY_SCALE_UP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "bk_cloud_id": 0,
                "cluster_id": CLUSTER_ID,
                "resource_spec": {"proxy": {"count": 1, "spec_id": 338}},
                "target_proxy_count": 3,
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "REDIS_PROXY_SCALE_UP",
    "ignore_duplication": True,
}

# redis 集群分片变更
REDIS_CLUSTER_SHARD_NUM_UPDATE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "data_check_repair_setting": {
            "execution_frequency": "once_after_replication",
            "type": "data_check_and_repair",
        },
        "infos": [
            {
                "capacity": 128.5,
                "cluster_shard_num": 2,
                "current_shard_num": 4,
                "current_spec_id": 333,
                "db_version": "Redis-5",
                "future_capacity": 1,
                "online_switch_type": "user_confirm",
                "resource_spec": {
                    "backend_group": {"affinity": "CROS_SUBZONE", "count": 1, "spec_id": 333},
                    "proxy": {"affinity": "CROS_SUBZONE", "count": 2, "spec_id": 338},
                },
                "src_cluster": CLUSTER_ID,
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "REDIS_CLUSTER_SHARD_NUM_UPDATE",
    "ignore_duplication": True,
}

# redis 集群类型变更
REDIS_CLUSTER_TYPE_UPDATE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "data_check_repair_setting": {
            "execution_frequency": "once_after_replication",
            "type": "data_check_and_repair",
        },
        "infos": [
            {
                "capacity": 128.5,
                "cluster_shard_num": 16,
                "current_cluster_type": "TwemproxyRedisInstance",
                "current_shard_num": 4,
                "current_spec_id": 333,
                "db_version": "Redis-5",
                "future_capacity": 3,
                "online_switch_type": "user_confirm",
                "resource_spec": {
                    "backend_group": {"affinity": "CROS_SUBZONE", "count": 1, "spec_id": 335},
                    "proxy": {"affinity": "CROS_SUBZONE", "count": 2, "spec_id": 338},
                },
                "src_cluster": CLUSTER_ID,
                "target_cluster_type": "PredixyRedisCluster",
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "REDIS_CLUSTER_TYPE_UPDATE",
    "ignore_duplication": True,
}

# redis 接入clb
REDIS_PLUGIN_CREATE_CLB = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {"cluster_id": CLUSTER_ID},
    "ticket_type": "REDIS_PLUGIN_CREATE_CLB",
}

# redis 集群机器信息
REDIS_MACHINE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "5.5.5.5",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "dns",
        "machine_type": MachineType.TENDISCACHE.value,
        "cluster_type": ClusterType.TendisTwemproxyRedisInstance,
        "bk_host_id": 495,
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
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "5.5.5.3",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "dns",
        "machine_type": MachineType.TENDISCACHE.value,
        "cluster_type": ClusterType.TendisTwemproxyRedisInstance,
        "bk_host_id": 493,
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

# 初始化redis集群
REDIS_CLUSTER_DATA = [
    {
        "id": CLUSTER_ID,
        "creator": BK_USERNAME,
        "updater": BK_USERNAME,
        "name": "kiotest-iam-1",
        "alias": "kiotest-iam-1",
        "bk_biz_id": BK_BIZ_ID,
        "cluster_type": ClusterType.TendisTwemproxyRedisInstance,
        "db_module_id": 0,
        "immute_domain": "cache.kiotest-iam-1.dba.db",
        "major_version": "Redis-5",
        "phase": "online",
        "status": "normal",
        "bk_cloud_id": 0,
        "region": "default",
        "time_zone": "+08:00",
        "disaster_tolerance_level": "NONE",
    },
    {
        "id": 131,
        "creator": BK_USERNAME,
        "updater": BK_USERNAME,
        "name": "kiotest-iam-2",
        "alias": "kiotest-iam-2",
        "bk_biz_id": BK_BIZ_ID,
        "cluster_type": ClusterType.TendisTwemproxyRedisInstance,
        "db_module_id": 0,
        "immute_domain": "cache.kiotest-iam-2.dba.db",
        "major_version": "Redis-5",
        "phase": "online",
        "status": "normal",
        "bk_cloud_id": 0,
        "region": "default",
        "time_zone": "+08:00",
        "disaster_tolerance_level": "CROS_SUBZONE",
    },
]

# 初始化机器实际的城市信息
REDIS_BKCITY_DATA = {
    "creator": BK_USERNAME,
    "create_at": "2024-03-13 11:14:48.433116",
    "updater": "",
    "update_at": "2024-03-13 11:14:48.433116",
    "bk_idc_city_id": 0,
    "bk_idc_city_name": "default",
    "logical_city_id": 1,
}

# 初始化逻辑上的城市信息
REDIS_LOGICALCITY_DATA = {
    "creator": BK_USERNAME,
    "create_at": "2024-03-13 11:14:48.433116",
    "updater": "",
    "update_at": "2024-03-13 11:14:48.433116",
    "NAME": "default",
}

REDIS_STORAGE_INSTANCE_TUPLE = {
    "creator": BK_USERNAME,
    "create_at": "2024-03-13 11:14:48.433116",
    "updater": "",
    "update_at": "2024-03-13 11:14:48.433116",
}

REDIS_STORAGE_INSTANCE = [
    {
        "id": 1,
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "version": "",
        "port": 30000,
        "machine_id": 495,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": "tendiscache",
        "instance_role": "redis_slave",
        "instance_inner_role": "slave",
        "cluster_type": "TwemproxyRedisInstance",
        "status": "unavailable",
        "phase": "online",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7979,
        "is_stand_by": "1",
    },
    {
        "id": 2,
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "version": "",
        "port": 30000,
        "machine_id": 493,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": "tendiscache",
        "instance_role": "redis_master",
        "instance_inner_role": "master",
        "cluster_type": "TwemproxyRedisInstance",
        "status": "running",
        "phase": "online",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7975,
        "is_stand_by": "1",
    },
]

REDIS_SPEC_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "spec_id": 333,
        "spec_name": "无限制",
        "spec_cluster_type": "redis",
        "spec_machine_type": "TwemproxyRedisInstance",
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
        "spec_id": 335,
        "spec_name": "2c_4g_50g",
        "spec_cluster_type": "redis",
        "spec_machine_type": "TwemproxyRedisInstance",
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
        "create_at": "2024-03-15 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-15 11:14:48.433116",
        "spec_id": 338,
        "spec_name": "2c_4g_50g",
        "spec_cluster_type": "redis",
        "spec_machine_type": "proxy",
        "cpu": {"max": 2, "min": 2},
        "mem": {"max": 4, "min": 3},
        "device_class": ["S5.MEDIUM4", "SA2.MEDIUM4", "S5t.MEDIUM4"],
        "storage_spec": [{"size": 50, "type": "ALL", "mount_point": "/data"}],
        "desc": "基础机型",
        "enable": True,
        "instance_num": 0,
        "qps": {},
    },
]

REDIS_TENDIS_ROLLBACK_TASK_DATA = {
    "creator": BK_USERNAME,
    "create_at": "2024-03-13 11:14:48.433116",
    "updater": "",
    "update_at": "2024-03-13 11:14:48.433116",
    "related_rollback_bill_id": 2551,
    "bk_biz_id": BK_BIZ_ID,
    "app": "",
    "bk_cloud_id": 0,
    "prod_cluster_type": ClusterType.TendisTwemproxyRedisInstance,
    "prod_cluster": "cache.kiotest-iam-1.dba.db",
    "prod_instance_range": ["5.5.5.5:30000", "5.5.5.5:30001", "5.5.5.5:30002", "5.5.5.5:30003"],
    "temp_cluster_type": ClusterType.TendisTwemproxyRedisInstance,
    "temp_proxy_password": "xxxxxxx",
    "temp_instance_range": [
        "2.2.3.3:30000",
        "2.2.3.3:30001",
        "2.2.3.3:30002",
        "2.2.3.3:30003",
    ],
    "temp_cluster_proxy": "2.2.3.3:50000",
    "prod_temp_instance_pairs": [
        ["5.5.5.5:30000", "2.2.3.3:30000"],
        ["5.5.5.5:30001", "2.2.3.3:30001"],
        ["5.5.5.5:30002", "2.2.3.3:30002"],
        ["5.5.5.5:30003", "2.2.3.3:30003"],
    ],
    "status": 2,
    "specification": {
        "id": 333,
        "cpu": {"max": 256, "min": 1},
        "mem": {"max": 256, "min": 1},
        "qps": {},
        "name": "无限制",
        "count": 1,
        "device_class": [],
        "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
    },
    "host_count": 1,
    "recovery_time_point": "2024-05-19T00:00:00+08:00",
    "prod_cluster_id": CLUSTER_ID,
    "destroyed_status": 0,
    "temp_redis_password": "xxxxxxxxxx",
}
