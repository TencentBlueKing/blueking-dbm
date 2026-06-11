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
import time

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.components.mysql_backup.client import RedisBackupApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.redis_context_dataclass import RedisDataStructureContext
from backend.utils.string import format_size

logger = logging.getLogger("flow")

_PROGRESS_LOG_INTERVAL_SEC = 60


class RedisDownloadBackupfile(BaseService):
    """
    Redis下载备份文件
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(15)

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
        self.log_debug({k: v for k, v in params.items() if k != "login_passwd"})

        response = RedisBackupApi.download(params=params)
        backup_bill_id = response.get("bill_id", -1)
        if backup_bill_id > 0:
            file_count = len(kwargs["task_ids"])
            total_bytes = kwargs.get("total_bytes")
            total_size = format_size(total_bytes) if total_bytes is not None else _("未知")
            self.log_info(
                _(
                    "下载备份到 {dest_ip}: source={source_ip}, full={full_count}, binlog={binlog_count}, "
                    "files={file_count}, size={total_size}, bill={bill_id}"
                ).format(
                    dest_ip=kwargs["dest_ip"],
                    source_ip=kwargs.get("source_ip") or "-",
                    full_count=kwargs.get("full_count") if kwargs.get("full_count") is not None else "-",
                    binlog_count=kwargs.get("binlog_count") if kwargs.get("binlog_count") is not None else "-",
                    file_count=file_count,
                    total_size=total_size,
                    bill_id=backup_bill_id,
                )
            )
            data.outputs.backup_bill_id = backup_bill_id
            return True
        else:
            return False

    def _schedule(self, data, parent_data, callback_data=None):
        backup_bill_id = data.get_one_of_outputs("backup_bill_id")
        self.log_debug(_("轮询下载单据 {}").format(backup_bill_id))
        result_response = RedisBackupApi.download_result({"bill_id": backup_bill_id})
        if result_response is not None and "total" in result_response:
            total = result_response["total"]
            if total["todo"] == 0 and total["doing"] == 0 and total["fail"] == 0:
                self.log_info(_("{} 下载成功").format(backup_bill_id))
                self.finish_schedule()
                return True
            elif total["fail"] > 0:
                self.log_error(_("{} 下载失败").format(backup_bill_id))
                self.log_debug(str(result_response))
                self.finish_schedule()
                return False
            else:
                self._log_download_progress(data, backup_bill_id, total)
        else:
            self.log_debug("result response fail")
            self.finish_schedule()
            return False

    def _log_download_progress(self, data, backup_bill_id, total):
        todo = total["todo"]
        doing = total["doing"]
        last_todo = data.get_one_of_outputs("last_todo")
        last_doing = data.get_one_of_outputs("last_doing")
        last_log_ts = data.get_one_of_outputs("last_progress_log_ts") or 0
        now = time.time()
        progress_changed = todo != last_todo or doing != last_doing
        if progress_changed or (now - last_log_ts) >= _PROGRESS_LOG_INTERVAL_SEC:
            self.log_info(_("{} 下载中: todo={} doing={}").format(backup_bill_id, todo, doing))
            data.outputs.last_todo = todo
            data.outputs.last_doing = doing
            data.outputs.last_progress_log_ts = now
        else:
            self.log_debug(_("{} 下载中: todo={} doing={}").format(backup_bill_id, todo, doing))


class RedisDownloadBackupfileComponent(Component):
    name = __name__
    code = "redis_download_backup_file"
    bound_service = RedisDownloadBackupfile
