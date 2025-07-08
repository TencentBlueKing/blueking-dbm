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
import uuid

from backend.configuration.constants import DBType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.machine_type import MachineType
from backend.db_services.dbbase.constants import IpSource
from backend.flow.models import StateType
from backend.tests.mock_data import constant
from backend.tests.mock_data.ticket.ticket_flow import BK_BIZ_ID, ROOT_ID
from backend.ticket.constants import TicketType

BK_USERNAME = "admin"
CLUSTER_ID = 125
SQL_IMPORT_NODE_ID = "a651615616516dwqd156dq6616516qd"
SQL_IMPORT_VERSION_ID = "d516156156qwd161651665161656"

MYSQL_HA_DB_TABLE_BACKUP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "db_patterns": ["*"],
                "table_patterns": ["*"],
                "ignore_dbs": [],
                "ignore_tables": [],
            }
        ]
    },
    "remark": "",
    "ticket_type": "MYSQL_HA_DB_TABLE_BACKUP",
}

MYSQL_DELETE_CLEAR_DB_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "clear_mode": {"days": 7, "mode": "timer"},
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "truncate_data_type": "drop_table",
                "db_patterns": ["*"],
                "table_patterns": ["*"],
                "ignore_dbs": [],
                "ignore_tables": [],
                "force": True,
            }
        ],
    },
    "remark": "",
    "ticket_type": "MYSQL_HA_TRUNCATE_DATA",
}

MYSQL_ROLLBACK_CLUSTER_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "backup_source": "remote",
                "cluster_id": CLUSTER_ID,
                "databases": ["*"],
                "databases_ignore": [],
                "rollback_time": "2025-06-11T23:59:59+08:00",
                "rollback_type": "REMOTE_AND_TIME",
                "tables": ["*"],
                "tables_ignore": [],
                "target_cluster_id": CLUSTER_ID,
            }
        ],
        "rollback_cluster_type": "BUILD_INTO_METACLUSTER",
    },
    "remark": "",
    "ticket_type": "MYSQL_ROLLBACK_CLUSTER",
}

MYSQL_FLASHBACK_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "flashback_type": "TABLE_FLASHBACK",
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "start_time": "2025-06-11T23:59:59+08:00",
                "end_time": "",
                "databases": ["source_test_db1"],
                "tables": ["test_table"],
                "databases_ignore": [],
                "tables_ignore": [],
            }
        ],
    },
    "remark": "",
    "ticket_type": "MYSQL_FLASHBACK",
}

MYSQL_ADD_SLAVE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "backup_source": "remote",
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID],
                "resource_spec": {
                    "new_slave": {
                        "hosts": [{"bk_biz_id": BK_BIZ_ID, "bk_cloud_id": 0, "bk_host_id": 1, "ip": "1.1.2.2"}],
                        "spec_id": 0,
                    }
                },
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "MYSQL_ADD_SLAVE",
}

MYSQL_CHECKSUM_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "data_repair": {"is_repair": True, "mode": "manual"},
        "remark": "",
        "runtime_hour": 48,
        "timing": "2099-05-21T00:00:00+08:00",
        "infos": [
            {
                "cluster_id": CLUSTER_ID,
                "master": {
                    "bk_biz_id": BK_BIZ_ID,
                    "bk_cloud_id": 0,
                    "bk_host_id": 599,
                    "ip": "1.1.3.3",
                    "port": 20000,
                },
                "slaves": [
                    {"bk_biz_id": BK_BIZ_ID, "bk_cloud_id": 0, "bk_host_id": 604, "ip": "1.1.3.5", "port": 20000}
                ],
                "db_patterns": ["source_test_db1"],
                "ignore_dbs": [],
                "table_patterns": ["*"],
                "ignore_tables": [],
            }
        ],
    },
    "remark": "",
    "ticket_type": "MYSQL_CHECKSUM",
}

MYSQL_HA_FULL_BACKUP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "backup_type": "logical",
        "file_tag": "DBFILE1M",
        "infos": [{"cluster_id": CLUSTER_ID, "backup_local": "master"}],
    },
    "remark": "",
    "ticket_type": "MYSQL_HA_FULL_BACKUP",
}

MYSQL_DATA_MIGRATE_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "db_list": ["source_test_db1"],
                "source_cluster": CLUSTER_ID,
                "target_clusters": [99],
                "data_schema_grant": "data,schema",
            }
        ]
    },
    "remark": "",
    "ticket_type": "MYSQL_DATA_MIGRATE",
}

MYSQL_AUTHORIZE_TICKET_DATA = {
    "bk_biz_id": constant.BK_BIZ_ID,
    "details": {
        "authorize_uid": uuid.uuid1().hex,
        "authorize_data": {
            "user": "admin",
            "access_dbs": ["dbnew", "user"],
            "source_ips": [{"ip": "1.1.1.1", "bk_host_id": 1}, {"ip": "2.2.2.2", "bk_host_id": 2}],
            "target_instances": ["gamedb.privtest55.blueking.db"],
            "cluster_type": "tendbha",
        },
    },
    "remark": "",
    "ticket_type": "MYSQL_AUTHORIZE_RULES",
}

MYSQL_FULL_BACKUP_TICKET_DATA = {
    "bk_biz_id": constant.BK_BIZ_ID,
    "details": {
        "backup_type": "logical",
        "file_tag": "DBFILE1M",
        "infos": [{"cluster_id": 1, "backup_local": "master"}],
    },
    "remark": "",
    "ticket_type": "MYSQL_HA_FULL_BACKUP",
}

MYSQL_ITSM_AUTHORIZE_TICKET_DATA = [
    {
        "user": "admin",
        "index": 0,
        "message": "",
        "operator": "admin",
        "bk_biz_id": 3,
        "source_ips": ["127.0.0.1"],
        "cluster_type": "tendbha",
        "account_rules": [{"dbname": "ddddd", "bk_biz_id": 3}],
    }
]

MYSQL_AUTHORIZE_CLONE_CLIENT_TICKET_DATA = {
    "bk_biz_id": constant.BK_BIZ_ID,
    "details": {
        "clone_uid": "80fc459ae1d51xxxx17626xxxb38e5",
        "clone_data_list": [
            {"module": "Test/Server/", "source": "127.0.0.1", "target": ["127.0.0.2"], "bk_cloud_id": 0}
        ],
        "clone_type": "client",
    },
    "remark": "",
    "ticket_type": "MYSQL_CLIENT_CLONE_RULES",
}

MYSQL_CLONE_CLIENT_TICKET_CONFIG = {
    "bk_biz_id": constant.BK_BIZ_ID,
    "ticket_type": TicketType.MYSQL_CLIENT_CLONE_RULES,
    "configs": {"need_itsm": True, "need_manual_confirm": True},
    "editable": 1,
    "group": DBType.MySQL,
}

MYSQL_SINGLE_APPLY_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "remark": "",
    "ticket_type": TicketType.MYSQL_SINGLE_APPLY,
    "details": {
        "ip_source": IpSource.RESOURCE_POOL,
        "bk_cloud_id": 0,
        "city_code": "南京",
        "db_app_abbr": "blueking",
        "spec": "SA2.SMALL4",
        "db_module_id": constant.DB_MODULE_ID,
        "cluster_count": 1,
        "charset": "",
        "mysql_port": 20000,
        "proxy_port": 10000,
        "domains": [{"key": "kio"}],
        "disaster_tolerance_level": "same_city_cross_zone",
        "resource_spec": {
            "backend": {
                "affinity": "NONE",
                "location_spec": {"city": "default", "sub_zone_ids": []},
                "spec_name": "spec_test",
                "spec_id": 1,
                "count": 1,
            }
        },
    },
}

MYSQL_TENDBHA_TICKET_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "ticket_type": TicketType.MYSQL_HA_APPLY,
    "remark": "",
    "details": {
        "bk_cloud_id": 0,
        "city_code": "南京",
        "db_app_abbr": "blueking",
        "spec": "SA2.SMALL4",
        "db_module_id": constant.DB_MODULE_ID,
        "cluster_count": 1,
        "charset": "",
        "mysql_port": 20000,
        "proxy_port": 10000,
        "domains": [{"key": "kio"}],
        "disaster_tolerance_level": "SAME_SUBZONE_CROSS_SWTICH",
        "resource_spec": {
            "proxy": {
                "affinity": "NONE",
                "location_spec": {"city": "default", "sub_zone_ids": []},
                "spec_name": "spec_test",
                "spec_id": 1,
                "count": 1,
            },
            "backend_group": {
                "affinity": "NONE",
                "location_spec": {"city": "default", "sub_zone_ids": []},
                "spec_name": "spec_test",
                "spec_id": 1,
                "count": 1,
            },
        },
    },
}

SQL_IMPORT_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "root_id": ROOT_ID,
        "charset": "default",
        "force": False,
        "path": "/bk-dbm/mysql/sqlfile",
        "cluster_ids": [110],
        "execute_objects": [
            {
                "sql_files": ["bar.sql", "foo.sql"],
                "dbnames": ["db_log%"],
                "ignore_dbnames": ["db1", "db2"],
                "import_mode": "file",
            }
        ],
        "ticket_mode": {"mode": "auto"},
        "backup": [],
        "highrisk_warnings": "",
        "bk_biz_id": BK_BIZ_ID,
        "created_by": "admin",
    },
    "remark": "",
    "ticket_type": "MYSQL_IMPORT_SQLFILE",
}

SQL_IMPORT_TICKET_DATA = {
    "bk_biz_id": constant.BK_BIZ_ID,
    "details": {"root_id": ROOT_ID},
    "remark": "",
    "ticket_type": "MYSQL_IMPORT_SQLFILE",
}

SQL_IMPORT_FLOW_NODE_DATA = {
    "uid": 1,
    "root_id": ROOT_ID,
    "node_id": SQL_IMPORT_NODE_ID,
    "version_id": SQL_IMPORT_VERSION_ID,
    "status": StateType.FINISHED.value,
}

MYSQL_DUMP_DATA = {
    "ticket_type": "MYSQL_DUMP_DATA",
    "bk_biz_id": constant.BK_BIZ_ID,
    "details": {
        "cluster_id": 1,
        "charset": "utf8",
        "databases": ["mytest"],
        "tables": ["*"],
        "dump_data": True,
        "dump_schema": True,
    },
}

MYSQL_PROXY_ADD_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID],
                "resource_spec": {
                    "new_proxy": {
                        "hosts": [{"bk_biz_id": BK_BIZ_ID, "bk_cloud_id": 0, "bk_host_id": 182, "ip": "5.5.5.4"}],
                        "spec_id": 0,
                    }
                },
            }
        ],
        "ip_source": "resource_pool",
    },
    "remark": "",
    "ticket_type": "MYSQL_PROXY_ADD",
}

MYSQL_MASTER_SLAVE_SWITCH_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID],
                "master_ip": {"ip": "5.5.5.5", "bk_host_id": 552, "bk_cloud_id": 0, "bk_biz_id": BK_BIZ_ID},
                "slave_ip": {"ip": "5.5.5.3", "bk_host_id": 556, "bk_cloud_id": 0, "bk_biz_id": BK_BIZ_ID},
            }
        ],
        "is_check_process": False,
        "is_check_delay": False,
        "is_verify_checksum": False,
    },
    "remark": "",
    "ticket_type": "MYSQL_MASTER_SLAVE_SWITCH",
}

MYSQL_PROXY_SWITCH_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "force": True,
        "infos": [
            {
                "cluster_ids": [CLUSTER_ID],
                "old_nodes": {
                    "origin_proxy": [
                        {
                            "bk_biz_id": BK_BIZ_ID,
                            "bk_cloud_id": 0,
                            "bk_host_id": 446,
                            "instance_address": "5.5.5.6:20001",
                            "ip": "5.5.5.6",
                            "port": 20001,
                        }
                    ]
                },
                "resource_spec": {
                    "target_proxy": {
                        "hosts": [{"bk_biz_id": BK_BIZ_ID, "bk_cloud_id": 0, "bk_host_id": 447, "ip": "5.5.5.7"}]
                    }
                },
            }
        ],
        "ip_source": "resource_pool",
        "opera_object": "instance",
    },
    "ignore_duplication": True,
    "remark": "",
    "ticket_type": "MYSQL_PROXY_SWITCH",
}

MYSQL_CLUSTER_DATA = [
    {
        "id": CLUSTER_ID,
        "creator": BK_USERNAME,
        "updater": BK_USERNAME,
        "name": "fre4",
        "alias": "",
        "bk_biz_id": BK_BIZ_ID,
        "cluster_type": ClusterType.TenDBHA,
        "db_module_id": 2,
        "immute_domain": "tendbha57db.fre4.dba.db",
        "major_version": "MySQL-5.7",
        "phase": "online",
        "status": "normal",
        "bk_cloud_id": 0,
        "region": "default",
        "time_zone": "+08:00",
        "disaster_tolerance_level": "NONE",
    },
    {
        "id": 99,
        "creator": BK_USERNAME,
        "updater": BK_USERNAME,
        "name": "9527",
        "alias": "",
        "bk_biz_id": BK_BIZ_ID,
        "cluster_type": ClusterType.TenDBSingle,
        "db_module_id": 1,
        "immute_domain": "test1db.9527.1.db",
        "major_version": "MySQL-5.7",
        "phase": "online",
        "status": "normal",
        "bk_cloud_id": 0,
        "region": "default",
        "time_zone": "+08:00",
        "disaster_tolerance_level": "NONE",
    },
]

MYSQL_PROXYINSTANCE_DATA = [
    {
        "id": 369,
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
        "machine_type": "proxy",
        "cluster_type": "tendbha",
        "status": "running",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 11553,
        "machine_id": 446,
        "phase": "online",
    },
]

MYSQL_STORAGE_INSTANCE = [
    {
        "id": 935,
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "version": "5.7.20",
        "port": 20001,
        "machine_id": 552,
        "db_module_id": 2,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": "backend",
        "instance_role": "backend_master",
        "instance_inner_role": "master",
        "cluster_type": "tendbha",
        "status": "running",
        "phase": "online",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7878,
        "is_stand_by": "1",
    },
    {
        "id": 936,
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "version": "5.7.20",
        "port": 20001,
        "machine_id": 556,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": "backend",
        "instance_role": "backend_slave",
        "instance_inner_role": "slave",
        "cluster_type": "tendbha",
        "status": "running",
        "phase": "online",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 7879,
        "is_stand_by": "1",
    },
    {
        "id": 966,
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "version": "5.7.20",
        "port": 20001,
        "machine_id": 182,
        "db_module_id": 0,
        "bk_biz_id": BK_BIZ_ID,
        "access_layer": "storage",
        "machine_type": "single",
        "instance_role": "orphan",
        "instance_inner_role": "orphan",
        "cluster_type": "tendbsingle",
        "status": "running",
        "phase": "online",
        "name": "",
        "time_zone": "+08:00",
        "bk_instance_id": 6272,
        "is_stand_by": "1",
    },
]

MYSQL_MACHINE_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "5.5.5.6",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": MachineType.PROXY.value,
        "cluster_type": ClusterType.TenDBHA,
        "bk_host_id": 446,
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
        "spec_id": 444,
        "bk_agent_id": "",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "5.5.5.7",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "proxy",
        "machine_type": MachineType.PROXY.value,
        "cluster_type": ClusterType.TenDBHA,
        "bk_host_id": 447,
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
        "spec_id": 444,
        "bk_agent_id": "",
    },
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "ip": "5.5.5.5",
        "bk_biz_id": BK_BIZ_ID,
        "db_module_id": 0,
        "access_layer": "storage",
        "machine_type": MachineType.BACKEND.value,
        "cluster_type": ClusterType.TenDBHA,
        "bk_host_id": 552,
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
        "spec_id": 445,
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
        "access_layer": "storage",
        "machine_type": MachineType.BACKEND.value,
        "cluster_type": ClusterType.TenDBHA,
        "bk_host_id": 556,
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
        "spec_id": 444,
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
        "machine_type": MachineType.SINGLE.value,
        "cluster_type": ClusterType.TenDBSingle,
        "bk_host_id": 182,
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
        "spec_id": 336,
        "bk_agent_id": "",
    },
]

MYSQL_SPEC_DATA = [
    {
        "creator": BK_USERNAME,
        "create_at": "2024-03-13 11:14:48.433116",
        "updater": "",
        "update_at": "2024-03-13 11:14:48.433116",
        "spec_id": 444,
        "spec_name": "无限制",
        "spec_cluster_type": "mysql",
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
        "spec_id": 445,
        "spec_name": "2c_4g_50g",
        "spec_cluster_type": "mysql",
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
        "spec_id": 336,
        "spec_name": "无限制",
        "spec_cluster_type": "mysql",
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
