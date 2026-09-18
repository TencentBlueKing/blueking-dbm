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
from datetime import timedelta

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_report.mysql_backup.handers import MySQLBackupHandler
from backend.flow.engine.bamboo.scene.mysql.common.get_local_backup import check_binlog_missing
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import MySQLDownloadBackupfile
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")

# 与 MySQLBackupHandler.get_binlog_for_rollback(minute_range=30) 默认冗余一致
_BINLOG_QUERY_SLACK = timedelta(minutes=30)


def _sms_from_backup_info(backup_info: dict) -> dict:
    binlog_info = (backup_info or {}).get("binlog_info") or {}
    return binlog_info.get("show_master_status") or binlog_info.get("show_slave_status") or {}


def _write_rollback_error(data, trans_data, err_text: str):
    if trans_data is not None:
        trans_data.rollback_error_info = {"error_logs": err_text}
        data.outputs["trans_data"] = trans_data


class MysqlExerciseBinlogQueryService(BaseService):
    """运行时查询演练窗口 binlog，失败只出状态码，不抛异常。"""

    def _fail(self, data, trans_data, err_text: str) -> bool:
        self.log_error(err_text)
        _write_rollback_error(data, trans_data, err_text)
        data.outputs.binlog_query_code = 1
        return False

    def _log_query_window(self, cluster_id, backup_info, start_time, end_time):
        """输出 apply 窗口与实际落库查询窗，方便对照 tb_mysql_binlog_result。"""
        query_start = start_time - _BINLOG_QUERY_SLACK
        query_end = end_time + _BINLOG_QUERY_SLACK
        sms = _sms_from_backup_info(backup_info)
        self.log_info(
            _(
                "演练 binlog 查询: cluster_id={} backup_id={} apply窗口={} ~ {} "
                "实际查询窗={} ~ {}（左右各扩 30 分钟）host={}:{} 起始文件={} pos={}"
            ).format(
                cluster_id,
                (backup_info or {}).get("backup_id"),
                start_time.isoformat(),
                end_time.isoformat(),
                query_start.isoformat(),
                query_end.isoformat(),
                sms.get("master_host") or sms.get("host"),
                sms.get("master_port") or sms.get("port"),
                sms.get("binlog_file"),
                sms.get("binlog_pos"),
            )
        )

    def _log_query_result(self, handler, binlog_result):
        query_sql = getattr(handler, "query", None)
        if query_sql:
            self.log_info(_("演练 binlog 查询 SQL: {}").format(query_sql))
        files = (binlog_result or {}).get("binlog_files_list") or []
        start_file = (binlog_result or {}).get("binlog_start_file")
        self.log_info(
            _("演练 binlog 查询命中文件数={} 文件={} 起始文件={} 起始文件是否命中={}").format(
                len(files), files, start_file, start_file in files if start_file else False
            )
        )

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        backup_info = kwargs.get("backup_info") or {}
        backup_time = kwargs.get("backup_time")
        rollback_time = kwargs.get("rollback_time")
        cluster_id = kwargs.get("cluster_id")

        try:
            start_time = str2datetime(backup_time)
            end_time = str2datetime(rollback_time)
        except Exception as exc:
            return self._fail(data, trans_data, _("演练 binlog 窗口时间解析失败: {}").format(str(exc)))

        self._log_query_window(cluster_id, backup_info, start_time, end_time)

        try:
            handler = MySQLBackupHandler(cluster_id=cluster_id, backup_id=backup_info.get("backup_id"))
            binlog_result = handler.get_binlog_for_rollback(backup_info, start_time, end_time)
        except Exception as exc:
            return self._fail(data, trans_data, _("查询演练窗口 binlog 失败: {}").format(str(exc)))

        self._log_query_result(handler, binlog_result)

        query_error = binlog_result.get("query_binlog_error")
        if query_error:
            return self._fail(data, trans_data, str(query_error))

        binlog_files = binlog_result.get("binlog_files_list") or []
        if not binlog_files:
            return self._fail(data, trans_data, _("窗口内未查询到 binlog 文件"))

        missing_files, check_ok = check_binlog_missing(binlog_files)
        if not check_ok:
            return self._fail(data, trans_data, _("binlog 文件不连续，缺失: {}").format(missing_files))

        trans_data.binlog_task_ids = binlog_result.get("binlog_task_ids") or []
        trans_data.binlog_files_list = binlog_files
        trans_data.binlog_start_file = binlog_result.get("binlog_start_file")
        trans_data.binlog_start_pos = binlog_result.get("binlog_start_pos")
        data.outputs["trans_data"] = trans_data
        data.outputs.binlog_query_code = 0
        self.log_info(_("查询演练窗口 binlog 成功，文件数 {}，起始 {}").format(len(binlog_files), trans_data.binlog_start_file))
        return True


class MysqlExerciseBinlogQueryComponent(Component):
    name = __name__
    code = "mysql_exercise_binlog_query"
    bound_service = MysqlExerciseBinlogQueryService


class MysqlExerciseBinlogDownloadService(MySQLDownloadBackupfile):
    """运行时从 trans_data 读取 task_ids，复用备份系统下载接口。"""

    def _fail_download(self, data, trans_data, err_text: str) -> bool:
        self.log_error(err_text)
        _write_rollback_error(data, trans_data, err_text)
        data.outputs.binlog_download_code = 1
        return False

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        task_ids = getattr(trans_data, "binlog_task_ids", None) or []
        if not task_ids:
            return self._fail_download(data, trans_data, _("未找到 binlog_task_ids"))
        kwargs["task_ids"] = task_ids
        ok = super()._execute(data, parent_data)
        if not ok:
            return self._fail_download(data, trans_data, _("演练 binlog 下载发起失败"))
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        result = super()._schedule(data, parent_data, callback_data)
        # 父类 interval 是类属性，finish 后仍在。轮询中返回 None，终态才写网关码。
        if result is None:
            return result
        data.outputs.binlog_download_code = 0 if result else 1
        if not result:
            trans_data = data.get_one_of_inputs("trans_data")
            _write_rollback_error(data, trans_data, _("演练 binlog 下载失败"))
        return result


class MysqlExerciseBinlogDownloadComponent(Component):
    name = __name__
    code = "mysql_exercise_binlog_download"
    bound_service = MysqlExerciseBinlogDownloadService
