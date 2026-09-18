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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components.mysql_backup.client import MysqlBackupApi
from backend.flow.plugins.components.collections.common.base_service import BkJobService


def download_bill_state(result_response):
    """备份下载单据的终态。True 成功，False 失败，None 仍在下载。"""
    if not result_response or "total" not in result_response:
        return False
    total = result_response["total"]
    if total["todo"] == 0 and total["doing"] == 0 and total["fail"] == 0:
        return True
    if total["fail"] > 0:
        return False
    return None


class MySQLDownloadBackupfile(BkJobService):
    """
    MySQL下载备份文件
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(120)
    # backupapi/recover 按这个大小切 task_ids。回档下载和演练下载共用。
    DOWNLOAD_TASK_BATCH_SIZE = 500

    def poll_download_bill(self, bill_id, bk_cloud_id):
        """查一张下载单据。不结束本节点，调用方决定何时 finish_schedule。"""
        result_response = MysqlBackupApi.download_result({"bill_id": bill_id, "bk_cloud_id": bk_cloud_id})
        state = download_bill_state(result_response)
        if state is True:
            self.log_info(_("{} 下载成功").format(bill_id))
        elif state is False:
            if result_response is not None and "total" in result_response:
                self.log_error(_("{} 下载失败").format(bill_id))
                self.log_error(str(result_response))
            else:
                self.log_error("result response fail")
        else:
            total = result_response["total"]
            self.log_info(_("{} 下载中: todo {} doing {}").format(bill_id, total["todo"], total["doing"]))
        return state

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        if not kwargs["task_ids"]:
            return False

        params = {
            "bk_cloud_id": kwargs["bk_cloud_id"],
            "taskid_list": kwargs["task_ids"],
            "dest_ip": kwargs["dest_ip"],
            "login_user": kwargs["login_user"],
            "dest_dir": kwargs["dest_dir"],
            "reason": kwargs["reason"],
            "login_passwd": kwargs["login_passwd"],
        }
        self.log_debug(params)
        self.log_info(_("下载 {} 到 {}").format(kwargs["task_ids"], kwargs["dest_ip"]))
        response = MysqlBackupApi.download(params=params)
        backup_bill_id = response.get("bill_id", -1)
        if backup_bill_id > 0:
            self.log_info(_("调起下载 {}").format(backup_bill_id))
            data.outputs.backup_bill_id = backup_bill_id
            return True
        else:
            return False

    def _schedule(self, data, parent_data, callback_data=None):
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_debug(kwargs)
        backup_bill_id = data.get_one_of_outputs("backup_bill_id")
        self.log_info(_("下载单据ID {}").format(backup_bill_id))
        state = self.poll_download_bill(backup_bill_id, kwargs["bk_cloud_id"])
        if state is None:
            return None
        self.finish_schedule()
        return state


class MySQLDownloadBackupfileComponent(Component):
    name = __name__
    code = "mysql_download_backup_file"
    bound_service = MySQLDownloadBackupfile
