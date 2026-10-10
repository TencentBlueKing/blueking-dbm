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
import time
import traceback

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.components.mysql_backup.client import RedisBackupApi
from backend.db_services.redis.rollback.constants import (
    DISK_USED_PLUS_NEED_RATIO_FAIL,
    DISK_USED_RATIO_FAIL,
    DOWNLOAD_BATCH_SIZE,
)
from backend.flow.engine.bamboo.scene.redis.redis_rollback.plan import RollbackPlan
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.utils.string import format_size

logger = logging.getLogger("flow")

_PROGRESS_LOG_INTERVAL_SEC = 60


def decode_df_line(disk_line: str) -> dict:
    parts = disk_line.split()
    return {
        "filesystem": parts[0],
        "total": int(parts[1]) * 1024,
        "used": int(parts[2]) * 1024,
        "avail": int(parts[3]) * 1024,
        "used_ratio": int(parts[4].replace("%", "")),
        "mount_on": parts[5],
    }


def disk_needs(backup_disk: dict, data_disk: dict, download_bytes: int, unpacked_bytes: int) -> list:
    """Peak usage per filesystem: the backup disk holds the download plus its unpacked copy,
    the data disk receives the unpacked file. On a shared filesystem the move is a rename."""
    if backup_disk["mount_on"] == data_disk["mount_on"]:
        return [(_("备份/数据"), backup_disk, download_bytes + unpacked_bytes)]
    return [
        (_("备份"), backup_disk, download_bytes + unpacked_bytes),
        (_("数据"), data_disk, unpacked_bytes),
    ]


class RedisRollbackDiskPrecheckService(BaseService):
    """Gate E: fail before any download when dest host disk is insufficient."""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        try:
            disk_used = getattr(trans_data, "disk_used", None) or {}
            exec_ip = kwargs["exec_ip"]
            host_disk = disk_used.get(exec_ip) or {}
            disks = {}
            for key in ("redis_backup_dir_data", "redis_data_dir_data"):
                raw = host_disk.get(key)
                if not raw:
                    self.log_error(_("{} 缺少磁盘信息: {}").format(exec_ip, key))
                    return False
                disks[key] = decode_df_line(raw)
            needs = disk_needs(
                disks["redis_backup_dir_data"],
                disks["redis_data_dir_data"],
                int(kwargs.get("download_bytes") or 0),
                int(kwargs.get("unpacked_bytes") or 0),
            )
            for label, disk_info, needed_size in needs:
                if not self._check(exec_ip, label, disk_info, needed_size):
                    return False
        except Exception as exc:  # pylint: disable=broad-except
            traceback.print_exc()
            self.log_error("redis rollback disk precheck failed:{}".format(exc))
            return False

        self.log_info("redis rollback disk precheck success")
        return True

    def _check(self, exec_ip, dir_label, disk_info, data_size) -> bool:
        self.log_info(
            _("临时机 {} [{}] {}: 需要 {} / 可用 {} (已用 {}%, 总量 {})").format(
                exec_ip,
                dir_label,
                disk_info["mount_on"],
                format_size(data_size),
                format_size(disk_info["avail"]),
                disk_info["used_ratio"],
                format_size(disk_info["total"]),
            )
        )
        if disk_info["used_ratio"] > DISK_USED_RATIO_FAIL:
            self.log_error(
                _("{} {} 已用 {}% > {}%").format(exec_ip, dir_label, disk_info["used_ratio"], DISK_USED_RATIO_FAIL)
            )
            return False
        if data_size > disk_info["avail"]:
            self.log_error(
                _("{} {} 需要 {} > 可用 {}").format(
                    exec_ip, dir_label, format_size(data_size), format_size(disk_info["avail"])
                )
            )
            return False
        used_plus_need_ratio = (disk_info["used"] + data_size) / disk_info["total"] if disk_info["total"] else 0
        if used_plus_need_ratio > DISK_USED_PLUS_NEED_RATIO_FAIL:
            self.log_error(_("{} {} (已用+需要) 将超过 90%").format(exec_ip, dir_label))
            return False
        return True


class RedisRollbackDiskPrecheckComponent(Component):
    name = __name__
    code = "redis_rollback_disk_precheck"
    bound_service = RedisRollbackDiskPrecheckService


class RedisRollbackDownloadService(BaseService):
    """Download all backup files of one dest_ip, submitted in bills of DOWNLOAD_BATCH_SIZE task_ids."""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(15)

    @staticmethod
    def _download_targets(kwargs):
        """``(task_ids, bytes)`` from the persisted plan; nodes built before plans were persisted carry them."""
        if kwargs.get("plan_id"):
            host = RollbackPlan.load(kwargs["plan_id"]).dest_host(kwargs["dest_ip"])
            return host.task_ids, host.download_bytes
        return kwargs["task_ids"], kwargs.get("download_bytes")

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        host_disk = (getattr(trans_data, "disk_used", None) or {}).get(kwargs["dest_ip"]) or {}
        backup_dir = host_disk.get("backup_dir")
        if not backup_dir:
            self.log_error(_("{} 缺少备份目录信息，无法确定下载路径").format(kwargs["dest_ip"]))
            return False
        task_ids, total_bytes = self._download_targets(kwargs)
        params = {
            "bk_cloud_id": kwargs["bk_cloud_id"],
            "dest_ip": kwargs["dest_ip"],
            "login_user": kwargs["login_user"],
            "login_passwd": kwargs["login_passwd"],
            "dest_dir": backup_dir.rstrip("/") + "/dbbak/recover_redis",
            "reason": kwargs.get("reason") or "redis rollback",
        }
        self.log_debug({k: v for k, v in params.items() if k != "login_passwd"})
        bill_ids = []
        for start in range(0, len(task_ids), DOWNLOAD_BATCH_SIZE):
            response = RedisBackupApi.download(
                params={**params, "taskid_list": task_ids[start : start + DOWNLOAD_BATCH_SIZE]}
            )
            bill_id = response.get("bill_id", -1)
            if bill_id <= 0:
                # A retry resubmits every batch: bamboo rebuilds outputs on each execute.
                self.log_error(_("提交下载失败: {}；已提交且仍在下载的单号: {}").format(response, bill_ids))
                return False
            bill_ids.append(bill_id)
        self.log_info(
            _("下载备份到 {dest_ip}: files={file_count}, size={total_size}, bills={bill_ids}").format(
                dest_ip=kwargs["dest_ip"],
                file_count=len(task_ids),
                total_size=format_size(total_bytes) if total_bytes is not None else _("未知"),
                bill_ids=bill_ids,
            )
        )
        data.outputs.backup_bill_ids = bill_ids
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        bill_ids = data.get_one_of_outputs("backup_bill_ids") or [data.get_one_of_outputs("backup_bill_id")]
        todo = doing = 0
        for bill_id in bill_ids:
            result_response = RedisBackupApi.download_result({"bill_id": bill_id})
            if result_response is None or "total" not in result_response:
                self.log_error(_("{} 查询下载结果失败").format(bill_id))
                self.finish_schedule()
                return False
            total = result_response["total"]
            if total["fail"] > 0:
                self.log_error(_("{} 下载失败").format(bill_id))
                self.finish_schedule()
                return False
            todo += total["todo"]
            doing += total["doing"]
        if todo == 0 and doing == 0:
            self.log_info(_("{} 下载成功").format(bill_ids))
            self.finish_schedule()
            return True
        last_todo = data.get_one_of_outputs("last_todo")
        last_doing = data.get_one_of_outputs("last_doing")
        last_log_ts = data.get_one_of_outputs("last_progress_log_ts") or 0
        now = time.time()
        if todo != last_todo or doing != last_doing or (now - last_log_ts) >= _PROGRESS_LOG_INTERVAL_SEC:
            self.log_info(_("{} 下载中: todo={} doing={}").format(bill_ids, todo, doing))
            data.outputs.last_todo = todo
            data.outputs.last_doing = doing
            data.outputs.last_progress_log_ts = now
        return True


class RedisRollbackDownloadComponent(Component):
    name = __name__
    code = "redis_rollback_download"
    bound_service = RedisRollbackDownloadService
