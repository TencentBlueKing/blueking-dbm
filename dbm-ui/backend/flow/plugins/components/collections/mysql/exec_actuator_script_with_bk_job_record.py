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
from pipeline.component_framework.component import Component

from backend.flow.utils.bk_job_record import (
    record_bk_job_instance,
    try_resolve_cluster_id,
    try_resolve_step_instance_id,
)
from backend.flow.utils.sql_file_exec_duration_recorder import record_sql_file_exec_durations

from .exec_actuator_script import ExecuteDBActuatorScriptService

# 新组件 code，与 mysql_db_actuator_execute 并存
ACTUATOR_BK_JOB_RECORD_COMPONENT_CODE = "mysql_db_actuator_execute_with_bk_job_record"


class ExecuteDBActuatorScriptWithBkJobRecordService(ExecuteDBActuatorScriptService):
    """
    与父类行为一致，在成功调度 fast_execute_script 后将 job_instance_id
    等写入 flow_bk_job_instance。作业成功后再解析 SQL 文件执行耗时入库。
    落库失败不阻断 Job（仅打日志，仍 return True）。
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        kwargs = data.get_one_of_inputs("kwargs")

        ok = super()._execute(data, parent_data)
        if not ok:
            return False
        try:
            ext_result = data.get_one_of_outputs("ext_result")
            if not (
                isinstance(ext_result, dict) and ext_result.get("result") and isinstance(ext_result.get("data"), dict)
            ):
                return True
            raw_id = ext_result["data"].get("job_instance_id")
            if raw_id is None:
                return True
            job_instance_id = int(raw_id)
            ticket_uid = None
            if isinstance(global_data, dict):
                ticket_uid = global_data.get("uid")
            ticket_id = ticket_uid if isinstance(ticket_uid, int) else None
            version_id = (self._runtime_attrs or {}).get("version") or ""
            out_ips = data.get_one_of_outputs("exec_ips")
            record_bk_job_instance(
                ticket_id=ticket_id,
                root_id=kwargs["root_id"],
                node_id=kwargs["node_id"],
                version_id=version_id,
                job_instance_id=job_instance_id,
                step_instance_id=try_resolve_step_instance_id(ext_result, job_instance_id),
                node_name=kwargs.get("node_name") or "",
                component_code=ACTUATOR_BK_JOB_RECORD_COMPONENT_CODE,
                cluster_id=try_resolve_cluster_id(
                    kwargs if isinstance(kwargs, dict) else None,
                    global_data,
                ),
                exec_ips=out_ips,
            )
        except Exception as e:
            self.log_exception(_("落库蓝鲸作业关联失败(已忽略,不影响任务执行): {}").format(str(e)))
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        ok = super()._schedule(data, parent_data, callback_data)
        if not ok:
            return False
        if data.get_one_of_outputs("job_execute") is not True:
            return True
        try:
            record_sql_file_exec_durations(data=data)
        except Exception as exc:
            self.log_exception(_("记录SQL文件执行耗时失败(已忽略,不影响任务执行): {}").format(str(exc)))
        return True


class ExecuteDBActuatorScriptWithBkJobRecordComponent(Component):
    name = __name__
    code = ACTUATOR_BK_JOB_RECORD_COMPONENT_CODE
    bound_service = ExecuteDBActuatorScriptWithBkJobRecordService
