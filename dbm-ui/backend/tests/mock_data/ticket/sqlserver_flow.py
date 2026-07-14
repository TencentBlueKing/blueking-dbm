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
from backend.tests.mock_data.constant import DB_MODULE_ID
from backend.ticket.constants import TicketType

BK_BIZ_ID = 2005000002
CLUSTER_ID = 101
BK_USERNAME = "admin"

DB_MODULE_DATA = [
    {
        "creator": "admin",
        "create_at": "2022-07-28 07:09:46",
        "updater": "admin",
        "update_at": "2022-07-29 07:09:46",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_name": "sqlserver-single-module",
        "db_module_id": DB_MODULE_ID,
        "cluster_type": ClusterType.SqlserverSingle.value,
        "alias_name": "",
    },
    {
        "creator": "admin",
        "create_at": "2022-07-28 07:09:46",
        "updater": "admin",
        "update_at": "2022-07-29 07:09:46",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_name": "sqlserver-ha-module",
        "db_module_id": DB_MODULE_ID,
        "cluster_type": ClusterType.SqlserverHA.value,
        "alias_name": "",
    },
]
# sqlserver 禁用单据
SQLSERVER_DISABLE_TICKET_DATA = {
    "created_by": BK_USERNAME,
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_DISABLE.value,
    "details": {"cluster_ids": [CLUSTER_ID]},
}

# sqlserver 启用单据
SQLSERVER_ENABLE_TICKET_DATA = {
    "created_by": BK_USERNAME,
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_ENABLE.value,
    "details": {"cluster_ids": [CLUSTER_ID + 1]},
}

# sqlserver 销毁单据
SQLSERVER_DESTROY_TICKET_DATA = {
    "created_by": BK_USERNAME,
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_DESTROY.value,
    "details": {"cluster_ids": [CLUSTER_ID + 1]},
}

# sqlserver 单节点部署单据
SQLSERVER_SINGLE_APPLY_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "remark": "",
    "ticket_type": TicketType.SQLSERVER_SINGLE_APPLY.value,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "深圳",
        "db_module_id": DB_MODULE_ID,
        "cluster_count": 1,
        "inst_num": 1,
        "ip_source": "resource_pool",
        "resource_spec": {
            "backend": {
                "spec_id": 1,
                "spec_name": "2核_4G_10G",
                "spec_cluster_type": "sqlserver_single",
                "spec_machine_type": "sqlserver_single",
                "affinity": "SAME_SUBZONE_CROSS_SWTICH",
                "location_spec": {"city": "default", "sub_zone_ids": []},
                "count": 2,
                "cpu": {"max": 4, "min": 2},
                "mem": {"max": 8, "min": 4},
                "storage_spec": [{"min": 10, "max": 2147483647, "type": "ALL", "mount_point": "/data"}],
            }
        },
        "domains": [
            {
                "key": "sqlserverha01",
                "master": "sqlserver-hadb.sqlserverha01.dba-test.db",
                "slave": "sqlserver-hadr.sqlserverha01.dba-test.db",
            }
        ],
        "db_version": "MSSQL_Enterprise_2016",
        "db_module_name": "test-sqlserver01",
        "start_mssql_port": 20000,
        "disaster_tolerance_level": "SAME_SUBZONE_CROSS_SWTICH",
    },
}

# sqlserver 单节点部署手动输入单据
SQLSERVER_SINGLE_MANUAL_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "remark": "",
    "ticket_type": TicketType.SQLSERVER_SINGLE_APPLY.value,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "深圳",
        "db_module_id": DB_MODULE_ID,
        "cluster_count": 1,
        "inst_num": 1,
        "ip_source": "manual_input",
        "nodes": {"backend": [{"ip": "2.2.2.1", "bk_cloud_id": 0}]},
        "domains": [
            {
                "key": "sqlserverha01",
                "master": "sqlserver-hadb.sqlserverha01.dba-test.db",
                "slave": "sqlserver-hadr.sqlserverha01.dba-test.db",
            }
        ],
        "db_version": "MSSQL_Enterprise_2016",
        "db_module_name": "test-sqlserver01",
        "start_mssql_port": 20000,
    },
}

# sqlserver 主从节点部署单据
SQLSERVER_HA_APPLY_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "remark": "",
    "ticket_type": TicketType.SQLSERVER_HA_APPLY.value,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "深圳",
        "db_module_id": DB_MODULE_ID,
        "cluster_count": 2,
        "inst_num": 1,
        "ip_source": "resource_pool",
        "nodes": {"backend": []},
        "resource_spec": {
            "backend_group": {
                "spec_id": 2,
                "spec_name": "2核_4G_10G",
                "spec_cluster_type": "sqlserver_ha",
                "spec_machine_type": "sqlserver_ha",
                "affinity": "SAME_SUBZONE_CROSS_SWTICH",
                "location_spec": {"city": "default", "sub_zone_ids": []},
                "count": 2,
                "cpu": {"max": 4, "min": 2},
                "mem": {"max": 8, "min": 4},
                "storage_spec": [{"min": 10, "max": 2147483647, "type": "ALL", "mount_point": "/data"}],
            }
        },
        "domains": [
            {
                "key": "testaa",
                "master": "sqlserver-hadb.testaa.dba-test.db",
                "slave": "sqlserver-hadr.testaa.dba-test.db",
            }
        ],
        "charset": "Chinese_PRC_CI_AS",
        "db_version": "MSSQL_Enterprise_2016",
        "db_module_name": "sqlserver-ha",
        "city_name": "无地域",
        "spec_display": "",
        "start_mysql_port": 20000,
        "disaster_tolerance_level": "SAME_SUBZONE_CROSS_SWTICH",
        "start_mssql_port": 48322,
    },
}

# sqlserver 主从节点手动部署单据
SQLSERVER_HA_MANUAL_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "remark": "",
    "ticket_type": TicketType.SQLSERVER_HA_APPLY.value,
    "details": {
        "bk_cloud_id": 0,
        "city_code": "深圳",
        "db_module_id": DB_MODULE_ID,
        "cluster_count": 1,
        "inst_num": 1,
        "ip_source": "manual_input",
        "nodes": {
            "backend": [
                {"ip": "3.2.2.1", "bk_cloud_id": 0, "bk_host_id": 3001},
                {"ip": "3.2.2.2", "bk_cloud_id": 0, "bk_host_id": 3002},
            ]
        },
        "domains": [
            {
                "key": "testaa",
                "master": "sqlserver-hadb.testaa.dba-test.db",
                "slave": "sqlserver-hadr.testaa.dba-test.db",
            }
        ],
        "charset": "Chinese_PRC_CI_AS",
        "db_version": "MSSQL_Enterprise_2016",
        "db_module_name": "sqlserver-ha",
        "city_name": "无地域",
        "spec_display": "",
        "start_mysql_port": 20000,
        "disaster_tolerance_level": "SAME_SUBZONE_CROSS_SWTICH",
        "start_mssql_port": 48322,
    },
}

# sqlserver DB重命名单据
SQLSERVER_DBRENAME_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_DBRENAME.value,
    "details": {
        "force": "false",
        "infos": [{"cluster_id": CLUSTER_ID, "from_database": "test_database", "to_database": "test_database_bak"}],
    },
}

# sqlserver 备份数据库单据
SQLSERVER_BACKUP_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_BACKUP_DBS,
    "details": {
        "backup_place": "master",
        "file_tag": "DBFILE1M",
        "backup_type": "full_backup",
        "infos": [
            {"cluster_id": CLUSTER_ID, "backup_dbs": ["test_database"], "db_list": ["M%"], "ignore_db_list": []}
        ],
    },
}

# SQLSERVER 数据迁移单据
SQLSERVER_DATA_MIGRATE_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_FULL_MIGRATE,
    "details": {
        "dts_mode": "full",
        "need_auto_rename": False,
        "infos": [
            {
                "src_cluster": CLUSTER_ID,
                "dst_cluster_list": [CLUSTER_ID + 1, CLUSTER_ID + 2],
                "db_list": [],
                "ignore_db_list": [],
                "rename_infos": [
                    {
                        "db_name": "test_database",
                        "target_db_name": "test_database",
                        "rename_cluster_list": [CLUSTER_ID + 1],
                        "rename_db_name": "test_database_bak",
                    }
                ],
            }
        ],
    },
}

# SQLSERVER DB清档单据
SQLSERVER_CLEAR_DBS_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_CLEAR_DBS,
    "details": {
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "clean_dbs": ["test_database"],
                "clean_dbs_patterns": ["test%"],
                "clean_ignore_dbs_patterns": [],
                "clean_tables": ["t1"],
                "ignore_clean_tables": [],
                "clean_mode": "clean_tables",
            }
        ]
    },
}

# SQLSERVER 导入sql执行单据
SQLSERVER_IMPORT_SQLFILE_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_IMPORT_SQLFILE,
    "details": {
        "charset": "GBK",
        "force": False,
        "cluster_ids": [CLUSTER_ID + 1],
        "execute_objects": [{"dbnames": ["master"], "ignore_dbnames": [], "sql_files": [], "import_mode": "manual"}],
        "ticket_mode": {"mode": "auto", "trigger_time": "2024-04-29T12:11:11+08:00"},
    },
}

# SQLSERVER 主从互切单据
SQLSERVER_MASTER_SLAVE_SWITCH_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_MASTER_SLAVE_SWITCH,
    "remark": "",
    "details": {
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID + 1],
                "master": {"ip": "2.2.2.2", "bk_cloud_id": 0, "bk_host_id": 1002},
                "slave": {"ip": "2.2.2.3", "bk_cloud_id": 0, "bk_host_id": 1003},
            }
        ]
    },
}

# SQLSERVER 主故障切换单据
SQLSERVER_MASTER_FAIL_OVER_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_MASTER_FAIL_OVER,
    "remark": "",
    "details": {
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID + 1],
                "master": {"ip": "1.1.1.3", "bk_cloud_id": 0, "bk_host_id": 2},
                "slave": {"ip": "1.1.1.4", "bk_cloud_id": 0, "bk_host_id": 3},
            }
        ]
    },
}

# SQLSERVER 重置单据
SQLSERVER_RESET_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_RESET,
    "remark": "",
    "details": {
        "infos": [
            {
                "cluster_id": CLUSTER_ID + 1,
                "new_cluster_name": "sqlserverha03",
                "new_immutable_domain": "sqlserver-hadb.sqlserverha03",
                "new_slave_domain": "sqlserver-singledb.test2.dba-test.db",
            }
        ]
    },
}

# SQLSERVER 从库原地重建单据
SQLSERVER_RESTORE_LOCAL_SLAVE_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_RESTORE_LOCAL_SLAVE,
    "remark": "xxx",
    "details": {
        "infos": [
            {
                "cluster_id": CLUSTER_ID + 1,
                "slave": {"ip": "2.2.2.1", "bk_cloud_id": 0, "port": 48322, "bk_host_id": 1001},
            }
        ]
    },
}

# SQLSERVER 从库新机重建单据
SQLSERVER_RESTORE_SLAVE_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_RESTORE_SLAVE,
    "remark": "xxx",
    "details": {
        "ip_source": "resource_pool",
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID + 1],
                "old_nodes": {"old_slave_host": [{"ip": "2.2.2.1", "bk_cloud_id": 0, "bk_host_id": 1003}]},
                "resource_spec": {
                    "sqlserver_ha": {"hosts": [{"ip": "2.2.2.2", "bk_cloud_id": 0, "bk_host_id": 1002}]}
                },
            }
        ],
    },
}

# SQLSERVER 从库资源池新机重建单据
SQLSERVER_RESTORE_SLAVE_SOURCE_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_RESTORE_SLAVE,
    "remark": "xxx",
    "details": {
        "ip_source": "resource_pool",
        "infos": [
            {
                "resource_spec": {"sqlserver_ha": {"spec_id": 2, "count": 1}},
                "cluster_ids": [CLUSTER_ID + 1],
                "old_nodes": {"old_slave_host": [{"ip": "2.2.2.3", "bk_cloud_id": 0, "bk_host_id": 1003}]},
            }
        ],
    },
}
# SQLSERVER 定点构造申请单据（远程构造，目标集群不同于源集群）
SQLSERVER_ROLLBACK_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_ROLLBACK,
    "details": {
        "is_time_fixed": False,  # False 代表使用最新备份，True 代表指定时间
        "infos": [
            {
                "src_cluster": CLUSTER_ID,
                "dst_cluster": CLUSTER_ID + 1,  # 目标集群 ID
                "db_list": ["test%"],  # 库正则
                "ignore_db_list": [],  # 忽略库正则
                "rename_infos": [
                    {
                        "db_name": "test_database",
                        "target_db_name": "test_database_restored",
                        "rename_db_name": "test_database_bak",
                    }
                ],
                "restore_backup_file": {
                    "backup_id": "backup_20240101_120000",
                    # backup_db_list 必须包含 rename_infos 中出现的所有 db_name，
                    # 否则 SqlserverDBConstructValidator.pre_check_dbs_in_backup_list 会失败
                    "backup_db_list": ["test_database", "test_db2", "master"],
                    "start_time": "2024-01-01 11:00:00",
                    "end_time": "2024-01-01 12:00:00",
                    "complete": True,
                    "expected_cnt": 3,
                    "real_cnt": 3,
                    "role": "master",
                    "backup_db_size_kb": 10240,
                    "backup_file_size_kb": 5120,
                    "excluded_db_list": [],
                    "bill_id": "",
                    # 每条 log 补齐 pre_check_log_backup_continuity 所需字段
                    # （backup_end_time / cluster_domain / last_lsn / file_name），
                    # 便于将 is_time_fixed 切换为 True + restore_time 场景时直接复用
                    "logs": [
                        {
                            "dbname": "test_database",
                            "backup_id": "backup_20240101_120000",
                            "backup_end_time": "2024-01-01 12:00:00",
                            "cluster_domain": "sqlserver.test.db",
                            "last_lsn": "1000000000",
                            "file_name": "test_database_full_20240101_120000.bak",
                        },
                        {
                            "dbname": "test_db2",
                            "backup_id": "backup_20240101_120000",
                            "backup_end_time": "2024-01-01 12:00:00",
                            "cluster_domain": "sqlserver.test.db",
                            "last_lsn": "1000000001",
                            "file_name": "test_db2_full_20240101_120000.bak",
                        },
                        {
                            "dbname": "master",
                            "backup_id": "backup_20240101_120000",
                            "backup_end_time": "2024-01-01 12:00:00",
                            "cluster_domain": "sqlserver.test.db",
                            "last_lsn": "1000000002",
                            "file_name": "master_full_20240101_120000.bak",
                        },
                    ],
                },
            }
        ],
    },
}

# SQLSERVER 原地构造申请单据（目标集群等于源集群，需对源集群重命名）
SQLSERVER_ROLLBACK_LOCAL_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_ROLLBACK_LOCAL,
    "details": {
        "is_time_fixed": False,  # False 代表使用最新备份，True 代表指定时间
        "infos": [
            {
                "src_cluster": CLUSTER_ID,
                "dst_cluster": CLUSTER_ID,  # 原地构造时目标集群等于源集群
                "db_list": ["test%"],
                "ignore_db_list": ["test_temp%"],
                "rename_infos": [],  # 原地构造可能不需要重命名
                "restore_backup_file": {
                    "backup_id": "backup_20240101_120000",
                    # backup_db_list 必须包含 rename_infos 中出现的所有 db_name；
                    # 当前 rename_infos 为空虽不会触发 pre_check_dbs_in_backup_list 的
                    # 逐库校验，但补齐可保证未来任何 rename 追加均无需再改 mock
                    "backup_db_list": ["test_database", "test_db2"],
                    "start_time": "2024-01-01 11:00:00",
                    "end_time": "2024-01-01 12:00:00",
                    "complete": True,
                    "expected_cnt": 2,
                    "real_cnt": 2,
                    "role": "master",
                    "backup_db_size_kb": 8192,
                    "backup_file_size_kb": 4096,
                    "excluded_db_list": [],
                    "bill_id": "",
                    "logs": [
                        {
                            "dbname": "test_database",
                            "backup_id": "backup_20240101_120000",
                            "backup_end_time": "2024-01-01 12:00:00",
                            "cluster_domain": "sqlserver.test.db",
                            "last_lsn": "1000000000",
                            "file_name": "test_database_full_20240101_120000.bak",
                        },
                        {
                            "dbname": "test_db2",
                            "backup_id": "backup_20240101_120000",
                            "backup_end_time": "2024-01-01 12:00:00",
                            "cluster_domain": "sqlserver.test.db",
                            "last_lsn": "1000000001",
                            "file_name": "test_db2_full_20240101_120000.bak",
                        },
                    ],
                },
            }
        ],
    },
}

DBCONFIG_DATA = {
    "buffer_percent": "50",
    "charset": "Chinese_PRC_CI_AS",
    "db_version": "MSSQL_Enterprise_2016",
    "max_remain_mem_gb": "32",
    "sync_type": "mirroring",
    "system_version": "WindowsServer2016",
}

# 初始化SQLSERVER集群
SQLSERVER_CLUSTER_DATA = [
    {
        "id": CLUSTER_ID,
        "creator": BK_USERNAME,
        "updater": BK_USERNAME,
        "name": "sqlserver-single01",
        "alias": "single01",
        "bk_biz_id": BK_BIZ_ID,
        "cluster_type": ClusterType.SqlserverSingle.value,
        "db_module_id": DB_MODULE_ID,
        "immute_domain": "test3-sqlserver.dba-test.db",
        "major_version": "MSSQL_Enterprise_2016",
        "phase": "online",
        "status": "normal",
        "bk_cloud_id": 0,
        "region": "default",
        "time_zone": "+08:00",
        "disaster_tolerance_level": "NONE",
    },
    {
        "id": CLUSTER_ID + 1,
        "creator": BK_USERNAME,
        "updater": BK_USERNAME,
        "name": "sqlserverha02",
        "alias": "sqlserverha02",
        "bk_biz_id": BK_BIZ_ID,
        "cluster_type": ClusterType.SqlserverHA.value,
        "db_module_id": DB_MODULE_ID,
        "immute_domain": "test3-sqlserver-1.dba-test.db",
        "major_version": "MSSQL_Enterprise_2016",
        "phase": "offline",
        "status": "normal",
        "bk_cloud_id": 0,
        "region": "default",
        "time_zone": "+08:00",
        "disaster_tolerance_level": "NONE",
    },
]

# SQLSERVER SINGLE实例数据
SQLSERVER_STORAGE_INSTANCE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-14 01:36:51.626234",
        "updater": "",
        "update_at": "2024-03-14 01:36:51.626234",
        "version": "MSSQL_Enterprise_2016",
        "port": 10000,
        "db_module_id": DB_MODULE_ID,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": MachineType.SQLSERVER_SINGLE.value,
        "cluster_type": ClusterType.SqlserverSingle.value,
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7089,
        "machine_id": 1001,
        "phase": "online",
        "instance_role": "orphan",
        "instance_inner_role": "master",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-14 01:36:51.626234",
        "updater": "",
        "update_at": "2024-03-14 01:36:51.626234",
        "version": "MSSQL_Enterprise_2016",
        "port": 10000,
        "db_module_id": DB_MODULE_ID,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": MachineType.SQLSERVER_HA.value,
        "cluster_type": ClusterType.SqlserverHA.value,
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7089,
        "machine_id": 1002,
        "phase": "online",
        "instance_role": "backend_master",
        "instance_inner_role": "master",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-14 01:36:51.626234",
        "updater": "",
        "update_at": "2024-03-14 01:36:51.626234",
        "version": "MSSQL_Enterprise_2016",
        "port": 10000,
        "db_module_id": DB_MODULE_ID,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": MachineType.SQLSERVER_HA.value,
        "cluster_type": ClusterType.SqlserverHA.value,
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7089,
        "machine_id": 1003,
        "phase": "online",
        "instance_role": "backend_slave",
        "instance_inner_role": "slave",
    },
]

# 构建storageinstancetuple数据
SQLSERVER_STORAGEINSTANCETUPLE_DATA = {
    "creator": BK_USERNAME,
    "create_at": "2024-03-13 11:14:48.433116",
    "updater": "",
    "update_at": "2024-03-13 11:14:48.433116",
    "ejector": 2,
    "receiver": 3,
}

# SQLSERVER 集群机器信息
SQLSERVER_MACHINE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "2.2.2.3",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "storage",
        "machine_type": MachineType.SQLSERVER_SINGLE.value,
        "cluster_type": ClusterType.SqlserverSingle.value,
        "bk_host_id": 1003,
        "bk_os_name": "Windows Server 2012 R2 Standard",
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
        "spec_config": '{"id": 440, "cpu": {"max": 4, "min": 2}, "mem": {"max": 8, "min": 4}, '
        '"qps": {"max": 0, "min": 0}, "name": "1核_4G_20G", "count": 1, "device_class": [], '
        '"storage_spec": [{"min": 20, "max": 2147483647, "type": "ALL", "mount_point": "C:\\", "isSystemDrive": true},'
        ' {"min": 30, "type": "ALL", "mount_point": "D:\\", "isSystemDrive": true}]}',
        "spec_id": 1,
        "bk_agent_id": "",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "2.2.2.2",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "storage",
        "machine_type": MachineType.SQLSERVER_HA.value,
        "cluster_type": ClusterType.SqlserverHA.value,
        "bk_host_id": 1002,
        "bk_os_name": "Windows Server 2012 R2 Standard",
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
        "spec_config": '{"id": 440, "cpu": {"max": 4, "min": 2}, "mem": {"max": 8, "min": 4}, '
        '"qps": {"max": 0, "min": 0}, "name": "1核_4G_20G", "count": 1, "device_class": [], '
        '"storage_spec": [{"min": 20, "max": 2147483647, "type": "ALL", "mount_point": "C:\\", "isSystemDrive": true},'
        ' {"min": 30, "type": "ALL", "mount_point": "D:\\", "isSystemDrive": true}]}',
        "spec_id": 2,
        "bk_agent_id": "",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "2.2.2.1",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 1003,
        "access_layer": "storage",
        "machine_type": MachineType.SQLSERVER_HA.value,
        "cluster_type": ClusterType.SqlserverHA.value,
        "bk_host_id": 1001,
        "bk_os_name": "Windows Server 2012 R2 Standard",
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
        "spec_config": '{"id": 440, "cpu": {"max": 4, "min": 2}, "mem": {"max": 8, "min": 4}, '
        '"qps": {"max": 0, "min": 0}, "name": "1核_4G_20G", "count": 1, "device_class": [], '
        '"storage_spec": [{"min": 20, "max": 2147483647, "type": "ALL", "mount_point": "C:\\", "isSystemDrive": true},'
        ' {"min": 30, "type": "ALL", "mount_point": "D:\\", "isSystemDrive": true}]}',
        "spec_id": 1,
        "bk_agent_id": "",
    },
]
