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

from backend.components import MySQLDTSApi
from backend.components.mysqldtsapi.types import CreateTaskRequest, Task, TaskStatusItem
from backend.db_meta.models import MysqlDtsCluster


class MySQLDtsMigrateHandler:
    @classmethod
    def _is_healthy_running(cls, item: TaskStatusItem) -> bool:
        """口径 A：stage 为 Running（大小写不敏感）且 error_msg 为空/空白 → 健康运行中。"""
        stage = (getattr(item, "stage", None) or "").strip().lower()
        error_msg = (getattr(item, "error_msg", None) or "").strip()
        return stage == "running" and not error_msg

    @classmethod
    def _clear_source_binlog_meta(cls, task: Task) -> None:
        """清空 source_conf 断点，避免带着失败前位点 recreate。"""
        for item in task.source_config.source_conf:
            item.binlog_name = ""
            item.binlog_pos = 0
            item.binlog_gtid = ""

    @classmethod
    def reset_task(cls, task_name: str, dts_cluster_id: int) -> dict:
        """
        删除任务后按原配置重建并启动，使 builtin 任务从 Dump 重跑。
        不会清理目标业务数据。健康 Running 的任务禁止 reset。
        """
        try:
            dts_cluster = MysqlDtsCluster.objects.get(id=dts_cluster_id)
        except MysqlDtsCluster.DoesNotExist as exc:
            raise ValueError(_("DTS 集群不存在: {}").format(dts_cluster_id)) from exc

        master_addr = (dts_cluster.master_addr or "").strip()
        if not master_addr:
            raise ValueError(_("DTS 集群 master_addr 为空: {}").format(dts_cluster_id))

        try:
            status_resp = MySQLDTSApi.get_task_status(master_addr, task_name)
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(_("查询 DTS 任务状态失败: {}").format(exc)) from exc

        items = getattr(status_resp, "data", None) or []
        if any(cls._is_healthy_running(item) for item in items):
            raise ValueError(_("任务运行正常，不允许 reset: {}").format(task_name))

        try:
            task = MySQLDTSApi.get_task(master_addr, task_name)
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(_("获取 DTS 任务配置失败: {}").format(exc)) from exc

        cls._clear_source_binlog_meta(task)

        try:
            MySQLDTSApi.delete_task(master_addr, task_name, force=True)
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(_("删除 DTS 任务失败: {}").format(exc)) from exc

        try:
            MySQLDTSApi.create_task(master_addr, CreateTaskRequest(task=task))
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(_("重建 DTS 任务失败: {}").format(exc)) from exc

        try:
            MySQLDTSApi.start_task(master_addr, task_name)
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(_("启动 DTS 任务失败: {}").format(exc)) from exc

        return {
            "task_name": task_name,
            "dts_cluster_id": dts_cluster_id,
            "master_addr": master_addr,
            "action": "reset",
        }
