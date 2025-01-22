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

BK_BIZ_ID = 2005000002
DB_MODULE_ID = 1
CLUSTER_ID = 1
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
        "db_module_id": DB_MODULE_ID + 1,
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
            "sqlserver_single": {
                "spec_id": 1,
                "spec_name": "2核_4G_10G",
                "spec_cluster_type": "sqlserver_single",
                "spec_machine_type": "sqlserver_single",
                "affinity": "SAME_SUBZONE_CROSS_SWTICH",
                "location_spec": {"city": "default", "sub_zone_ids": []},
                "count": 2,
                "cpu": {"max": 4, "min": 2},
                "mem": {"max": 8, "min": 4},
                "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
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
        "nodes": {"sqlserver_single": [{"ip": "2.2.2.1", "bk_cloud_id": 0}]},
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
        "db_module_id": DB_MODULE_ID + 1,
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
                "storage_spec": [{"size": 10, "type": "ALL", "mount_point": "/data"}],
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
        "db_module_id": DB_MODULE_ID + 1,
        "cluster_count": 1,
        "inst_num": 1,
        "ip_source": "manual_input",
        "nodes": {
            "sqlserver_ha": [
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
                "dst_cluster": CLUSTER_ID + 1,
                "db_list": [],
                "ignore_db_list": [],
                "rename_infos": [{"db_name": "test_database", "target_db_name": "test_database"}],
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
        "ip_source": "manual_input",
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID + 1],
                "old_slave_host": {"ip": "2.2.2.1", "bk_cloud_id": 0, "bk_host_id": 1001},
                "new_slave_host": {"ip": "2.2.2.2", "bk_cloud_id": 0, "bk_host_id": 1002},
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
                "old_slave_host": {"ip": "2.2.2.3", "bk_cloud_id": 0, "bk_host_id": 1003},
            }
        ],
    },
}
# SQLSERVER 定点构造申请单据
SQLSERVER_ROLLBACK_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.SQLSERVER_ROLLBACK,
    "details": {
        "is_local": False,  # 是否代表原地构造，true代表是，false代表远程构造
        "infos": [
            {
                "src_cluster": CLUSTER_ID,
                "dst_cluster": CLUSTER_ID + 1,  # 如果是原地构造，target_cluster_id=cluster_id
                "db_list": [],
                "ignore_db_list": [],
                "rename_infos": [
                    {
                        "db_name": "SampleDatabaseRollback2",
                        "target_db_name": "SampleDatabase2",
                        "rename_db_name": "SampleDatabaseBak001",
                    }
                ],
                "restore_backup_file": {"backup_id": "XXX", "logs": [{}]},
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
        "db_module_id": DB_MODULE_ID + 1,
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
        "id": 1,
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
        "id": 2,
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
        "id": 3,
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
        '"storage_spec": [{"size": 20, "type": "ALL", "mount_point": "C:\\", "isSystemDrive": true},'
        ' {"size": 30, "type": "ALL", "mount_point": "D:\\", "isSystemDrive": true}]}',
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
        '"storage_spec": [{"size": 20, "type": "ALL", "mount_point": "C:\\", "isSystemDrive": true},'
        ' {"size": 30, "type": "ALL", "mount_point": "D:\\", "isSystemDrive": true}]}',
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
        '"storage_spec": [{"size": 20, "type": "ALL", "mount_point": "C:\\", "isSystemDrive": true},'
        ' {"size": 30, "type": "ALL", "mount_point": "D:\\", "isSystemDrive": true}]}',
        "spec_id": 1,
        "bk_agent_id": "",
    },
]
