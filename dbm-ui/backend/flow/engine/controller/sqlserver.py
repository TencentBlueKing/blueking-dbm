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
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_backup_dbs import SqlserverBackupDBSFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_clean_dbs import SqlserverCleanDBSFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_destroy import SqlserverDestroyFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_disable import SqlserverDisableFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_enable import SqlserverEnableFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_cluster_reset import SqlserverResetFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_ha_deploy import SqlserverHAApplyFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_master_slave_failover import SqlserverFailOverFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_master_slave_switch import SqlserverSwitchFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_rename_dbs import SqlserverRenameDBSFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_single_deploy import SqlserverSingleApplyFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_slave_rebuild import SqlserverSlaveRebuildFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_sql_execute import SqlserverSQLExecuteFlow
from backend.flow.engine.controller.base import BaseController


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
