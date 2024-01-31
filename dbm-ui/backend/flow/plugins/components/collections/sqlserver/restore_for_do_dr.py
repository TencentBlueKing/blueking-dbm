"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging

from pipeline.component_framework.component import Component

from backend.flow.consts import SqlserverRestoreMode
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptService
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import get_backup_info_in_master

logger = logging.getLogger("flow")

sync_payload_func_map = {
    SqlserverRestoreMode.FULL: SqlserverActPayload.get_restore_full_dbs_payload.__name__,
    SqlserverRestoreMode.LOG: SqlserverActPayload.get_restore_log_dbs_payload.__name__,
}


class RestoreForDoDrService(SqlserverActuatorScriptService):
    """
    根据Sqlserver做dr的场景，数据库级别建立同步，做恢复数据在slave
    逻辑：
    1：在master本地备份表查询这次流程的产生的备份信息，根据传入的backup_id 以及 同步的数据库列表
    2：拼接参数，做恢复操作
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        restore_dbs = []
        restore_infos = []

        for db_name in kwargs["restore_dbs"]:
            self.log_info(f"checking db:[{db_name}]")

            backup_info = get_backup_info_in_master(
                cluster_id=kwargs["cluster_id"],
                backup_id=kwargs["backup_id"],
                db_name=db_name,
                backup_type=kwargs["restore_mode"],
            )
            if len(backup_info) == 0:
                self.log_warning(f"the database [{db_name}] is not backup-infos ")
                continue

            restore_dbs.append(db_name)
            if kwargs["restore_mode"] == SqlserverRestoreMode.LOG:
                bak_file = [backup_info[0]["backup_file"]]
            else:
                bak_file = backup_info[0]["backup_file"]

            restore_infos.append({"db_name": db_name, "target_db_name": db_name, "bak_file": bak_file})

        if len(restore_dbs) == 0:
            raise Exception("not dbs restore, check")

        # 拼接恢复参数
        data.get_one_of_inputs("kwargs")["get_payload_func"] = sync_payload_func_map[kwargs["restore_mode"]]
        data.get_one_of_inputs("kwargs")["custom_params"] = {
            "restore_infos": restore_infos,
            "restore_mode": "NORECOVERY",
        }

        return super()._execute(data, parent_data)


class RestoreForDoDrComponent(Component):
    name = __name__
    code = "sqlserver_restore_for_do_dr"
    bound_service = RestoreForDoDrService
