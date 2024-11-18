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
from datetime import datetime

from django.utils.translation import ugettext as _

from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler

logger = logging.getLogger("root")


def get_backup_binlog(
    cluster_id: int, start_time: datetime, end_time: datetime, binlog_info: dict, minute_range=30
) -> dict:
    result = {}
    if start_time > end_time:
        result["query_binlog_error"] = _("备份时间点:{} 大于 回滚时间点:{}".format(start_time, end_time))
        return result
    # 先从别分文件的主节点查询，查询不到改为从节点查询。
    rollback_handler = FixPointRollbackHandler(cluster_id)
    backup_binlog = None
    if "show_slave_status" in binlog_info.keys() and binlog_info.get("show_slave_status", None) is not None:
        backup_binlog = rollback_handler.query_binlog_from_bklog(
            start_time=start_time,
            end_time=end_time,
            host_ip=binlog_info["show_slave_status"]["master_host"],
            port=binlog_info["show_slave_status"]["master_port"],
            minute_range=minute_range,
        )
        result["binlog_start_file"] = binlog_info["show_slave_status"]["binlog_file"]
        result["binlog_start_pos"] = binlog_info["show_slave_status"]["binlog_pos"]
        logger.info("master binlog is:", backup_binlog)

    if backup_binlog is None or len(backup_binlog) == 0:
        backup_binlog = rollback_handler.query_binlog_from_bklog(
            start_time=start_time,
            end_time=end_time,
            host_ip=binlog_info["show_master_status"]["master_host"],
            port=binlog_info["show_master_status"]["master_port"],
            minute_range=minute_range,
        )
        result["binlog_start_file"] = binlog_info["show_master_status"]["binlog_file"]
        result["binlog_start_pos"] = binlog_info["show_master_status"]["binlog_pos"]
        if backup_binlog is None:
            result["query_binlog_error"] = _("原备份节点节点{} 的binlog失败").format(
                binlog_info["show_master_status"]["master_host"]
            )
            return result
    file_list_details = backup_binlog.get("file_list_details", [])
    if len(file_list_details) == 0:
        result["query_binlog_error"] = _("获取不到binlog文件 {}").format(backup_binlog)
        return result

    result["binlog_task_ids"] = [i["task_id"] for i in file_list_details]
    binlog_files = [i["file_name"] for i in file_list_details]
    result["binlog_files"] = ",".join(binlog_files)
    return result
