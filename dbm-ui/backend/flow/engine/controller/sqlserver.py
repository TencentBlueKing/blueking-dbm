"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.bamboo.scene.sqlserver.build_database_sync import SqlserverBuildDBSyncFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_add_slave import SqlserverAddSlaveFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_authorize_rules import SQLServerAuthorizeRules
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_backup_dbs import SqlserverBackupDBSFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_clean_dbs import SqlserverCleanDBSFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_destroy import SqlserverDestroyFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_disable import SqlserverDisableFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_enable import SqlserverEnableFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_migrate import SqlserverClusterMigrateFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_reset import SqlserverResetFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_standardization import SqlserverStandardizationFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_data_export import SqlserverDataExportFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_db_construct import SqlserverDataConstruct
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_dts import SqlserverDTSFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_ha_deploy import SqlserverHAApplyFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_inst_modify_status import SqlserverModifyStatusFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_master_slave_failover import SqlserverFailOverFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_master_slave_switch import SqlserverSwitchFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_rename_dbs import SqlserverRenameDBSFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_single_deploy import SqlserverSingleApplyFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_slave_rebuild import SqlserverSlaveRebuildFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_sql_execute import SqlserverSQLExecuteFlow
from backend.flow.engine.bamboo.scene.sqlserver.validate.sqlserver_cluster_migrate_for_ins_validator import (
    SqlserverClusterMigrateForInsFlowValidator,
)
from backend.flow.engine.bamboo.scene.sqlserver.validate.sqlserver_cluster_migrate_validator import (
    SqlserverClusterMigrateFlowForHostValidator,
)
from backend.flow.engine.bamboo.scene.sqlserver.validate.sqlserver_data_export_validator import (
    SqlserverDataExportValidator,
)
from backend.flow.engine.bamboo.scene.sqlserver.validate.sqlserver_db_construct_validator import (
    SqlserverDBConstructValidator,
)
from backend.flow.engine.bamboo.scene.sqlserver.validate.sqlserver_db_rollback_in_local_validator import (
    SqlserverDBRollbackInLocalValidator,
)
from backend.flow.engine.controller.base import BaseController
from backend.flow.engine.validate.base_validate import validates_with


class SqlserverController(BaseController):
    """
    sqlserver 相关调用
    """

    def single_cluster_apply_scene(self):
        flow = SqlserverSingleApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def ha_cluster_apply_scene(self):
        flow = SqlserverHAApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def sql_file_execute_scene(self):
        flow = SqlserverSQLExecuteFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def backup_dbs_scene(self):
        flow = SqlserverBackupDBSFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def rename_dbs_scene(self):
        flow = SqlserverRenameDBSFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def clean_dbs_scene(self):
        flow = SqlserverCleanDBSFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def ha_switch_scene(self):
        flow = SqlserverSwitchFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def ha_fail_over_scene(self):
        flow = SqlserverFailOverFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def ha_build_db_sync_scene(self):
        flow = SqlserverBuildDBSyncFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def cluster_disable_scene(self):
        flow = SqlserverDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def cluster_enable_scene(self):
        flow = SqlserverEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def cluster_reset_scene(self):
        flow = SqlserverResetFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def cluster_destroy_scene(self):
        flow = SqlserverDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def add_slave_scene(self):
        flow = SqlserverAddSlaveFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def slave_rebuild_in_local_scene(self):
        flow = SqlserverSlaveRebuildFlow(root_id=self.root_id, data=self.ticket_data)
        flow.slave_rebuild_in_local_flow()

    def slave_rebuild_in_new_slave_scene(self):
        flow = SqlserverSlaveRebuildFlow(root_id=self.root_id, data=self.ticket_data)
        flow.slave_rebuild_in_new_slave_flow()

    def full_dts_scene(self):
        flow = SqlserverDTSFlow(root_id=self.root_id, data=self.ticket_data)
        flow.full_dts_flow_v2()

    def incr_dts_scene(self):
        flow = SqlserverDTSFlow(root_id=self.root_id, data=self.ticket_data)
        flow.incr_dts_flow_v2()

    # 指定目标集群构造数据
    @validates_with(SqlserverDBConstructValidator)
    def db_construct_scene(self):
        flow = SqlserverDataConstruct(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    # 原地回档数据
    @validates_with(SqlserverDBRollbackInLocalValidator)
    def db_rollback_in_local_scene(self):
        flow = SqlserverDataConstruct(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def authorize(self):
        flow = SQLServerAuthorizeRules(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def sqlserver_standardization_scene(self):
        flow = SqlserverStandardizationFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    def sqlserver_modify_inst_status_scene(self):
        # 实例告警自愈触发单据
        flow = SqlserverModifyStatusFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    @validates_with(SqlserverClusterMigrateFlowForHostValidator)
    def sqlserver_cluster_migrate_for_host_scene(self):
        # 集群迁移流程单据(整机迁移)
        flow = SqlserverClusterMigrateFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    @validates_with(SqlserverClusterMigrateForInsFlowValidator)
    def sqlserver_cluster_migrate_for_ins_scene(self):
        # 集群迁移流程单据(集群迁移拆分)
        flow = SqlserverClusterMigrateFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()

    @validates_with(SqlserverDataExportValidator)
    def sqlserver_data_export_scene(self):
        # 数据导出单据flow
        flow = SqlserverDataExportFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()
