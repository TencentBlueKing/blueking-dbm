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
from pipeline.component_framework.component import Component

from backend.db_periodic_task.models import MySQLBackupRecoverTask
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
        tsk.task_status = kwargs["task_status"]
        if kwargs["task_status"] == "deploy_success":
            tsk.recover_start_time = timezone.now()
            tsk.save(update_fields=["task_status", "recover_start_time"])
        elif kwargs["task_status"] == "recover_success":
            # 如果是恢复成功，则更新任务结束时间
            tsk.recover_end_time = timezone.now()
            tsk.status = True
            tsk.save(update_fields=["task_status", "recover_end_time"])
        else:
            tsk.save(update_fields=["task_status"])
        result = True
        data.outputs.ext_result = result
        return result


class MySQLBackupRecoverTaskMetaComponent(Component):
    name = __name__
    code = "backup_recover_meta"
    bound_service = MySQLBackupRecoverTaskMetaSvr
