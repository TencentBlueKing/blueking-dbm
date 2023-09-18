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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.mysql.import_sqlfile_flow import ImportSQLFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_authorize_rules import MySQLAuthorizeRules
from backend.flow.engine.bamboo.scene.mysql.mysql_checksum import MysqlChecksumFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_clone_rules import MySQLCloneRules
from backend.flow.engine.bamboo.scene.mysql.mysql_edit_config_flow import MysqlEditConfigFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_fake_sql_semantic_check import MySQLFakeSemanticCheck
from backend.flow.engine.bamboo.scene.mysql.mysql_flashback_flow import MysqlFlashbackFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_apply_flow import MySQLHAApplyFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_db_table_backup import MySQLHADBTableBackupFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_destroy_flow import MySQLHADestroyFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_disable_flow import MySQLHADisableFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_enable_flow import MySQLHAEnableFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_full_backup_flow import MySQLHAFullBackupFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_standardize_flow import MySQLHAStandardizeFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_master_fail_over import MySQLMasterFailOverFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_master_slave_switch import MySQLMasterSlaveSwitchFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_migrate_cluster_flow import MySQLMigrateClusterFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_migrate_cluster_remote_flow import MySQLMigrateClusterRemoteFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_open_area_flow import MysqlOpenAreaFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_partition import MysqlPartitionFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_proxy_cluster_add import MySQLProxyClusterAddFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_proxy_cluster_switch import MySQLProxyClusterSwitchFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_rename_database_flow import MySQLRenameDatabaseFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_restore_slave_flow import MySQLRestoreSlaveFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_restore_slave_remote_flow import MySQLRestoreSlaveRemoteFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_data_flow import MySQLRollbackDataFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_single_apply_flow import MySQLSingleApplyFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_single_destroy_flow import MySQLSingleDestroyFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_single_disable_flow import MySQLSingleDisableFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_single_enable_flow import MySQLSingleEnableFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_truncate_flow import MySQLTruncateFlow
from backend.flow.engine.bamboo.scene.mysql.pt_table_sync import PtTableSyncFlow
from backend.flow.engine.controller.base import BaseController


class MySQLController(BaseController):
    """
    mysql实例相关调用
    """

    def mysql_single_apply_scene(self):
        """
        部署tenDB(mysql)单实例场景(新flow编排)
        """
        flow = MySQLSingleApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_mysql_single_flow_with_manual()

    def mysql_restore_slave_scene(self):
        """
        tenDB slave 恢复流程编排
        """
        flow = MySQLRestoreSlaveFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_restore_slave_flow()

    def mysql_add_slave_scene(self):
        """
        仅添加 slave 流程编排
        """
        flow = MySQLRestoreSlaveFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_add_slave_flow()

    def mysql_restore_local_slave_scene(self):
        """
        tenDB slave 原地恢复流程编排
        """
        flow = MySQLRestoreSlaveFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_restore_local_slave_flow()

    #  mysql 从节点恢复(接入备份系统)
    def mysql_restore_slave_remote_scene(self):
        """
        tenDB slave 恢复流程编排
        """
        flow = MySQLRestoreSlaveRemoteFlow(root_id=self.root_id, tick_data=self.ticket_data)
        flow.tendb_ha_restore_slave_flow()

    def mysql_add_slave_remote_scene(self):
        """
        仅添加 slave 流程编排
        """
        self.ticket_data["add_slave_only"] = True
        flow = MySQLRestoreSlaveRemoteFlow(root_id=self.root_id, tick_data=self.ticket_data)
        flow.tendb_ha_restore_slave_flow()

    def mysql_restore_local_remote_scene(self):
        """
        tenDB slave 原地恢复流程编排
        """
        flow = MySQLRestoreSlaveRemoteFlow(root_id=self.root_id, tick_data=self.ticket_data)
        flow.restore_local_slave_flow()

    def mysql_ha_apply_scene(self):
        """
        部署tenDB(mysql) HA集群场景(新flow编排)
        """
        flow = MySQLHAApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_mysql_ha_flow_with_manual()

    def mysql_ha_destroy_scene(self):
        """
            下架tenDB(mysql) HA集群场景(新flow编排)
            ticket_data 参数结构体样例
            {
            "uid": "2022051612120001",
            "creator": "xxx",
            "bk_biz_id": "152",
            "force": ture/false,
            "ticket_type": "MYSQL_HA_DESTROY",
            "cluster_ids": [1,2,3]
        }
        """
        flow = MySQLHADestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_mysql_ha_flow()

    def mysql_ha_disable_scene(self):
        """
            禁用tenDB(mysql) HA集群场景(新flow编排)
            ticket_data 参数结构体样例
            {
            "uid": "2022051612120001",
            "creator": "xxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_HA_DISABLE",
            "cluster_ids": [1,2,3]
        }
        """
        flow = MySQLHADisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_mysql_ha_flow()

    def mysql_ha_enable_scene(self):
        """
            启动tenDB(mysql) HA集群场景(新flow编排)，针对已被禁用的集群
            ticket_data 参数结构体样例
            {
            "uid": "2022051612120001",
            "creator": "xxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_HA_ENABLE",
            "cluster_ids": [1,2,3]
        }
        """
        flow = MySQLHAEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_mysql_ha_flow()

    def mysql_single_destroy_scene(self):
        """
            下架tenDB(mysql) single集群场景(新flow编排)，针对已被禁用的集群
            ticket_data 参数结构体样例
            {
            "uid": "2022051612120001",
            "creator": "xxx",
            "bk_biz_id": "152",
            "force": ture/false,
            "ticket_type": "MYSQL_SINGLE_DESTROY",
            "cluster_ids": [1,2,3]
        }
        """
        flow = MySQLSingleDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_mysql_single_flow()

    def mysql_single_disable_scene(self):
        """
            禁用tenDB(mysql) single集群场景(新flow编排)
            ticket_data 参数结构体样例
            {
            "uid": "2022051612120001",
            "creator": "xxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_SINGLE_DISABLE",
            "cluster_ids": [1,2,3]
        }
        """
        flow = MySQLSingleDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_mysql_single_flow()

    def mysql_single_enable_scene(self):
        """
            启动tenDB(mysql) single集群场景(新flow编排)， 针对已被禁用的集群
            ticket_data 参数结构体样例
            {
            "uid": "2022051612120001",
            "creator": "xxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_SINGLE_ENABLE",
            "cluster_ids": [1,2,3]
        }
        """
        flow = MySQLSingleEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_mysql_single_flow()

    def mysql_authorize_rules(self):
        """授权mysql权限场景"""

        flow = MySQLAuthorizeRules(root_id=self.root_id, data=self.ticket_data)
        flow.authorize_mysql_rules()

    def mysql_clone_rules(self):
        """
        权限克隆mysql场景：
        - 实例间权限克隆
        - 客户端权限克隆
        """

        flow = MySQLCloneRules(root_id=self.root_id, data=self.ticket_data)
        flow.clone_mysql_rules()

    def mysql_proxy_add_scene(self):
        """
        添加mysql_proxy实例场景(新flow编排)
        ticket_data 参数结构体样例
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_PROXY_ADD",
        "add_infos": [
              {
                "cluster_ids": [1,2,3],
                "proxy_ip": "1.1.1.1"
              },
              {
                "cluster_ids": [4,5,6],
                "proxy_ip": "2.2.2.2"
              }
        ]
        }
        """

        flow = MySQLProxyClusterAddFlow(root_id=self.root_id, data=self.ticket_data)
        flow.add_mysql_cluster_proxy_flow()

    def mysql_ha_truncate_data_scene(self):
        """
        TenDBHA 清档
        ticket_data 参数结构体样例
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_HA_TRUNCATE_DATA",
        "infos": [
            {
                "cluster_id": str,
                "db_patterns": ["db1%", "db2%"],
                "ignore_dbs": ["db11", "db12", "db23"],
                "table_patterns": ["tb_role%", "tb_mail%", "*"],
                "ignore_tables": ["tb_role1", "tb_mail10"],
                "truncate_data_type": "drop_database"
                "force": ture/false
            },
            ...
            ...
            ]
        }

        truncate_data_type 为枚举的 value

        class TruncateDataTypeEnum(str, StructuredEnum):
            TRUNCATE_TABLE = EnumField('truncate_table', _('truncate_table'))
            DROP_DATABASE = EnumField('drop_database', _('drop_database'))
            DROP_TABLE = EnumField('drop_table', _('drop_table'))
        """

        flow = MySQLTruncateFlow(root_id=self.root_id, data=self.ticket_data, cluster_type=ClusterType.TenDBHA.value)
        flow.truncate_flow()

    def mysql_proxy_switch_scene(self):
        """
        上架mysql_proxy实例场景(新flow编排)
        ticket_data 参数结构体样例
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "force": false,
        "ticket_type": "MYSQL_PROXY_SWITCH",
        "switch_infos": [
              {
                "cluster_ids": [1,2,3],
                "origin_proxy_ip":"1.1.1.1",
                "target_proxy_ip":"2.2.2.2"
              },
              {
                "cluster_ids": [4,5,6]
                "origin_proxy_ip":"3.3.3.3",
                "target_proxy_ip":"4.4.4.4"
              }
        ]
        }
        """
        flow = MySQLProxyClusterSwitchFlow(root_id=self.root_id, data=self.ticket_data)
        flow.switch_mysql_cluster_proxy_flow()

    def mysql_import_sqlfile_scene(self):
        flow = ImportSQLFlow(root_id=self.root_id, data=self.ticket_data)
        flow.import_sqlfile_flow()

    def mysql_sql_semantic_check_scene(self):
        """
        SQL语义检查场景
        """
        flow = ImportSQLFlow(root_id=self.root_id, data=self.ticket_data)
        flow.sql_semantic_check_flow()

    def mysql_checksum(self):
        """
        mysql 数据校验
        """
        flow = MysqlChecksumFlow(root_id=self.root_id, data=self.ticket_data)
        flow.mysql_checksum_flow()

    def mysql_partition(self):
        """
        mysql 表分区
        """
        flow = MysqlPartitionFlow(root_id=self.root_id, data=self.ticket_data)
        flow.mysql_partition_flow()

    def mysql_fake_sql_semantic_check_scene(self):
        """
        测试专用，模拟SQL语义检查场景
        """
        flow = MySQLFakeSemanticCheck(root_id=self.root_id, data=self.ticket_data)
        flow.fake_semantic_check()

    def mysql_ha_rename_database_scene(self):
        """
        TenDBHA 重命名数据库
        ticket_data 参数结构体样例
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_HA_RENAME_DATABASE",
        "infos": [
            {
                "cluster_id": int,
                "from_database": str,
                "to_database": str
                "force": bool
            },
            ...
            ...
            ]
        }
        """
        flow = MySQLRenameDatabaseFlow(
            root_id=self.root_id, data=self.ticket_data, cluster_type=ClusterType.TenDBHA.value
        )
        flow.rename_database()

    def mysql_migrate_cluster_scene(self):
        """
        主从成对迁移flow编排
        """
        flow = MySQLMigrateClusterFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_migrate_cluster_flow()

    def mysql_migrate_remote_scene(self):
        """
        主从成对迁移flow编排
        """
        flow = MySQLMigrateClusterRemoteFlow(root_id=self.root_id, data=self.ticket_data)
        flow.migrate_cluster_flow()

    def mysql_ha_db_table_backup_scene(self):
        """
        TenDBHA 库表备份
        ticket_data 参数结构样例
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_HA_DB_TABLE_BACKUP",
        "infos": [
            {
                "cluster_id": int,
                "backup_on": str enum InstanceInnerRole
                "db_patterns": ["db1%", "db2%"],
                "ignore_dbs": ["db11", "db12", "db23"],
                "table_patterns": ["tb_role%", "tb_mail%", "*"],
                "ignore_tables": ["tb_role1", "tb_mail10"],
            },
            ...
            ...
        ]
        }
        """
        flow = MySQLHADBTableBackupFlow(root_id=self.root_id, data=self.ticket_data)
        flow.backup_flow()

    def mysql_ha_switch_scene(self):
        """
        mysql主从切换单据场景（整机切换）
        ticket_data 参数结构体样例
        {
            "uid": "2022051612120001",
            "create_by": "xxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_MASTER_SLAVE_SWITCH",
            "infos":[
              "cluster_ids": [1,2,3],
              "master_ip": {"ip":"1.1.1.1", "bk_cloud_id": 0},
              "slave_ip": {"ip":"2.2.2.2", "bk_cloud_id": 0},
              "is_safe": ture
            ]
        }
        """
        flow = MySQLMasterSlaveSwitchFlow(root_id=self.root_id, data=self.ticket_data)
        flow.master_slave_switch_flow()

    def mysql_ha_master_fail_over_scene(self):
        """
        mysql主库故障切换单据场景（整机切换）
        ticket_data 参数结构体样例
        {
            "uid": "2022051612120001",
            "create_by": "xxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_MASTER_FAIL_OVER",
            "switch_infos":[
              "cluster_ids": [1,2,3],
              "master_ip": {"ip":"1.1.1.1", "bk_cloud_id": 0},
              "slave_ip": {"ip":"2.2.2.2", "bk_cloud_id": 0},
              "is_safe": ture
            ]
        }
        """
        flow = MySQLMasterFailOverFlow(root_id=self.root_id, data=self.ticket_data)
        flow.master_fail_over_flow()

    def mysql_rollback_data_cluster_scene(self):
        """
        数据定点回档
        """
        flow = MySQLRollbackDataFlow(root_id=self.root_id, data=self.ticket_data)
        flow.rollback_data_flow()

    def mysql_pt_table_sync_scene(self):
        """
        mysql数据修复场景
        """
        flow = PtTableSyncFlow(root_id=self.root_id, data=self.ticket_data)
        flow.exec_pt_table_sync_flow()

    def mysql_flashback_scene(self):
        flow = MysqlFlashbackFlow(root_id=self.root_id, data=self.ticket_data)
        flow.mysql_flashback_flow()

    def mysql_full_backup_scene(self):
        flow = MySQLHAFullBackupFlow(root_id=self.root_id, data=self.ticket_data)
        flow.full_backup_flow()

    def mysql_edit_config_scene(self):
        flow = MysqlEditConfigFlow(root_id=self.root_id, data=self.ticket_data)
        flow.mysql_edit_config_flow()

    def mysql_single_truncate_data_scene(self):
        """
        TenDBSingle 清档
        ticket_data 参数结构体样例
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_SINGLE_TRUNCATE_DATA",
        "infos": [
            {
                "cluster_id": str,
                "db_patterns": ["db1%", "db2%"],
                "ignore_dbs": ["db11", "db12", "db23"],
                "table_patterns": ["tb_role%", "tb_mail%", "*"],
                "ignore_tables": ["tb_role1", "tb_mail10"],
                "truncate_data_type": "drop_database"
                "force": ture/false
            },
            ...
            ...
            ]
        }

        truncate_data_type 为枚举的 value

        class TruncateDataTypeEnum(str, StructuredEnum):
            TRUNCATE_TABLE = EnumField('truncate_table', _('truncate_table'))
            DROP_DATABASE = EnumField('drop_database', _('drop_database'))
            DROP_TABLE = EnumField('drop_table', _('drop_table'))
        """

        flow = MySQLTruncateFlow(
            root_id=self.root_id, data=self.ticket_data, cluster_type=ClusterType.TenDBSingle.value
        )
        flow.truncate_flow()

    def mysql_single_rename_database_scene(self):
        """
        TenDBHA 重命名数据库
        ticket_data 参数结构体样例
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_SINGLE_RENAME_DATABASE",
        "infos": [
            {
                "cluster_id": int,
                "from_database": str,
                "to_database": str
                "force": bool
            },
            ...
            ...
            ]
        }
        """
        flow = MySQLRenameDatabaseFlow(
            root_id=self.root_id, data=self.ticket_data, cluster_type=ClusterType.TenDBSingle.value
        )
        flow.rename_database()

    def mysql_ha_standardize_scene(self):
        flow = MySQLHAStandardizeFlow(root_id=self.root_id, data=self.ticket_data)
        flow.standardize()

    def mysql_open_area_scene(self):
        flow = MysqlOpenAreaFlow(root_id=self.root_id, data=self.ticket_data)
        flow.mysql_open_area_flow()
