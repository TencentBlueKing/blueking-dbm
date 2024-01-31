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

import logging.config

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

import backend.flow.utils.mongodb.mongodb_dataclass as flow_context
from backend.components.mysql_backup.client import RedisBackupApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MongoDownloadBackupFile(BaseService):
    """
    下载备份文件到 $dest_dir/dbbak/recover_mg
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(2)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: flow_context.CommonContext = data.get_one_of_inputs("trans_data")
        logger.info("trans_data {} ".format(trans_data))
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = flow_context.CommonContext()
            self.log_info("trans_data init {}".format(trans_data))
        else:
            self.log_info("trans_data is {}".format(trans_data))

        retry_times = trans_data.get("retry") or 0
        trans_data.set("retry", retry_times + 1)
        data.outputs["trans_data"] = trans_data  # update

        params = {
            "bk_cloud_id": kwargs["bk_cloud_id"],
            "taskid_list": kwargs["task_ids"],
            "login_user": kwargs["login_user"],
            "login_passwd": kwargs["login_passwd"],
            "dest_ip": kwargs["dest_ip"],
            "dest_dir": kwargs["dest_dir"],
            "reason": kwargs["reason"],
        }
        logger.info("MongoDownloadBackupFile params :{} +++ ".format(params))

        self.log_debug(params)
        response = RedisBackupApi.download(params=params)  # 这里使用RedisBackupApi，这是通用的.
        self.log_warning("RedisBackupApi.download response: {}".format(response))

        backup_bill_id = response.get("bill_id", -1)
        if backup_bill_id > 0:
            self.log_debug(_("调起下载 {}").format(backup_bill_id))
            data.outputs.backup_bill_id = backup_bill_id  # 注意，这里保存了output.backup_bill_id
            return True
        else:
            return False

    def _schedule(self, data, parent_data, callback_data=None):
        trans_data: flow_context.CommonContext = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = flow_context.CommonContext()
            self.log_info("trans_data init {}".format(trans_data))
        else:
            self.log_info("trans_data is {}".format(trans_data))
        trans_data.set("retry", (trans_data.get("retry") or 0) + 1)
        data.outputs["trans_data"] = trans_data  # update

        # 重写异步扫描
        backup_bill_id = data.get_one_of_outputs("backup_bill_id")
        if backup_bill_id is None:
            self.log_debug("_schedule backup_bill_id is None, retry")
            # todo 重试次数
            return
        self.log_info(_("下载单据ID {}").format(backup_bill_id))
        result_response = RedisBackupApi.download_result({"bill_id": backup_bill_id})
        self.log_info(_("下载单据ID {} resp: {}").format(backup_bill_id, result_response))
        # 如何判断
        if result_response is not None and "total" in result_response:
            total = result_response["total"]
            if total["todo"] == 0 and total["fail"] == 0 and total["doing"] == 0:
                self.log_info(_("{} 下载成功").format(backup_bill_id))
                self.finish_schedule()
                return True
            elif total["fail"] > 0:
                self.log_error(_("{} 下载失败").format(backup_bill_id))
                self.log_debug(str(result_response))
                self.finish_schedule()
                return False
            else:
                self.log_debug(_("{} 下载中: todo {}").format(backup_bill_id, total["todo"]))
        else:
            self.log_debug("result response fail")
            self.finish_schedule()
            return False


class MongoDownloadBackupFileComponent(Component):
    name = __name__
    code = "mongo_download_backup_file"
    bound_service = MongoDownloadBackupFile
