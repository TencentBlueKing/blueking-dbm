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

from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import MySQLDownloadBackupfile
from backend.flow.utils.sqlserver.payload_handler import PayloadHandler

logger = logging.getLogger("flow")


class SqlserverDownloadBackupFile(MySQLDownloadBackupfile):
    """
    sqlserver 完整备份文件下载，通过备份系统
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        # 获取mssql账号密码
        mssql_user, mssql_pwd = PayloadHandler.get_download_backup_file_user()

        # 获取备份信息
        backup_file_infos = getattr(trans_data, kwargs["get_backup_file_info_var"])

        # 判断传入文件组是否为空，如果为空则报异常
        if not isinstance(backup_file_infos, list) or len(backup_file_infos) == 0:
            raise Exception(
                f"an exception was detected when obtaining backup information from trans_data"
                f"get_backup_file_info_var:[{kwargs['get_backup_file_info_var']}]"
            )

        # 获取需要下载的文件
        taskid_list = []
        for info in backup_file_infos:
            if not info["is_in_local"]:
                # 如果文件不在本地，则在备份系统拉取
                self.log_info(f"download file [{info['file_name']}] from backup system")
                taskid_list.append(info["task_id"])
            else:
                self.log_info(f" file [{info['file_name']}] is in local, skip")

        # 如果需要下载的文件列表为空，则直接返回
        if len(taskid_list) == 0:
            self.log_info("no file download for backup system")
            data.outputs.skip_result = True
            return True

        # 拼接下载参数
        data.get_one_of_inputs("kwargs")["bk_cloud_id"] = kwargs["bk_cloud_id"]
        data.get_one_of_inputs("kwargs")["task_ids"] = taskid_list
        data.get_one_of_inputs("kwargs")["dest_ip"] = kwargs["dest_ip"]
        data.get_one_of_inputs("kwargs")["dest_dir"] = kwargs["dest_dir"]
        data.get_one_of_inputs("kwargs")["login_user"] = mssql_user
        data.get_one_of_inputs("kwargs")["login_passwd"] = mssql_pwd
        data.get_one_of_inputs("kwargs")["reason"] = "[dbm] sqlserver download backup files"

        # 执行父类execute函数，下载文件
        return super()._execute(data, parent_data)

    def _schedule(self, data, parent_data, callback_data=None):
        skip_result = data.get_one_of_outputs("skip_result")
        if skip_result:
            self.finish_schedule()
            return True

        return super()._schedule(data, parent_data)


class SqlserverDownloadBackupFileComponent(Component):
    name = __name__
    code = "sqlserver_Download_backup_file"
    bound_service = SqlserverDownloadBackupFile
