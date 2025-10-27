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

from pipeline.component_framework.component import Component

from backend.db_report.mysql_backup.handers import MySQLBackupHandler
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileService
from backend.ticket.builders.common.constants import MySQLBackupSource

logger = logging.getLogger("flow")


class TransFileFromBackupService(TransFileService):
    """
    下载介质文件包到目标机器
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行传输文件的原子任务。目前文件传输支持两个模式：1：第三方cos原文件传输 2：服务器之间文件传输
        kwargs.get('file_type') 参数用来控传输模式，如果等于1，则采用服务之间的文件传输。否则都作为第三方cos原文件传输
        """
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        backup_id = kwargs["backup_id"]
        cluster_id = kwargs["cluster_id"]
        backup_handler = MySQLBackupHandler(
            cluster_id=cluster_id,
            is_full_backup=True,
            backup_id=backup_id,
            backup_source=MySQLBackupSource.LOCAL,
        )
        backup_info = backup_handler.get_tendb_latest_backup_info()
        logger.info("get backup info")
        logger.info(backup_info)
        if backup_info is None or len(backup_info["task_ids"]) == 0:
            raise Exception("backup_info is empty")
        # 传到父类
        data.get_one_of_inputs("kwargs")["backup_id"] = kwargs["backup_id"]
        data.get_one_of_inputs("kwargs")["cluster_id"] = kwargs["cluster_id"]
        data.get_one_of_inputs("kwargs")["file_list"] = backup_info["task_ids"]

        # 作为上下文传到下一个节点
        trans_data["backup_info"] = backup_info
        data.outputs.trans_data = trans_data

        return super()._execute(data, parent_data)


class TransFileFromBackupComponent(Component):
    name = __name__
    code = "mysql_exec_trans_file_from_backup_context"
    bound_service = TransFileFromBackupService
