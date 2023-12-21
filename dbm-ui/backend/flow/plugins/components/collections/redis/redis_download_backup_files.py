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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.components.mysql_backup.client import RedisBackupApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.redis_context_dataclass import RedisDataStructureContext


class RedisDownloadBackupfile(BaseService):
    """
    Redis下载备份文件
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(60)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisDataStructureContext = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        dest_dir = trans_data.backup_dir + "/dbbak/recover_redis"
        params = {
            "bk_cloud_id": kwargs["bk_cloud_id"],
            "taskid_list": kwargs["task_ids"],
            "dest_ip": kwargs["dest_ip"],
            "login_user": kwargs["login_user"],
            "login_passwd": kwargs["login_passwd"],
            "dest_dir": dest_dir,
            "reason": kwargs["reason"],
        }
        self.log_debug(params)
        response = RedisBackupApi.download(params=params)
        backup_bill_id = response.get("bill_id", -1)
        if backup_bill_id > 0:
            self.log_debug(_("调起下载 {}").format(backup_bill_id))
            data.outputs.backup_bill_id = backup_bill_id
            return True
        else:
            return False

    def _schedule(self, data, parent_data, callback_data=None):
        # 定义异步扫描
        backup_bill_id = data.get_one_of_outputs("backup_bill_id")
        self.log_info(_("下载单据ID {}").format(backup_bill_id))
        result_response = RedisBackupApi.download_result({"bill_id": backup_bill_id})
        # 如何判断
        if result_response is not None and "total" in result_response:
            if result_response["total"]["todo"] == 0 and result_response["total"]["fail"] == 0:
                self.log_info(_("{} 下载成功").format(backup_bill_id))
                self.finish_schedule()
                return True
            elif result_response["total"]["fail"] > 0:
                self.log_error(_("{} 下载失败").format(backup_bill_id))
                self.log_debug(str(result_response))
                self.finish_schedule()
                return False
            else:
                self.log_debug(_("{} 下载中: todo {}").format(backup_bill_id, result_response["total"]["todo"]))
        else:
            self.log_debug("result response fail")
            self.finish_schedule()
            return False


class RedisDownloadBackupfileComponent(Component):
    name = __name__
    code = "redis_download_backup_file"
    bound_service = RedisDownloadBackupfile
