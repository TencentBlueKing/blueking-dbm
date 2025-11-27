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
import json
import logging
import os
from datetime import timedelta
from typing import Any, Dict

from django.db.models import F, Func, Q
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase, TaskStatus
from backend.db_report.models.mysql_backup_result import MysqlBackupResult
from backend.flow.consts import RollbackType
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise import MySQLRollbackExerciseFlow
from backend.flow.engine.controller.base import BaseController
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


def bytes_to_gb(bytes: int) -> float:
    return bytes / 1024 / 1024 / 1024


def backup_info_format(backup_info: dict) -> Dict[str, Any]:
    """
    备份信息格式化，兼容从es获取的备份信息
    @param backup_info:一条备份记录
    @return: 返回格式化后的备份信息
    """
    backup_info["binlog_info"] = json.loads(backup_info["binlog_info"])
    backup_info["file_list"] = json.loads(backup_info["file_list"])
    backup_info["extra_fields"] = json.loads(backup_info["extra_fields"])
    backup_info["consistent_backup_time"] = backup_info["backup_consistent_time"]
    backup_info["backup_time"] = backup_info["backup_consistent_time"]
    backup_info["bk_cloud_id"] = backup_info["extra_fields"]["bk_cloud_id"]
    backup_info["encrypt_enable"] = backup_info["extra_fields"]["encrypt_enable"]
    backup_info["time_zone"] = backup_info["extra_fields"]["time_zone"]
    backup_info["backup_charset"] = backup_info["extra_fields"]["backup_charset"]
    backup_info["backup_tool"] = backup_info["extra_fields"]["backup_tool"]
    backup_info["file_list_details"] = backup_info["file_list"]
    task_ids = []
    local_files = []
    for file in backup_info["file_list_details"]:
        task_ids.append(file["task_id"])
        local_files.append(os.path.join(backup_info["extra_fields"].get("original_backup_dir", ""), file["file_name"]))
        if file["file_type"] == "priv":
            file["mysql_role"] = backup_info["mysql_role"]
            file["backup_consistent_time"] = backup_info["backup_consistent_time"]
            backup_info["priv"] = file
        if file["file_type"] == "index":
            backup_info["index"] = file
    backup_info["task_ids"] = task_ids
    backup_info["local_files"] = local_files
    return backup_info


class MySQLBackupDataRecoveryController(BaseController):
    """
    备份恢复演练
    """

    def mysql_backup_data_recovery_scene(self):
        """
        备份恢复演练
        """
        flow = MySQLRollbackExerciseFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run()

    def mysql_rollback_exercise_by_cluster(self):
        """
        按集群执行MySQL回档演练
        """
        cluster_id = self.ticket_data["cluster_id"]
        pause_after_restore = self.ticket_data["pause_after_restore"]
        rollback_host = self.ticket_data["rollback_host"]
        bk_biz_id = self.ticket_data["bk_biz_id"]
        backup_id = self.ticket_data.get("backup_id")

        # 验证集群存在
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            logger.error(_("集群 {} 不存在").format(cluster_id))
            raise ValueError(_("集群 {} 不存在").format(cluster_id))

        # 查询备份记录
        backup_result = None
        if backup_id:
            # 如果指定了backup_id，查询对应的备份记录
            logger.info(_("查询指定的备份记录: backup_id={}, cluster_id={}").format(backup_id, cluster_id))
            backup_results = MysqlBackupResult.objects.filter(
                backup_id=backup_id, cluster_id=cluster_id, is_full_backup=1
            ).exclude(mysql_role__in=["spider_master", "TDBCTL", "spider_mnt"])

            if not backup_results.exists():
                logger.error(_("未找到备份记录: backup_id={}, cluster_id={}").format(backup_id, cluster_id))
                raise ValueError(_("未找到备份记录: backup_id={}, cluster_id={}").format(backup_id, cluster_id))

            backup_result = backup_results.first()
        else:
            # 如果未指定backup_id，查询最近3天的备份记录
            logger.info(_("查询最近3天的备份记录: cluster_id={}").format(cluster_id))
            start_time = timezone.now() - timedelta(days=3)
            end_time = timezone.now()

            conditions = Q(
                cluster_id=cluster_id,
                cluster_address=cluster.immute_domain,
                backup_consistent_time__gte=start_time,
                backup_consistent_time__lte=end_time,
                is_full_backup=1,
            ) & ~Q(mysql_role__in=["spider_master", "TDBCTL", "spider_mnt"])

            backup_results = (
                MysqlBackupResult.objects.filter(conditions)
                .annotate(json_valid=Func(F("extra_fields"), function="JSON_VALID"))
                .filter(json_valid=1)
                .order_by("-backup_consistent_time")
            )

            if not backup_results.exists():
                logger.error(_("集群 {} 最近3天没有可用的备份记录").format(cluster.immute_domain))
                raise ValueError(_("集群 {} 最近3天没有可用的备份记录").format(cluster.immute_domain))

            backup_result = backup_results.first()
            logger.info(
                _("找到备份记录: backup_id={}, backup_time={}").format(
                    backup_result.backup_id, backup_result.backup_consistent_time
                )
            )

        # 格式化备份信息
        backup_result.backup_consistent_time = backup_result.backup_consistent_time.isoformat()
        backup_result.backup_begin_time = backup_result.backup_begin_time.isoformat()
        backup_result.backup_end_time = backup_result.backup_end_time.isoformat()
        backup_record = model_to_dict(backup_result)
        backup_record["backup_source"] = MySQLBackupSource.REMOTE.value

        # 格式化备份记录为flow需要的格式
        try:
            backup_record_formatted = backup_info_format(backup_record)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(_("格式化备份记录失败: {}, 备份记录: {}").format(e, backup_record))
            raise ValueError(_("格式化备份记录失败: {}").format(str(e)))

        # 从格式化后的备份记录中提取任务需要的字段
        extra_fields = backup_record_formatted.get("extra_fields", {})
        time_zone = extra_fields.get("time_zone", "")
        backup_charset = backup_record_formatted.get("backup_charset", "")
        backup_tool = backup_record_formatted.get("backup_tool", "")
        sql_mode = extra_fields.get("sql_mode", "")

        # 创建MySQLBackupRecoverTask记录
        task = MySQLBackupRecoverTask(
            bk_biz_id=bk_biz_id,
            cluster_id=cluster.id,
            cluster_domain=cluster.immute_domain,
            cluster_type=cluster.cluster_type,
            charset=backup_charset,
            mysql_version=backup_record.get("mysql_version", ""),
            sql_mode=sql_mode,
            backup_id=backup_record["backup_id"],
            backup_begin_time=backup_record["backup_begin_time"],
            backup_end_time=backup_record["backup_end_time"],
            backup_total_size=int(bytes_to_gb(backup_record.get("total_filesize", 0))),
            backup_host=backup_record.get("backup_host", ""),
            backup_host_role=backup_record.get("mysql_role", ""),
            backup_type=backup_record.get("backup_type", ""),
            backup_tool=backup_tool,
            time_zone=time_zone,
            task_id=self.root_id,
            task_status=TaskStatus.COMMIT_SUCCESS,
            phase=TaskPhase.RUNNING,
            exercise_host_ip=rollback_host["ip"],
            creator="system",
            updater="system",
        )
        task.save()

        # 构建flow_context
        flow_context = {
            "uid": self.root_id,
            "ticket_type": TicketType.MYSQL_ROLLBACK_EXERCISE,
            "exercise_cluster_id": cluster.id,
            "backup_id": backup_record["backup_id"],
            "rollback_host": rollback_host,
            "bk_biz_id": bk_biz_id,
            "backup_record": backup_record_formatted,
            "created_by": "system",
            "labels": [],
            "rollback_type": RollbackType.REMOTE_AND_BACKUPID,
            "pause_after_restore": pause_after_restore,
        }

        # 启动flow
        logger.info(_("启动MySQL回档演练流程: root_id={}, cluster_id={}").format(self.root_id, cluster_id))
        flow = MySQLRollbackExerciseFlow(root_id=self.root_id, data=flow_context)
        flow.run()
