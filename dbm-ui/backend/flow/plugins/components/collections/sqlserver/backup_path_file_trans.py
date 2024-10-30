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
from pathlib import PureWindowsPath

from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsService
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import SqlserverBackupIDContext
from backend.flow.utils.sqlserver.sqlserver_db_function import get_backup_path_files

logger = logging.getLogger("flow")


class SqlserverTransBackupFileFor2P2Service(TransFileInWindowsService):
    """
    sqlserver 点对点传输备份文件
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        file_list = []

        # 获取备份ID
        if kwargs["is_trans_full_backup"]:
            full_backup_id = getattr(trans_data, SqlserverBackupIDContext.full_backup_id_var_name())["id"]
            if not full_backup_id:
                raise Exception(f"full backup id is null: full_backup_id:{full_backup_id}")

            full_backup_files = [
                str(PureWindowsPath(i["PATH"]) / i["FILENAME"])
                for i in get_backup_path_files(cluster_id=kwargs["cluster_id"], backup_id=full_backup_id)
            ]
            file_list += full_backup_files

        if kwargs["is_trans_log_backup"]:
            log_backup_id = getattr(trans_data, SqlserverBackupIDContext.log_backup_id_var_name())["id"]
            if not log_backup_id:
                raise Exception(f"log backup id is null: log_backup_id:{log_backup_id}")

            log_backup_files = [
                str(PureWindowsPath(i["PATH"]) / i["FILENAME"])
                for i in get_backup_path_files(cluster_id=kwargs["cluster_id"], backup_id=log_backup_id)
            ]
            file_list += log_backup_files

        if len(file_list) == 0:
            raise Exception(
                f"file_list is null, check: {getattr(trans_data, SqlserverBackupIDContext.full_backup_id_var_name())}"
            )

        # 拼接下载参数
        data.get_one_of_inputs("kwargs")["file_list"] = file_list

        # 执行父类execute函数，传输文件
        return super()._execute(data, parent_data)


class SqlserverTransBackupFileFor2P2Component(Component):
    name = __name__
    code = "sqlserver_trans_backup_file_for_2p2"
    bound_service = SqlserverTransBackupFileFor2P2Service
