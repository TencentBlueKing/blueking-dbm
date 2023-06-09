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
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

from backend.components.mysql_backup.client import MysqlBackupApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")
single_ticket_type = [TicketType.MYSQL_SINGLE_APPLY.name]
ha_ticket_type = [TicketType.MYSQL_HA_APPLY.name]


class MySQLDownloadBackupfile(BaseService):
    """
    MySQL下载备份文件
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(60)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        params = {
            "BkCloudID": kwargs["bk_cloud_id"],
            "TaskidList": kwargs["task_ids"],
            "DestIP": kwargs["dest_ip"],
            "LoginUser": kwargs["user"],
            "DestDir": kwargs["file_target_path"],
            "Reason": kwargs["reason"],
        }
        logger.info(params)
        response = MysqlBackupApi.download(params=params)
        if response["code"] == "0":
            bill_id = response["data"]["bill_id"]
            data.outputs.bill_id = bill_id
            return True
        else:
            return False

    def _schedule(self, data, parent_data, callback_data=None):
        # 定义异步扫描
        bill_id = data.get_one_of_outputs("bill_id")
        result_response = MysqlBackupApi.download_result({"bill_id": bill_id})
        if result_response["code"] == "0":
            if result_response["data"]["total"]["todo"] == 0 and result_response["data"]["total"]["fail"] == 0:
                self.finish_schedule()
                return True
            elif result_response["data"]["total"]["fail"] > 0:
                self.finish_schedule()
                return False
        else:
            self.finish_schedule()
            return False


class MySQLDownloadBackupfileComponent(Component):
    name = __name__
    code = "mysql_download_backupfile"
    bound_service = MySQLDownloadBackupfile
