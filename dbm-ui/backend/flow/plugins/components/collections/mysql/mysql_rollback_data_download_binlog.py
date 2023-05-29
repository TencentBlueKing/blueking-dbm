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
import logging

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import TenDBGetBackupInfoFailedException
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import MySQLDownloadBackupfile
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


class MySQLRollbackDownloadBinlog(MySQLDownloadBackupfile):
    """
    MySQL下载备份文件
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(60)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        self.log_info(kwargs)
        self.log_info(trans_data)
        cluster = kwargs["cluster"]
        backup_time = trans_data.backupinfo["backup_time"]
        rollback_time = cluster["rollback_time"]
        self.log_info("backup time is {}".format(backup_time))
        self.log_info("rollback time is {}".format(rollback_time))
        # 查询binlog
        rollback_handler = FixPointRollbackHandler(cluster["cluster_id"])
        backup_binlog = rollback_handler.query_binlog_from_bklog(
            start_time=str2datetime(backup_time),
            end_time=str2datetime(rollback_time),
            minute_range=30,
            host_ip=cluster["master_ip"],
            port=cluster["master_port"],
        )
        self.log_info(backup_binlog)

        if backup_binlog is None:
            raise TenDBGetBackupInfoFailedException(message=_("获取实例 {} 的备份信息失败".format(cluster["master_ip"])))

        binlog_files_list = [i["file_name"] for i in backup_binlog["file_list_details"]]
        kwargs["task_ids"] = [i["task_id"] for i in backup_binlog["file_list_details"]]
        trans_data.binlog_files_list = binlog_files_list
        trans_data.binlog_files = ",".join(binlog_files_list)
        trans_data.backup_time = backup_time
        # trans_data["binlog_files_list"] = binlog_files_list
        # trans_data["binlog_files"] = ",".join(binlog_files_list)
        self.log_info(kwargs)
        data.outputs["kwargs"] = kwargs
        data.outputs["trans_data"] = trans_data
        return super()._execute(data, parent_data)


class MySQLRollbackDownloadBinlogComponent(Component):
    name = __name__
    code = "rollback_download_binlog"
    bound_service = MySQLRollbackDownloadBinlog
