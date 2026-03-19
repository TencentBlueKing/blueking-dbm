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
import copy
import logging
from datetime import datetime
from typing import Optional

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend import env
from backend.components import JobApi
from backend.db_meta.api.cluster.nosqlcomm.decommission import decommission_instances
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.scene.redis.redis_data_structure import RedisDataStructureFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldService
from backend.flow.plugins.components.collections.common.base_service import BaseService, BkJobService
from backend.flow.utils.redis import redis_context_dataclass as flow_context
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.utils.basic import generate_root_id
from backend.utils.string import base64_encode

logger = logging.getLogger("json")


class RedisLogCapturingService(BaseService):
    """
    Enhanced BaseService that automatically captures all log messages to trans_data.task_info.
    Only works with `RedisRollbackExerciseContext`.
    """

    trans_data: Optional[RedisRollbackExerciseContext] = None

    def init_trans_data(self, data):
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data: RedisRollbackExerciseContext = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            cls_name = kwargs.get("set_trans_data_dataclass", RedisRollbackExerciseContext.__name__)
            trans_data = getattr(flow_context, cls_name)()
        self.trans_data = trans_data

    def _append_to_task_info(self, msg: str, log_level: str):
        """Internal method to append formatted message to task_info"""
        if self.trans_data is None:
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{current_time}] [{log_level.upper()}]: {msg}"

        if self.trans_data.task_msg is None:
            self.trans_data.task_msg = []
        self.trans_data.task_msg.append(formatted_msg)

    def log_info(self, msg: str):
        """Override to auto-capture info logs"""
        super().log_info(msg)
        self._append_to_task_info(msg, "info")

    def log_warning(self, msg: str):
        """Override to auto-capture warning logs"""
        super().log_warning(msg)
        self._append_to_task_info(msg, "warning")

    def log_error(self, msg: str):
        """Override to auto-capture error logs and set error_occurred flag"""
        super().log_error(msg)
        self._append_to_task_info(msg, "error")
        if self.trans_data is not None:
            self.trans_data.error_occurred = True

    def log_debug(self, msg: str):
        """Override to auto-capture debug logs"""
        super().log_debug(msg)
        self._append_to_task_info(msg, "debug")

    def _execute(self, data, parent_data) -> bool:
        self.init_trans_data(data)
        result = self._execute_inner_captured(data, parent_data)
        data.outputs["trans_data"] = self.trans_data
        return result

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        self.init_trans_data(data)
        result = self._schedule_inner_captured(data, parent_data, callback_data)
        data.outputs["trans_data"] = self.trans_data
        return result

    def _execute_inner_captured(self, data, parent_data) -> bool:
        raise NotImplementedError("Subclasses must implement this method")

    def _schedule_inner_captured(self, data, parent_data, callback_data=None) -> bool:
        self.finish_schedule()
        return True


class RedisRollbackExerciseAlarmShieldService(RedisLogCapturingService, AddAlarmShieldService):
    """
    Alarm shield service that combines RedisLogCapturingService's init_trans_data
    with AddAlarmShieldService's alarm shield logic.
    """

    def _execute_inner_captured(self, data, parent_data) -> bool:
        return AddAlarmShieldService._execute(self, data, parent_data)


class RedisRollbackExerciseAlarmShieldComponent(Component):
    name = __name__
    code = "redis_alarm_shield"
    bound_service = RedisRollbackExerciseAlarmShieldService


class RedisExerciseReportUpdateService(RedisLogCapturingService):
    """
    Pipeline component that updates RedisRollbackExerciseReport stage at runtime.
    Always returns True so it never blocks the pipeline.
    """

    TERMINAL_STAGES = {TaskStage.DONE, TaskStage.ROLLBACK_FAILED, TaskStage.CLEANUP_FAILED}

    def _execute_inner_captured(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        report_id = kwargs.get("report_id")
        stage = kwargs.get("stage")
        task_message = kwargs.get("task_message")

        if stage in self.TERMINAL_STAGES and not task_message and self.trans_data and self.trans_data.task_msg:
            task_message = "\n".join(self.trans_data.task_msg)

        try:
            report = Report.objects.get(id=report_id)
            report.mark(stage, task_message=task_message)
            self.log_info(_("Report {} marked as {}").format(report_id, stage))
        except Report.DoesNotExist:
            self.log_error(_("Report {} not found").format(report_id))
        except Exception as e:
            self.log_error(_("Failed to update report {}: {}").format(report_id, str(e)))

        return True


class RedisExerciseReportUpdateComponent(Component):
    name = __name__
    code = "redis_exercise_report_update"
    bound_service = RedisExerciseReportUpdateService


FLOW_REGISTRY = {
    "redis_data_structure": (RedisDataStructureFlow, "redis_data_structure_flow"),
    "redis_data_structure_task_delete": (RedisDataStructureTaskDeleteFlow, "redis_rollback_task_delete_flow"),
}


class RedisExerciseFlowRunnerService(RedisLogCapturingService):
    """Generic runner that launches a child pipeline via Flow.flow() and polls until completion.

    Looks up the flow class/method from the registry by ``flow_identifier``,
    generates a child root_id via ``generate_root_id()``, calls the flow's main
    method (which creates a proper FlowTree + submits the pipeline), then polls
    ``FlowTree.status`` until the child finishes or times out.

    Sets ``rollback_code`` in outputs so ``add_conditional_subs`` can branch.

    kwargs:
        flow_identifier: key into flow registry (e.g. "redis_data_structure")
        flow_data: data dict for the flow constructor
        report_id: (optional) report ID for storing the child pipeline ID
        flow_id_field: (optional) report field to write the child root_id into
        polling_timeout: timeout in seconds (default 3600)
        polling_interval: seconds between schedule ticks (default 10)
        output_var: output key for the result code, must match conditions_param
                    in add_conditional_subs (default "rollback_code")

    Outputs:
        <output_var>: 0 = success, 1 = failure
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)

    def _set_result(self, data, code: int):
        output_var = data.get_one_of_outputs("output_var") or "rollback_code"
        setattr(data.outputs, output_var, code)

    def _execute_inner_captured(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        polling_interval = kwargs.get("polling_interval", 10)
        self.interval = StaticIntervalGenerator(polling_interval)

        flow_identifier = kwargs["flow_identifier"]
        flow_data = kwargs["flow_data"]
        report_id = kwargs.get("report_id")
        flow_id_field = kwargs.get("flow_id_field")
        polling_timeout = kwargs.get("polling_timeout", 3600)
        output_var = kwargs.get("output_var", "rollback_code")

        data.outputs.output_var = output_var

        registry_entry = FLOW_REGISTRY.get(flow_identifier)
        if not registry_entry:
            self.log_error(_("Unknown flow_identifier: {}").format(flow_identifier))
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        flow_class, method_name = registry_entry
        child_root_id = generate_root_id()

        try:
            flow_instance = flow_class(root_id=child_root_id, data=copy.deepcopy(flow_data))
            getattr(flow_instance, method_name)()
        except Exception as e:
            self.log_error(_("Failed to run {} (root_id={}): {}").format(flow_identifier, child_root_id, e))
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        if report_id and flow_id_field:
            try:
                Report.objects.filter(id=report_id).update(**{flow_id_field: child_root_id})
            except Exception as e:
                self.log_warning(_("Failed to store {} on report {}: {}").format(flow_id_field, report_id, e))

        self.log_info(_("Child pipeline {} ({}) submitted").format(child_root_id, flow_identifier))
        data.outputs.child_root_id = child_root_id
        data.outputs.start_time = datetime.now().isoformat()
        data.outputs.polling_timeout = polling_timeout
        return True

    def _schedule_inner_captured(self, data, parent_data, callback_data=None) -> bool:
        child_root_id = data.get_one_of_outputs("child_root_id")
        if not child_root_id:
            self.finish_schedule()
            return True

        raw_start_time = data.get_one_of_outputs("start_time")
        if not raw_start_time:
            self.log_error("start_time missing from outputs")
            self._set_result(data, 1)
            self.finish_schedule()
            return True
        start_time = datetime.fromisoformat(raw_start_time)
        polling_timeout = data.get_one_of_outputs("polling_timeout") or 3600

        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > polling_timeout:
            self.log_error(_("Child pipeline {} timed out after {:.0f}s").format(child_root_id, elapsed))
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        try:
            flow_tree = FlowTree.objects.get(root_id=child_root_id)
        except FlowTree.DoesNotExist:
            return True

        if flow_tree.status == StateType.FINISHED:
            self.log_info(_("Child pipeline {} finished successfully").format(child_root_id))
            self._set_result(data, 0)
            self.finish_schedule()
            return True
        elif flow_tree.status in (StateType.FAILED, StateType.REVOKED):
            self.log_error(_("Child pipeline {} ended with status {}").format(child_root_id, flow_tree.status))
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        return True


class RedisExerciseFlowRunnerComponent(Component):
    name = __name__
    code = "redis_exercise_flow_runner"
    bound_service = RedisExerciseFlowRunnerService


_KILL_SCRIPT = (
    "pkill -f redis-server || true; "
    "pkill -f tendisplus || true; "
    "pkill -f nutcracker || true; "
    "pkill -f predixy || true"
)


class RedisExerciseBestEffortCleanupService(RedisLogCapturingService, BkJobService):
    """Best-effort cleanup for exercise failures.

    Runs at the main pipeline level after all per-cluster sub-flows complete.
    Uses BkJobService's built-in __need_schedule__ + _schedule polling to:
      1. Submit a pkill job targeting all temp hosts (_execute_inner_captured)
      2. Poll until the job completes (_schedule from BkJobService)
      3. After job completes: decommission metadata, clean TbTendisRollbackTasks,
         reconcile reports (last, to capture as many logs as possible)

    Always returns True so it never blocks the pipeline.
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    def _execute_inner_captured(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        infos = global_data.get("infos", [])

        cleanup_hosts = []
        for info in infos:
            resource_applied = info.get("redis", [])
            if not resource_applied:
                continue
            temp_host_ip = resource_applied[0]["ip"]
            cluster = Cluster.objects.get(id=info["cluster_id"])
            bk_cloud_id = cluster.bk_cloud_id

            instances = StorageInstance.objects.filter(machine__ip=temp_host_ip, machine__bk_cloud_id=bk_cloud_id)
            if not instances.exists():
                self.log_info(_("No StorageInstance on {}, skipping").format(temp_host_ip))
                continue

            has_cluster_binding = False
            for inst in instances:
                if inst.cluster.count() > 0:
                    self.log_warning(
                        _(
                            "StorageInstance {}:{} is associated with a cluster, "
                            "skipping cleanup to protect production data"
                        ).format(temp_host_ip, inst.port)
                    )
                    has_cluster_binding = True
                    break
            if has_cluster_binding:
                continue

            ports = list(instances.values_list("port", flat=True))  # len(ports) should be 1
            cleanup_hosts.append({"ip": temp_host_ip, "bk_cloud_id": bk_cloud_id, "ports": ports})
            self.log_info(_("Will clean up {} (ports: {})").format(temp_host_ip, ports))

        data.outputs.cleanup_hosts = cleanup_hosts

        if not cleanup_hosts:
            self.log_info(_("No temp hosts require cleanup"))
            data.outputs.ext_result = True
            data.outputs.exec_ips = []
            return True

        target_ips = [{"bk_cloud_id": h["bk_cloud_id"], "ip": h["ip"]} for h in cleanup_hosts]
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM_drill_cleanup",
            "script_content": base64_encode(_KILL_SCRIPT),
            "script_language": 1,
            "target_server": {"ip_list": target_ips},
        }

        self.log_info(_("Submitting kill job for {} host(s)").format(len(cleanup_hosts)))
        resp = JobApi.fast_execute_script({**copy.deepcopy(redis_fast_execute_script_common_kwargs), **body}, raw=True)

        data.outputs.ext_result = resp
        data.outputs.exec_ips = [{"ip": h["ip"], "bk_cloud_id": h["bk_cloud_id"]} for h in cleanup_hosts]
        return True

    def _schedule_inner_captured(self, data, parent_data, callback_data=None) -> bool:
        # Explicitly invoke BkJobService's job-polling logic, then do post-cleanup work
        result = BkJobService._schedule(self, data, parent_data, callback_data)

        if not self.is_schedule_finished():
            return result

        global_data = data.get_one_of_inputs("global_data")
        ticket_id = global_data.get("uid")
        cleanup_hosts = data.get_one_of_outputs("cleanup_hosts") or []

        for host in cleanup_hosts:
            try:
                decommission_instances(ip=host["ip"], bk_cloud_id=host["bk_cloud_id"], ports=host["ports"])
                self.log_info(_("Decommissioned instances on {} ports {}").format(host["ip"], host["ports"]))
            except Exception as e:
                self.log_error(_("Failed to decommission instances on {}: {}").format(host["ip"], e))

        if ticket_id:
            try:
                deleted, _detailed = TbTendisRollbackTasks.objects.filter(related_rollback_bill_id=ticket_id).delete()
                if deleted:
                    self.log_info(_("Cleaned up {} TbTendisRollbackTasks for ticket {}").format(deleted, ticket_id))
            except Exception as e:
                self.log_error(_("Failed to clean TbTendisRollbackTasks: {}").format(e))

        infos = global_data.get("infos", [])
        for info in infos:
            report_id = info.get("report_id")
            try:
                self._reconcile_report(report_id)
            except Exception as e:
                self.log_error(_("Failed to reconcile report {}: {}").format(report_id, e))

        return result

    def _reconcile_report(self, report_id):
        """Ensure every report has task_message populated and a terminal stage."""
        if not report_id:
            return
        try:
            report = Report.objects.get(id=report_id)
        except Report.DoesNotExist:
            return

        task_msg = "\n".join(self.trans_data.task_msg) if self.trans_data and self.trans_data.task_msg else ""

        terminal_stages = {
            TaskStage.DONE,
            TaskStage.RESOURCE_APPLI_FAILED,
            TaskStage.ROLLBACK_FAILED,
            TaskStage.CLEANUP_FAILED,
        }
        if report.task_stage in {s.value for s in terminal_stages}:
            if task_msg:
                report.mark(task_message=task_msg)
            return
        report.mark(TaskStage.CLEANUP_FAILED, task_message=task_msg)
        self.log_info(_("Report {} marked CLEANUP_FAILED by best-effort cleanup").format(report_id))


class RedisExerciseBestEffortCleanupComponent(Component):
    name = __name__
    code = "redis_exercise_best_effort_cleanup"
    bound_service = RedisExerciseBestEffortCleanupService
