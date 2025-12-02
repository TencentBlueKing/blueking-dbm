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

from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskStatus
from backend.db_report.enums import ReportStateType
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MySQLBackupRecoverTaskMetaSvr(BaseService):
    """
    更新备份恢复演练任务元信息
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        # 根据task_id 更新task_status
        tsk = MySQLBackupRecoverTask.objects.get(task_id=kwargs["task_id"])
        # 如果已经失败了，就不在更改状态
        if tsk.task_status == TaskStatus.RECOVER_FAILED:
            result = True
            data.outputs.ext_result = result
            return result
        tsk.task_status = kwargs["task_status"]
        if kwargs["task_status"] == TaskStatus.DEPLOY_SUCCESS:
            tsk.recover_start_time = timezone.now()
            tsk.save(update_fields=["task_status", "recover_start_time"])
        elif kwargs["task_status"] == TaskStatus.RECOVER_SUCCESS:
            # 如果是恢复成功，则更新任务结束时间
            tsk.recover_end_time = timezone.now()
            tsk.state = ReportStateType.NORMAL.value
            tsk.save(update_fields=["task_status", "state", "recover_end_time"])
        elif kwargs["task_status"] == TaskStatus.RECOVER_FAILED:
            # 备份恢复失败时，设置 state 为 abnormal，且后续不再改变
            update_fields_list = ["task_status"]
            tsk.state = ReportStateType.ABNORMAL.value
            update_fields_list.append("state")
            # 恢复失败时，从上下文读取 source_act 写入的错误日志
            try:
                # 从 trans_data 读取错误日志（ExecRollbackActForSourceService 失败时写入）
                trans_data = data.get_one_of_inputs("trans_data")
                self.log_info(f"trans_data: {trans_data}")
                rollback_error_info = trans_data.rollback_error_info
                self.log_info(f"rollback_error_info: {rollback_error_info}")
                err_text = rollback_error_info.get("error_logs", "")
                self.log_info(f"err_text: {err_text}")
                # 使用 strip() 去除空白字符，避免保存无意义的空白内容
                if err_text and err_text.strip():
                    prefix = _("\n错误日志:\n")
                    err_text = err_text.strip()
                    tsk.task_info = (tsk.task_info + prefix if tsk.task_info else prefix) + err_text
                    update_fields_list.append("task_info")
                    tsk.save(update_fields=update_fields_list)
                else:
                    logger.warning(_("未能获取到错误日志，task_id: {}").format(kwargs["task_id"]))
                    tsk.save(update_fields=update_fields_list)
            except Exception as e:
                logger.warning(_("读取上下文错误日志失败: {}").format(str(e)))
                tsk.save(update_fields=update_fields_list)
        else:
            tsk.save(update_fields=["task_status"])
        result = True
        data.outputs.ext_result = result
        return result


class MySQLBackupRecoverTaskMetaComponent(Component):
    name = __name__
    code = "backup_recover_meta"
    bound_service = MySQLBackupRecoverTaskMetaSvr
