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
import shlex
from collections import defaultdict
from datetime import datetime
from typing import Optional

from django.core.cache import cache
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend import env
from backend.components import JobApi
from backend.constants import IP_PORT_DIVIDER
from backend.core.notify.constants import MsgType
from backend.db_meta.api.cluster.nosqlcomm.decommission import decommission_instances
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.flow.consts import DEFAULT_REDIS_START_PORT, StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.engine.bamboo.scene.common.machine_os_init import RecycleOutputContext
from backend.flow.engine.bamboo.scene.redis.redis_data_structure import RedisDataStructureFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldService
from backend.flow.plugins.components.collections.common.base_service import BaseService, BkJobService
from backend.flow.utils.base.flow_output import FlowOutputHandler
from backend.flow.utils.redis import redis_context_dataclass as flow_context
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext
from backend.flow.utils.redis.redis_rollback_exercise_resource import (
    all_infos_have_redis,
    apply_exercise_resources,
    get_effective_drill_infos,
    get_instance_machine,
    info_has_applied_redis,
)
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.ticket.constants import TicketStatus
from backend.ticket.models import Ticket
from backend.utils.basic import generate_root_id
from backend.utils.string import base64_encode

logger = logging.getLogger("json")


def merge_task_message(*messages: str) -> str:
    """Merge report task logs into one ordered, de-duplicated block.

    Node logs accumulate in ``trans_data.task_msg`` (append-only), so the same
    lines are re-submitted repeatedly -- e.g. a terminal-stage snapshot and the
    later cleanup pass both carry the full history up to that point. Merging per
    line preserves order and any explicit notes already on the report while
    dropping lines that were already persisted.
    """
    merged, seen = [], set()
    for message in messages:
        for line in (message or "").splitlines():
            if line in seen:
                continue
            seen.add(line)
            merged.append(line)
    return "\n".join(merged).strip()


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
            try:
                trans_data = getattr(flow_context, cls_name)()
            except AttributeError:
                logger.error("trans_data_dataclass '%s' not found on flow_context, using default", cls_name)
                trans_data = RedisRollbackExerciseContext()
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
        """Override to auto-capture error logs"""
        super().log_error(msg)
        self._append_to_task_info(msg, "error")

    def log_debug(self, msg: str):
        """Override to auto-capture debug logs"""
        super().log_debug(msg)
        self._append_to_task_info(msg, "debug")

    def render_report_message(self, existing_msg: str = "") -> str:
        """Build a report ``task_message`` from the captured node logs.

        ``existing_msg`` (the message already stored on the report) is kept first
        so explicit notes -- e.g. a build-time skip reason -- survive, then the
        append-only ``trans_data.task_msg`` is merged on top with duplicates removed.
        """
        captured = self.trans_data.task_msg if self.trans_data else None
        return merge_task_message(existing_msg, "\n".join(captured or []))

    @staticmethod
    def _get_effective_infos(data) -> list:
        global_data = data.get_one_of_inputs("global_data") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        return get_effective_drill_infos(global_data, trans_data)

    @classmethod
    def _get_effective_info(cls, data, info_index: Optional[int]):
        if info_index is None:
            return None
        infos = cls._get_effective_infos(data)
        if info_index >= len(infos):
            return None
        return infos[info_index]

    def _execute(self, data, parent_data) -> bool:
        self.init_trans_data(data)
        data.inputs.trans_data = self.trans_data
        result = self._execute_inner_captured(data, parent_data)
        data.outputs["trans_data"] = self.trans_data
        return result

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        self.init_trans_data(data)
        data.inputs.trans_data = self.trans_data
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
        kwargs = data.get_one_of_inputs("kwargs") or {}
        info_index = kwargs.get("info_index")
        if info_index is not None:
            info = self._get_effective_info(data, info_index)
            if info is None:
                self.log_warning(_("info_index {} out of range, skip alarm shield").format(info_index))
                return True
            redis_hosts = info.get("redis") or []
            if len(redis_hosts) == 1:
                temp_host_ip = redis_hosts[0]["ip"]
                dimensions = list(kwargs.get("dimensions") or [])
                dimensions.append({"name": "bk_target_ip", "values": [temp_host_ip]})
                kwargs["dimensions"] = dimensions
                kwargs["description"] = _("主机 {} Redis回档演练操作").format(temp_host_ip)
                data.inputs.kwargs = kwargs
            else:
                self.log_info(_("演练资源未申请，跳过告警屏蔽"))
                return True
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
    RESOURCE_DEPENDENT_STAGES = {
        TaskStage.ROLLBACK_STARTED,
        TaskStage.ROLLBACK_SUCCEEDED,
        TaskStage.ROLLBACK_FAILED,
        TaskStage.DONE,
        TaskStage.CLEANUP_FAILED,
    }

    def _execute_inner_captured(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        report_id = kwargs.get("report_id")
        stage = kwargs.get("stage")
        task_message = kwargs.get("task_message")
        info_index = kwargs.get("info_index")

        if (
            stage in self.RESOURCE_DEPENDENT_STAGES
            and info_index is not None
            and not info_has_applied_redis(self._get_effective_info(data, info_index))
        ):
            self.log_info(_("演练资源未申请，跳过标记 {}").format(stage))
            return True

        try:
            report = Report.objects.get(id=report_id)
        except Report.DoesNotExist:
            self.log_error(_("Report {} not found").format(report_id))
            return True
        except Exception as e:
            self.log_error(_("Failed to update report {}: {}").format(report_id, str(e)))
            return True

        if stage in self.TERMINAL_STAGES and not task_message and self.trans_data and self.trans_data.task_msg:
            task_message = self.render_report_message(report.task_message)

        try:
            # Embed per-report child-flow failed-node logs before mark() so each
            # report in a batch carries its own failure evidence (and AI analysis
            # can read it from task_message without re-fetching BKLog).
            from backend.db_services.redis.rollback.failure_analysis import embed_failed_node_logs

            task_message = embed_failed_node_logs(task_message, report, stage)
            report.mark(stage, task_message=task_message)
            self.log_info(_("Report {} marked as {}").format(report_id, stage))
            if stage in self.TERMINAL_STAGES:
                from backend.db_report.portrait.redis_ingest import ingest_rollback_exercise_portrait

                ingest_rollback_exercise_portrait(report)
        except Exception as e:
            self.log_error(_("Failed to update report {}: {}").format(report_id, str(e)))

        return True


class RedisExerciseReportUpdateComponent(Component):
    name = __name__
    code = "redis_exercise_report_update"
    bound_service = RedisExerciseReportUpdateService


CHILD2RUNNER_CACHE_PREFIX = "redis_rollback_drill:child2runner_node"


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

    def _finish_by_child_state(self, data, child_root_id: str, child_state):
        """Handle child state and return whether the runner can complete:

        - True: child reached a terminal state; schedule completed.
        - None: child is still running; keep polling.

        A child failure is a business outcome, not a runner failure. Preserve mode
        records the scene and lets the following pause node hold this branch for
        manual confirmation, keeping the parent ticket RUNNING.
        """
        if child_state == StateType.FINISHED:
            self.log_info(_("Child pipeline {} finished successfully").format(child_root_id))
            self._set_result(data, 0)
            self.finish_schedule()
            return True

        if child_state in (StateType.FAILED, StateType.REVOKED):
            if data.get_one_of_outputs("preserve_scene_on_failure"):
                # Preserve the child and complete this runner normally. The failure
                # output routes the branch to a manual-confirmation pause node.
                self.log_error(
                    _(
                        "Child pipeline {} ended with status {}, scene preserved for manual inspection. "
                        "Please investigate and complete the following confirmation node to mark the failure "
                        "and clean up."
                    ).format(child_root_id, child_state)
                )
                self._set_result(data, 1)
                self._preserve_scene(data, child_root_id)
                self.finish_schedule()
                return True

            self.log_error(_("Child pipeline {} ended with status {}").format(child_root_id, child_state))
            # FAILED means the pipeline errored out but sibling/pending nodes may still be running.
            # Revoke to ensure the whole tree is terminated. REVOKED is already terminal, skip.
            if child_state == StateType.FAILED:
                self._terminate_child_pipeline(child_root_id)
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        return None

    def _preserve_scene(self, data, child_root_id: str):
        """Mark this runner's report as SCENE_PRESERVED.

        Embed child failure-node logs before mark so task_message keeps evidence.
        Mark failures are logged only; the runner still completes so the
        following pause node can preserve the scene without failing the ticket.
        """
        kwargs = data.get_one_of_inputs("kwargs") or {}
        report_id = kwargs.get("report_id")
        if not report_id:
            self.log_warning(
                _("preserve scene skipped: no report_id in runner kwargs (child {})").format(child_root_id)
            )
            return
        try:
            report = Report.objects.get(id=report_id)
        except Report.DoesNotExist:
            self.log_warning(_("Report {} not found when preserving scene").format(report_id))
            return
        if report.task_stage == TaskStage.SCENE_PRESERVED:
            self.log_info(_("Report {} is already scene preserved, skip duplicate mark").format(report_id))
            return
        try:
            from backend.db_services.redis.rollback.failure_analysis import embed_failed_node_logs

            task_message = self.render_report_message(report.task_message)
            task_message = embed_failed_node_logs(task_message, report, TaskStage.SCENE_PRESERVED)
            report.mark(TaskStage.SCENE_PRESERVED, task_message=task_message)
            self.log_info(_("Report {} marked {} (scene preserved)").format(report_id, TaskStage.SCENE_PRESERVED))
        except Exception:
            self.log_error(_("Failed to mark report {} as scene preserved").format(report_id))
            logger.exception("failed to mark scene preserved report %s", report_id)

    def _terminate_child_pipeline(self, child_root_id: str):
        try:
            revoke_result = BambooEngine(root_id=child_root_id).revoke_pipeline()
            if not revoke_result.result:
                self.log_warning(
                    _("Failed to revoke child pipeline {}: {}").format(child_root_id, revoke_result.message)
                )
            else:
                self.log_info(_("Revoked child pipeline {}").format(child_root_id))
        except Exception:
            logger.warning(_("Exception while revoking child pipeline {}").format(child_root_id), exc_info=True)

    def _revoke_previous_child_pipeline(self, report_id, flow_id_field):
        """Force-retry safety net: revoke a leftover non-terminal child before submitting a new one.

        Preserve-mode nodes are not retryable, but is_force=True can still bypass that.
        If the old child root_id is left behind, the report field is overwritten and the
        old scene becomes an orphan pipeline. Revoke only when the FlowTree exists and is
        not FINISHED/REVOKED; failures are warnings only.
        """
        try:
            previous_root_id = Report.objects.filter(id=report_id).values_list(flow_id_field, flat=True).first()
        except Exception as e:
            self.log_warning(_("Failed to load previous child root for report {}: {}").format(report_id, e))
            return
        if not previous_root_id:
            return

        try:
            previous_tree = FlowTree.objects.filter(root_id=previous_root_id).only("status").first()
        except Exception as e:
            self.log_warning(_("Failed to load previous child tree {}: {}").format(previous_root_id, e))
            return
        if not previous_tree or previous_tree.status in (StateType.FINISHED, StateType.REVOKED):
            return

        self.log_info(
            _("Revoking previous leftover child pipeline {} before submitting a new child flow").format(
                previous_root_id
            )
        )
        self._terminate_child_pipeline(previous_root_id)

    def _execute_inner_captured(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        polling_interval = kwargs.get("polling_interval", 10)
        self.interval = StaticIntervalGenerator(polling_interval)

        flow_identifier = kwargs["flow_identifier"]
        report_id = kwargs.get("report_id")
        flow_id_field = kwargs.get("flow_id_field")
        polling_timeout = kwargs.get("polling_timeout", 3600)
        output_var = kwargs.get("output_var", "rollback_code")

        data.outputs.output_var = output_var
        # Preserve mode (flow passes not error_ignorable); stash on outputs for schedule.
        data.outputs.preserve_scene_on_failure = bool(kwargs.get("preserve_scene_on_failure", False))

        if kwargs.get("build_flow_data_from_global") or kwargs.get("build_delete_flow_data_from_global"):
            global_data = data.get_one_of_inputs("global_data") or {}
            info_index = kwargs.get("info_index")
            cluster_id = kwargs.get("cluster_id")
            infos = self._get_effective_infos(data)
            if info_index is None or info_index >= len(infos):
                self.log_warning(_("info_index invalid, skip child flow"))
                self._set_result(data, 1)
                self.finish_schedule()
                return True
            info = infos[info_index]
            redis_hosts = info.get("redis") or []
            if len(redis_hosts) != 1:
                self.log_info(_("演练资源未申请，跳过子流程"))
                self._set_result(data, 1)
                self.finish_schedule()
                return True
            try:
                cluster = Cluster.objects.get(id=cluster_id or info["cluster_id"])
            except Cluster.DoesNotExist:
                self.log_error(_("集群 {} 不存在").format(cluster_id or info.get("cluster_id")))
                self._set_result(data, 1)
                self.finish_schedule()
                return True

            from backend.flow.engine.bamboo.scene.redis.redis_rollback_exercise import RedisRollbackExerciseFlow

            if kwargs.get("build_delete_flow_data_from_global"):
                flow_data = RedisRollbackExerciseFlow.build_delete_flow_data(global_data, cluster)
            else:
                flow_data = RedisRollbackExerciseFlow.build_ds_flow_data(global_data, info, cluster)
                if not info.get("drill_prod_temp_instance_pairs"):
                    instance_ip = info.get("instance_ip")
                    instance_port = info.get("instance_port")
                    temp_host_ip = redis_hosts[0]["ip"]
                    info["drill_prod_temp_instance_pairs"] = [
                        [
                            "{}{}{}".format(instance_ip, IP_PORT_DIVIDER, instance_port),
                            "{}{}{}".format(temp_host_ip, IP_PORT_DIVIDER, DEFAULT_REDIS_START_PORT),
                        ]
                    ]
        else:
            flow_data = kwargs["flow_data"]

        registry_entry = FLOW_REGISTRY.get(flow_identifier)
        if not registry_entry:
            self.log_error(_("Unknown flow_identifier: {}").format(flow_identifier))
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        flow_class, method_name = registry_entry
        if report_id and flow_id_field and data.get_one_of_outputs("preserve_scene_on_failure"):
            self._revoke_previous_child_pipeline(report_id, flow_id_field)
        child_root_id = generate_root_id()

        try:
            flow_instance = flow_class(root_id=child_root_id, data=copy.deepcopy(flow_data))
            launch_result = getattr(flow_instance, method_name)()
        except Exception as e:
            self.log_error(_("Failed to run {} (root_id={}): {}").format(flow_identifier, child_root_id, e))
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        if launch_result is False:
            self.log_error(
                _("Child pipeline {} ({}) was rejected before submission").format(child_root_id, flow_identifier)
            )
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

        runner_node_id = self.runtime_attrs.get("id")
        parent_root_id = self.runtime_attrs.get("root_pipeline_id")
        if runner_node_id and parent_root_id:
            cache.set(
                f"{CHILD2RUNNER_CACHE_PREFIX}:{child_root_id}",
                {"runner_node_id": runner_node_id, "parent_root_id": parent_root_id},
                polling_timeout,
            )
        data.outputs.start_time = datetime.now().isoformat()
        data.outputs.polling_timeout = polling_timeout
        return True

    def _schedule_inner_captured(self, data, parent_data, callback_data=None) -> bool:
        child_root_id = data.get_one_of_outputs("child_root_id")
        if not child_root_id:
            self.finish_schedule()
            return True

        if callback_data:
            # BambooEngine.callback wraps desc under {"description": desc}, so unwrap before reading.
            # Fall back to the top-level dict in case a caller bypasses BambooEngine and stores the desc directly.
            payload = callback_data.get("description")
            if not isinstance(payload, dict):
                payload = callback_data
            callback_child_root_id = payload.get("child_root_id")
            callback_child_state = payload.get("child_state")

            if not callback_child_root_id:
                self.log_warning("Received callback_data without child_root_id, ignoring fast-path")
            elif callback_child_root_id != child_root_id:
                self.log_warning(
                    _("Callback child root id mismatch: expected {}, got {}").format(
                        child_root_id, callback_child_root_id
                    )
                )
            else:
                outcome = self._finish_by_child_state(data, child_root_id, callback_child_state)
                if outcome is not None:
                    return outcome

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
            if data.get_one_of_outputs("preserve_scene_on_failure"):
                # Preserve: do not revoke — the hung child is the scene. Complete
                # the runner and let the following pause node hold the branch.
                self.log_error(
                    _(
                        "Child pipeline {} timed out after {:.0f}s, still running and scene preserved for manual "
                        "inspection. Please investigate and complete the following confirmation node to mark "
                        "the failure and clean up."
                    ).format(child_root_id, elapsed)
                )
                self._set_result(data, 1)
                self._preserve_scene(data, child_root_id)
                self.finish_schedule()
                return True
            self.log_error(_("Child pipeline {} timed out after {:.0f}s").format(child_root_id, elapsed))
            self._terminate_child_pipeline(child_root_id)
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        try:
            flow_tree = FlowTree.objects.get(root_id=child_root_id)
        except FlowTree.DoesNotExist:
            return True

        outcome = self._finish_by_child_state(data, child_root_id, flow_tree.status)
        # None (still running) -> keep polling; terminal states finish the runner.
        return True if outcome is None else outcome


class RedisExerciseFlowRunnerComponent(Component):
    name = __name__
    code = "redis_exercise_flow_runner"
    bound_service = RedisExerciseFlowRunnerService


class RedisExerciseRevokeAppliedHostsService(RedisLogCapturingService):
    """Publish rollback exercise resource hosts for the standard RECYCLE_APPLY_HOST flow."""

    @staticmethod
    def _normalize_recycle_host(host: dict) -> Optional[dict]:
        if not isinstance(host, dict):
            return None

        ip = host.get("ip")
        bk_cloud_id = host.get("bk_cloud_id")
        bk_host_id = host.get("bk_host_id") or host.get("host_id")
        if not (ip and bk_cloud_id is not None and bk_host_id is not None):
            return None

        normalized = {
            "ip": ip,
            "bk_cloud_id": bk_cloud_id,
            "bk_host_id": bk_host_id,
            "remark": host.get("remark", _("Redis rollback exercise revoked")),
        }
        return normalized

    @staticmethod
    def _standardize_recycle_hosts(recycle_hosts: list) -> list:
        if not recycle_hosts:
            return []

        remarks = {host["bk_host_id"]: host.get("remark", "") for host in recycle_hosts}
        standardized_hosts = ResourceHandler.standardized_resource_host(recycle_hosts)
        if len(standardized_hosts) < len(recycle_hosts):
            missing_host_ids = {host["bk_host_id"] for host in recycle_hosts} - {
                host["bk_host_id"] for host in standardized_hosts
            }
            logger.warning("Recycle hosts dropped after CMDB normalization: %s", sorted(missing_host_ids))
        for host in standardized_hosts:
            host["remark"] = remarks.get(host["bk_host_id"], "")
        return standardized_hosts

    @classmethod
    def _collect_recycle_hosts(cls, infos: list) -> list:
        hosts_by_id = {}
        for info in infos or []:
            for host in info.get("redis", []) or []:
                normalized = cls._normalize_recycle_host(host)
                if normalized is not None:
                    host_id = normalized["bk_host_id"]
                    if host_id not in hosts_by_id:
                        hosts_by_id[host_id] = normalized
                    else:
                        hosts_by_id[host_id].update(
                            {
                                key: value
                                for key, value in normalized.items()
                                if value and not hosts_by_id[host_id].get(key)
                            }
                        )
        return cls._standardize_recycle_hosts(list(hosts_by_id.values()))

    def _execute_inner_captured(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}
        recycle_hosts = self._collect_recycle_hosts(global_data.get("infos", []))
        if not recycle_hosts:
            self.log_info(_("No applied redis hosts found for revoke recycle output"))
        else:
            self.log_info(_("Published {} redis host(s) for revoke recycle").format(len(recycle_hosts)))

        FlowOutputHandler(RecycleOutputContext.ToResourceSerializer).insert_data(
            global_data["job_root_id"], recycle_hosts
        )
        return True


class RedisExerciseRevokeAppliedHostsComponent(Component):
    name = __name__
    code = "redis_exercise_revoke_applied_hosts"
    bound_service = RedisExerciseRevokeAppliedHostsService


class RedisExerciseResourceApplyService(RedisLogCapturingService):
    """Batch-apply redis drill hosts via DBResourceApi and inject ticket recycle metadata."""

    @staticmethod
    def _instance_addr(info: dict) -> str:
        return "{}{}{}".format(info.get("instance_ip"), IP_PORT_DIVIDER, info.get("instance_port"))

    @classmethod
    def _resolve_cluster_domains(cls, infos: list) -> dict:
        missing_cluster_ids = {
            info["cluster_id"] for info in infos if info.get("cluster_id") and not info.get("cluster_domain")
        }
        if not missing_cluster_ids:
            return {}
        return dict(Cluster.objects.filter(id__in=missing_cluster_ids).values_list("id", "immute_domain"))

    @classmethod
    def _format_disk_gb(cls, redis_host: dict) -> Optional[int]:
        disk_gb = redis_host.get("bk_disk")
        if disk_gb not in (None, ""):
            try:
                disk_value = int(disk_gb)
                if disk_value > 0:
                    return disk_value
            except (TypeError, ValueError):
                pass

        storage_device = redis_host.get("storage_device") or {}
        total = 0
        for item in storage_device.values():
            if not isinstance(item, dict):
                continue
            try:
                total += int(item.get("size") or 0)
            except (TypeError, ValueError):
                continue
        return total or None

    @classmethod
    def _format_mem_gb(cls, mem_mb) -> str:
        """Render ``bk_mem`` (stored in MB across db_meta / resource pool) as GB.

        Whole values collapse to ints (16GB) and fractional ones keep one
        decimal (3.5GB), so 3619MB no longer prints as the bogus "3619GB".
        """
        if mem_mb in (None, ""):
            return ""
        try:
            gb = int(mem_mb) / 1024
        except (TypeError, ValueError):
            return ""
        if gb <= 0:
            return ""
        return "{:g}GB".format(round(gb, 1))

    @classmethod
    def _format_spec_details(cls, redis_host: dict) -> str:
        cpu = redis_host.get("bk_cpu")
        mem_label = cls._format_mem_gb(redis_host.get("bk_mem"))
        disk_gb = cls._format_disk_gb(redis_host)

        parts = []
        if cpu not in (None, ""):
            parts.append("{} cores".format(cpu))
        if mem_label:
            parts.append("{} RAM".format(mem_label))
        if disk_gb:
            parts.append("{}GB disk".format(disk_gb))
        return " ".join(parts)

    @classmethod
    def _resolve_bk_svr_device_cls_name(cls, redis_host: dict) -> str:
        for key in ("bk_svr_device_cls_name", "device_class"):
            value = redis_host.get(key)
            if value:
                return str(value)
        return ""

    @classmethod
    def _machine_to_spec_host_dict(cls, machine) -> dict:
        spec_config = machine.spec_config or {}
        cpu_info = spec_config.get("cpu") or {}
        mem_info = spec_config.get("mem") or {}
        cpu = cpu_info.get("min") or cpu_info.get("max") or ""
        # spec_config.mem is GB; normalize to MB so bk_mem stays consistent with the resource pool.
        mem_gb = mem_info.get("min") or mem_info.get("max") or 0
        try:
            mem_mb = int(mem_gb) * 1024 or ""
        except (TypeError, ValueError):
            mem_mb = ""
        return {
            "bk_cpu": cpu,
            "bk_mem": mem_mb,
            "storage_device": machine.storage_device or {},
            "bk_svr_device_cls_name": machine.bk_svr_device_cls_name or "",
            "device_class": machine.bk_svr_device_cls_name or "",
        }

    @classmethod
    def _resolve_source_machine_spec(cls, info: dict, cluster, machine_cache: dict) -> str:
        cache_key = (info.get("cluster_id"), info.get("instance_ip"), info.get("instance_port"))
        if cache_key in machine_cache:
            return machine_cache[cache_key]

        machine = get_instance_machine(info, cluster) if cluster else None
        spec_label = cls._format_spec_details(cls._machine_to_spec_host_dict(machine)) if machine else ""
        machine_cache[cache_key] = spec_label
        return spec_label

    @classmethod
    def _format_applied_host_spec(cls, redis_host: dict) -> str:
        spec_details = cls._format_spec_details(redis_host)
        device_cls_name = cls._resolve_bk_svr_device_cls_name(redis_host)
        if spec_details and device_cls_name:
            return "{} {}".format(spec_details, device_cls_name)
        return spec_details or device_cls_name

    @classmethod
    def _append_original_instance_lines(
        cls,
        lines: list,
        entries: list,
        cluster,
        machine_cache: dict,
        *,
        spec_in_parens: bool = False,
    ):
        for entry in sorted(entries, key=lambda item: cls._instance_addr(item["info"])):
            info = entry["info"]
            instance_addr = cls._instance_addr(info)
            orig_spec = cls._resolve_source_machine_spec(info, cluster, machine_cache)
            if orig_spec and spec_in_parens:
                lines.append("        {} ({})".format(instance_addr, orig_spec))
            elif orig_spec:
                lines.append("        {} {}".format(instance_addr, orig_spec))
            else:
                lines.append("        {}".format(instance_addr))

    @classmethod
    def _append_pending_instance_lines(
        cls,
        lines: list,
        pending_infos: list,
        cluster,
        machine_cache: dict,
        *,
        no_resource_label: str = "",
        spec_in_parens: bool = False,
    ):
        if not pending_infos:
            return
        if no_resource_label:
            lines.append("    {}".format(no_resource_label))
        for info in sorted(pending_infos, key=cls._instance_addr):
            instance_addr = cls._instance_addr(info)
            orig_spec = cls._resolve_source_machine_spec(info, cluster, machine_cache)
            indent = "        " if no_resource_label else "    "
            if orig_spec and spec_in_parens:
                lines.append("{}{} ({})".format(indent, instance_addr, orig_spec))
            elif orig_spec:
                lines.append("{}{} {}".format(indent, instance_addr, orig_spec))
            else:
                lines.append("{}{}".format(indent, instance_addr))

    @classmethod
    def _build_resource_apply_log_summary(
        cls,
        infos: list,
        *,
        header: str,
        include_applied_ip: bool = True,
        no_resource_label: str = "",
    ) -> str:
        cluster_domain_map = cls._resolve_cluster_domains(infos)
        cluster_ids = {info["cluster_id"] for info in infos if info.get("cluster_id")}
        cluster_objects = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}

        clusters = defaultdict(lambda: {"domain": "", "applied_hosts": defaultdict(list), "pending": []})

        for info in infos:
            cluster_id = info.get("cluster_id")
            if cluster_id is None:
                continue
            cluster_domain = info.get("cluster_domain") or cluster_domain_map.get(cluster_id) or ""
            clusters[cluster_id]["domain"] = cluster_domain or clusters[cluster_id]["domain"]

            redis_hosts = info.get("redis") or []
            if include_applied_ip and redis_hosts:
                applied_ip = redis_hosts[0].get("ip") or ""
                clusters[cluster_id]["applied_hosts"][applied_ip].append({"info": info, "redis_host": redis_hosts[0]})
            else:
                clusters[cluster_id]["pending"].append(info)

        lines = [header] if header else []
        machine_cache = {}
        for cluster_id in sorted(clusters):
            cluster_data = clusters[cluster_id]
            cluster = cluster_objects.get(cluster_id)
            cluster_label = cluster_data["domain"] or str(cluster_id)
            lines.append(cluster_label)

            for applied_ip in sorted(cluster_data["applied_hosts"]):
                entries = cluster_data["applied_hosts"][applied_ip]
                spec_label = cls._format_spec_details(entries[0]["redis_host"])
                if spec_label:
                    lines.append("    {} ({})".format(applied_ip, spec_label))
                else:
                    lines.append("    {}".format(applied_ip))
                cls._append_original_instance_lines(lines, entries, cluster, machine_cache)

            cls._append_pending_instance_lines(
                lines,
                cluster_data["pending"],
                cluster,
                machine_cache,
                no_resource_label=no_resource_label,
                spec_in_parens=bool(no_resource_label),
            )

        return "\n".join(lines)

    def _log_applied_resources(self, infos: list, request_id: str = ""):
        if self.trans_data and getattr(self.trans_data, "resource_apply_logged", False):
            return

        host_count = sum(1 for info in infos if info.get("redis"))
        if not host_count:
            return

        header = _("演练资源申请完成，共 {} 台主机").format(host_count)
        if request_id:
            header = "{} request_id={}".format(header, request_id)
        self.log_info(self._build_resource_apply_log_summary(infos, header=header))
        if self.trans_data:
            self.trans_data.resource_apply_logged = True

    def _log_resource_apply_failure(self, infos: list, error_message: str):
        header = _("演练资源申请失败: {}").format(error_message)
        self.log_error(
            self._build_resource_apply_log_summary(
                infos,
                header=header,
                include_applied_ip=False,
                no_resource_label=_("(no resource)"),
            )
        )

    def _inject_ticket_details(
        self,
        ticket_id: int,
        applied_hosts: list,
        node_infos: dict,
        resource_request_id: str,
        summary: list,
    ):
        standardized = ResourceHandler.standardized_resource_host(applied_hosts)
        ticket = Ticket.objects.get(id=ticket_id)
        ticket.details["recycle_hosts"] = standardized
        ticket.details["nodes"] = node_infos
        ticket.details["resource_request_id"] = resource_request_id
        ticket.details["resource_apply_summary"] = summary
        ticket.details["immediate_recycle"] = True
        ticket.details["send_msg_config"] = {
            status: {MsgType.RTX: True} if status == TicketStatus.FAILED else {}
            for status in TicketStatus.get_values()
        }
        ticket.save(update_fields=["details"])

    def _persist_applied_infos(self, infos: list):
        if self.trans_data is None:
            return
        self.trans_data.applied_infos = copy.deepcopy(infos)

    def _execute_inner_captured(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}
        infos = global_data.get("infos") or []
        ticket_id = global_data.get("uid")

        if all_infos_have_redis(infos):
            self.log_info(_("演练资源已申请，跳过重复申请"))
            self._persist_applied_infos(infos)
            self._log_applied_resources(infos)
            return True

        result = apply_exercise_resources(global_data, global_data.get("job_root_id") or self.root_id)

        if result.skipped_idempotent:
            self.log_info(_("演练资源已申请，跳过重复申请"))
            self._persist_applied_infos(infos)
            self._log_applied_resources(infos)
            return True

        if not result.success:
            warn_msg = _("WARN: no available resources")
            fail_msg = result.error_message or warn_msg
            self._persist_applied_infos(infos)
            self._log_resource_apply_failure(infos, fail_msg)
            if result.node_infos and ticket_id:
                partial_hosts = [
                    {
                        "bk_host_id": host["bk_host_id"],
                        "ip": host["ip"],
                        "bk_cloud_id": host["bk_cloud_id"],
                    }
                    for hosts in result.node_infos.values()
                    for host in hosts
                ]
                if partial_hosts:
                    self._inject_ticket_details(
                        ticket_id,
                        partial_hosts,
                        result.node_infos,
                        result.resource_request_id,
                        result.resource_apply_summary,
                    )
            for info in infos:
                report_id = info.get("report_id")
                if not report_id:
                    continue
                try:
                    report = Report.objects.get(id=report_id)
                    report.mark(TaskStage.SKIPPED, task_message=fail_msg)
                except Report.DoesNotExist:
                    self.log_warning(_("Report {} not found when marking resource skip").format(report_id))
            return True

        applied_hosts = []
        for hosts in result.node_infos.values():
            for host in hosts:
                applied_hosts.append(
                    {
                        "bk_host_id": host["bk_host_id"],
                        "ip": host["ip"],
                        "bk_cloud_id": host["bk_cloud_id"],
                    }
                )

        if applied_hosts and ticket_id:
            self._inject_ticket_details(
                ticket_id,
                applied_hosts,
                result.node_infos,
                result.resource_request_id,
                result.resource_apply_summary,
            )

        self._persist_applied_infos(infos)
        self._log_applied_resources(infos, result.resource_request_id)

        for info in infos:
            report_id = info.get("report_id")
            if not report_id:
                continue
            try:
                report = Report.objects.get(id=report_id)
                if info.get("redis"):
                    report.mark(TaskStage.RESOURCE_APPLI_SUCCEEDED)
            except Report.DoesNotExist:
                self.log_warning(_("Report {} not found when marking resource success").format(report_id))

        return True


class RedisExerciseResourceApplyComponent(Component):
    name = __name__
    code = "redis_exercise_resource_apply"
    bound_service = RedisExerciseResourceApplyService


class RedisExerciseBestEffortCleanupService(RedisLogCapturingService, BkJobService):
    """Best-effort cleanup for exercise failures.

    Runs at the main pipeline level after all per-cluster sub-flows complete.
    Uses BkJobService's built-in __need_schedule__ + _schedule polling to:
      1. Submit a guarded per-port cleanup job targeting temp hosts (_execute_inner_captured)
      2. Poll until the job completes (_schedule from BkJobService)
      3. After job completes: decommission metadata, clean TbTendisRollbackTasks,
         reconcile reports (last, to capture as many logs as possible)

    Always returns True so it never blocks the pipeline.
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    @staticmethod
    def _parse_ip_port(instance):
        if not isinstance(instance, str):
            return None
        ip, sep, port = instance.rpartition(":")
        if not sep:
            return None
        try:
            return ip, int(port)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _parse_instance_set(cls, instances) -> set:
        parsed = set()
        if isinstance(instances, dict):
            iterator = []
            for key, value in instances.items():
                if isinstance(key, str):
                    iterator.append(key)
                if isinstance(value, (list, tuple, set)):
                    iterator.extend(value)
                else:
                    iterator.append(value)
        elif isinstance(instances, (list, tuple, set)):
            iterator = instances
        else:
            iterator = []

        for instance in iterator:
            parsed_instance = cls._parse_ip_port(instance)
            if parsed_instance:
                parsed.add(parsed_instance)
        return parsed

    @classmethod
    def _parse_prod_temp_pairs(cls, pairs) -> tuple:
        prod_addrs, temp_addrs = set(), set()
        if isinstance(pairs, dict):
            iterator = pairs.items()
        elif isinstance(pairs, (list, tuple, set)):
            iterator = pairs
        else:
            iterator = []

        for pair in iterator:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            prod_addr = cls._parse_ip_port(pair[0])
            temp_addr = cls._parse_ip_port(pair[1])
            if prod_addr:
                prod_addrs.add(prod_addr)
            if temp_addr:
                temp_addrs.add(temp_addr)
        return prod_addrs, temp_addrs

    def _extract_allowlisted_temp_ports(
        self,
        temp_host_ip: str,
        prod_temp_instance_pairs: list,
        temp_instance_range: Optional[list] = None,
        prod_instance_range: Optional[list] = None,
        task_id: Optional[int] = None,
    ) -> list:
        task_temp_addrs = self._parse_instance_set(temp_instance_range)
        task_prod_addrs = self._parse_instance_set(prod_instance_range)
        pair_prod_addrs, pair_temp_addrs = self._parse_prod_temp_pairs(prod_temp_instance_pairs)
        if not pair_temp_addrs:
            if task_id is not None:
                self.log_warning(
                    _("Rollback task {} has no prod/temp instance pairs, skipping work-dir cleanup").format(task_id)
                )
            return []

        if task_temp_addrs:
            allowed_temp_addrs = task_temp_addrs & pair_temp_addrs
        else:
            allowed_temp_addrs = set(pair_temp_addrs)

        unsafe_addrs = allowed_temp_addrs & (task_prod_addrs | pair_prod_addrs)
        if unsafe_addrs:
            label = _("Rollback task {}").format(task_id) if task_id is not None else _("Drill fallback")
            self.log_warning(
                _("{} temp addresses overlap source/prod addresses {}, skipping them").format(
                    label, sorted("{}:{}".format(ip, port) for ip, port in unsafe_addrs)
                )
            )
            allowed_temp_addrs -= unsafe_addrs

        ports = set()
        for ip, port in allowed_temp_addrs:
            if ip == temp_host_ip:
                ports.add(port)
        return sorted(ports)

    def _get_task_temp_ports(self, ticket_id, bk_biz_id, cluster_id, temp_host_ip: str) -> list:
        if not ticket_id or not bk_biz_id or not cluster_id:
            return []
        tasks = TbTendisRollbackTasks.objects.filter(
            related_rollback_bill_id=ticket_id,
            bk_biz_id=bk_biz_id,
            prod_cluster_id=cluster_id,
        )
        ports = set()
        for task in tasks:
            for port in self._extract_allowlisted_temp_ports(
                temp_host_ip,
                task.prod_temp_instance_pairs,
                temp_instance_range=task.temp_instance_range,
                prod_instance_range=task.prod_instance_range,
                task_id=task.id,
            ):
                ports.add(port)
        return sorted(ports)

    @classmethod
    def _get_drill_prod_temp_instance_pairs(cls, info: dict):
        pairs = info.get("drill_prod_temp_instance_pairs")
        if pairs:
            return pairs
        resource_applied = info.get("redis") or []
        instance_ip = info.get("instance_ip")
        instance_port = info.get("instance_port")
        if not resource_applied or instance_ip is None or instance_port is None:
            return None
        temp_host_ip = resource_applied[0]["ip"]
        return [
            [
                "{}{}{}".format(instance_ip, IP_PORT_DIVIDER, instance_port),
                "{}{}{}".format(temp_host_ip, IP_PORT_DIVIDER, DEFAULT_REDIS_START_PORT),
            ]
        ]

    def _get_drill_fallback_temp_ports(self, info: dict, temp_host_ip: str) -> list:
        pairs = self._get_drill_prod_temp_instance_pairs(info)
        if not pairs:
            return []
        return self._extract_allowlisted_temp_ports(temp_host_ip, pairs)

    @staticmethod
    def _get_rollback_task_ticket_id(global_data: dict):
        return global_data.get("parent_ticket") or global_data.get("uid")

    def _collect_cleanup_hosts(self, global_data: dict) -> list:
        ticket_id = self._get_rollback_task_ticket_id(global_data)
        ticket_bk_biz_id = global_data.get("bk_biz_id")
        cleanup_hosts = []
        infos = get_effective_drill_infos(global_data, self.trans_data)

        for info in infos:
            resource_applied = info.get("redis", [])
            if not resource_applied:
                continue
            temp_host_ip = resource_applied[0]["ip"]

            try:
                cluster = Cluster.objects.get(id=info["cluster_id"])
            except Exception as e:
                self.log_warning(_("Failed to load cluster {}: {}").format(info.get("cluster_id"), e))
                continue

            instances = list(
                StorageInstance.objects.filter(machine__ip=temp_host_ip, machine__bk_cloud_id=cluster.bk_cloud_id)
            )
            has_unexpected_cluster_binding = False
            for inst in instances:
                bound_cluster_ids = set(inst.cluster.values_list("id", flat=True))
                unexpected_cluster_ids = bound_cluster_ids - {cluster.id}
                if unexpected_cluster_ids:
                    self.log_warning(
                        _(
                            "StorageInstance {}:{} is associated with unexpected cluster(s) {}, "
                            "skipping cleanup to protect production data"
                        ).format(temp_host_ip, inst.port, sorted(unexpected_cluster_ids))
                    )
                    has_unexpected_cluster_binding = True
                    break
            if has_unexpected_cluster_binding:
                continue

            ports = self._get_task_temp_ports(ticket_id, ticket_bk_biz_id, cluster.id, temp_host_ip)
            if not ports:
                ports = self._get_drill_fallback_temp_ports(info, temp_host_ip)
                if ports:
                    self.log_info(
                        _("Using drill ticket pairs fallback for {} (no TbTendisRollbackTasks)").format(temp_host_ip)
                    )
            source_instance = self._parse_ip_port("{}:{}".format(info.get("instance_ip"), info.get("instance_port")))
            if source_instance and source_instance[0] == temp_host_ip and source_instance[1] in ports:
                self.log_warning(
                    _(
                        "Cleanup target {}:{} matches the drill source instance, "
                        "removing it from work-dir cleanup targets"
                    ).format(source_instance[0], source_instance[1])
                )
                ports = [port for port in ports if port != source_instance[1]]
            if not ports:
                self.log_warning(
                    _("No rollback task temp ports found for {}, skipping work-dir cleanup").format(temp_host_ip)
                )
                continue

            cleanup_hosts.append({"ip": temp_host_ip, "bk_cloud_id": cluster.bk_cloud_id, "ports": ports})
            self.log_info(
                _("Will clean up {} in bk_cloud_id {} (ports: {})").format(temp_host_ip, cluster.bk_cloud_id, ports)
            )

        return cleanup_hosts

    @staticmethod
    def _build_cleanup_script(cleanup_hosts: list) -> str:
        host_cases = []
        for host in cleanup_hosts:
            ports = " ".join(str(port) for port in sorted(host["ports"]))
            host_cases.append(
                "    {}) cleanup_ports={}; matched_ip={}; break ;;".format(
                    shlex.quote(host["ip"]),
                    shlex.quote(ports),
                    shlex.quote(host["ip"]),
                )
            )
        case_body = "\n".join(host_cases) or "    *) cleanup_ports='' ;;"

        return """current_ips="$(hostname -I 2>/dev/null || true)"
if command -v ip >/dev/null 2>&1; then
  current_ips="$current_ips $(ip -o -4 addr show 2>/dev/null | awk '{{print $4}}' | cut -d/ -f1 || true)"
fi
cleanup_ports=""
matched_ip=""
for current_ip in $current_ips; do
  case "$current_ip" in
{case_body}
  esac
done

if [ -z "$cleanup_ports" ]; then
  echo "No allowlisted redis work dirs for this host, skip work-dir cleanup"
  exit 0
fi

if [ -n "$REDIS_DATA_DIR" ]; then
  data_root="$REDIS_DATA_DIR"
elif [ -d /data1/redis ]; then
  data_root="/data1"
elif [ -d /data/redis ]; then
  data_root="/data"
else
  echo "No redis data dir found on $matched_ip, skip work-dir cleanup"
  exit 0
fi

redis_dir="$data_root/redis"
backend_pattern=""
for port in $cleanup_ports; do
  if [ -z "$backend_pattern" ]; then
    backend_pattern="$matched_ip:$port"
  else
    backend_pattern="$backend_pattern|$matched_ip:$port"
  fi
done

for port in $cleanup_ports; do
  case "$port" in
    ""|*[!0-9]*)
      echo "Skip invalid redis port: $port"
      continue
      ;;
  esac

  inst_dir="$redis_dir/$port"
  case "$inst_dir" in
    "$redis_dir"/[0-9]*) ;;
    *)
      echo "Unsafe redis work dir $inst_dir, skip"
      continue
      ;;
  esac

  if [ ! -d "$inst_dir" ]; then
    echo "Redis work dir $inst_dir does not exist, skip"
    continue
  fi

  conf_file="$inst_dir/redis.conf"
  if [ -f "$conf_file" ] && ! grep -Eq "^[[:space:]]*port[[:space:]]+$port([[:space:]]|$)" "$conf_file"; then
    echo "Redis work dir $inst_dir has mismatched redis.conf port, skip"
    continue
  fi

  echo "Stop allowlisted redis processes for $inst_dir / port $port"
  pkill -f "$inst_dir" 2>/dev/null || true
  pkill -f "(redis-server|tendis[a-z_+-]*).*[.:]$port([^0-9]|$)" 2>/dev/null || true
  pkill -f "$data_root/(predixy|twemproxy-0.2.4)/[0-9]+/" 2>/dev/null || true
  sleep 3

  if ps -ef | grep -E "($inst_dir|(redis-server|tendis[a-z_+-]*).*[.:]$port([^0-9]|$))" | grep -v grep; then
    echo "Allowlisted redis process still exists for port $port, skip $inst_dir"
    continue
  fi

  echo "Remove allowlisted redis work dir $inst_dir"
  rm -rf -- "$inst_dir"
done

for proxy_dir in /data1/predixy/[0-9]* /data/predixy/[0-9]* /data1/twemproxy-0.2.4/[0-9]* /data/twemproxy-0.2.4/[0-9]*; do
  [ -d "$proxy_dir" ] || continue
  case "$proxy_dir" in
    /data1/predixy/[0-9]*|/data/predixy/[0-9]*|/data1/twemproxy-0.2.4/[0-9]*|/data/twemproxy-0.2.4/[0-9]*) ;;
    *)
      echo "Unsafe proxy work dir $proxy_dir, skip"
      continue
      ;;
  esac
  if ! grep -RqsE "$backend_pattern" "$proxy_dir"; then
    echo "Proxy work dir $proxy_dir does not reference allowlisted backends, skip"
    continue
  fi

  echo "Stop allowlisted proxy process for $proxy_dir"
  pkill -f "$proxy_dir/" 2>/dev/null || true
  sleep 2
  if ps -ef | grep -F "$proxy_dir/" | grep -v grep; then
    echo "Proxy process still exists for $proxy_dir, skip removal"
    continue
  fi

  echo "Remove allowlisted proxy work dir $proxy_dir"
  rm -rf -- "$proxy_dir"
done
""".format(
            case_body=case_body,
        )

    def _revoke_leftover_child_flows(self, global_data: dict):
        """Revoke leftover non-terminal child pipelines before cleanup so they do not race the cleanup script.

        Non-terminal = FlowTree status not FINISHED/REVOKED. A FAILED tree may still have
        RUNNING siblings (see the runner comments) and must be revoked as a whole.
        RUNNING/CREATED/READY are revoked directly. In non-preserve mode the runner already
        revoked on failure (tree is REVOKED), so this is a no-op.
        """
        child_root_ids = []
        for info in get_effective_drill_infos(global_data, self.trans_data):
            report_id = info.get("report_id")
            if not report_id:
                continue
            try:
                report = Report.objects.filter(id=report_id).only("rollback_flow_obj_id", "delete_flow_obj_id").first()
            except Exception as e:
                self.log_warning(_("Failed to load report {} for leftover child revoke: {}").format(report_id, e))
                continue
            if not report:
                continue
            for root_id in (report.rollback_flow_obj_id, report.delete_flow_obj_id):
                if root_id:
                    child_root_ids.append(root_id)

        if not child_root_ids:
            return

        try:
            leftover_root_ids = list(
                FlowTree.objects.filter(root_id__in=child_root_ids)
                .exclude(status__in=[StateType.FINISHED, StateType.REVOKED])
                .values_list("root_id", flat=True)
            )
        except Exception as e:
            self.log_error(_("Failed to query leftover child flows for revoke: {}").format(e))
            return

        for root_id in leftover_root_ids:
            try:
                revoke_result = BambooEngine(root_id=root_id).revoke_pipeline()
                if not revoke_result.result:
                    self.log_warning(
                        _("Failed to revoke leftover child pipeline {}: {}").format(root_id, revoke_result.message)
                    )
                else:
                    self.log_info(_("Revoked leftover child pipeline {}").format(root_id))
            except Exception as e:
                self.log_warning(_("Exception while revoking leftover child pipeline {}: {}").format(root_id, e))

    def _execute_inner_captured(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}

        # Step 0: revoke leftover children (including FAILED trees with RUNNING siblings) so they do not race cleanup
        self._revoke_leftover_child_flows(global_data)

        self.log_info(_("Step 1/4: Collecting cleanup targets from rollback task metadata"))
        cleanup_hosts = self._collect_cleanup_hosts(global_data)

        data.outputs.cleanup_hosts = cleanup_hosts

        if not cleanup_hosts:
            self.log_info(_("No temp hosts require cleanup"))
            data.outputs.ext_result = True
            data.outputs.exec_ips = []
            return True

        target_ips = [{"bk_cloud_id": h["bk_cloud_id"], "ip": h["ip"]} for h in cleanup_hosts]
        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM_drill_cleanup",
            "script_content": base64_encode(self._build_cleanup_script(cleanup_hosts)),
            "script_language": 1,
            "target_server": {"ip_list": target_ips},
        }

        self.log_info(_("Step 2/4: Submitting kill job for {} host(s)").format(len(cleanup_hosts)))
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
        ticket_id = self._get_rollback_task_ticket_id(global_data)
        cleanup_hosts = data.get_one_of_outputs("cleanup_hosts") or []

        self.log_info(_("Step 3/4: Decommissioning StorageInstance metadata"))
        for host in cleanup_hosts:
            if not host["ports"]:
                self.log_info(_("No metadata to decommission on {}").format(host["ip"]))
                continue
            try:
                decommission_instances(ip=host["ip"], bk_cloud_id=host["bk_cloud_id"], ports=host["ports"])
                self.log_info(_("Decommissioned instances on {} ports {}").format(host["ip"], host["ports"]))
            except Exception as e:
                self.log_error(_("Failed to decommission instances on {}: {}").format(host["ip"], e))

        self.log_info(_("Step 4/4: Cleaning up rollback tasks and reconciling reports"))
        if ticket_id:
            try:
                deleted, _detailed = TbTendisRollbackTasks.objects.filter(related_rollback_bill_id=ticket_id).delete()
                if deleted:
                    self.log_info(_("Cleaned up {} TbTendisRollbackTasks for ticket {}").format(deleted, ticket_id))
            except Exception as e:
                self.log_error(_("Failed to clean TbTendisRollbackTasks: {}").format(e))

        infos = get_effective_drill_infos(global_data, self.trans_data)
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

        merged_msg = self.render_report_message(report.task_message)

        terminal_stages = {
            TaskStage.DONE,
            TaskStage.SKIPPED,
            TaskStage.RESOURCE_APPLI_FAILED,
            TaskStage.ROLLBACK_FAILED,
            TaskStage.CLEANUP_FAILED,
        }
        if report.task_stage in {s.value for s in terminal_stages}:
            if merged_msg != (report.task_message or ""):
                report.mark(task_message=merged_msg)
            return

        from backend.db_services.redis.rollback.failure_analysis import embed_failed_node_logs

        merged_msg = embed_failed_node_logs(merged_msg, report, TaskStage.CLEANUP_FAILED)
        report.mark(TaskStage.CLEANUP_FAILED, task_message=merged_msg)
        self.log_info(_("Report {} marked CLEANUP_FAILED by best-effort cleanup").format(report_id))
        from backend.db_report.portrait.redis_ingest import ingest_rollback_exercise_portrait

        ingest_rollback_exercise_portrait(report)


class RedisExerciseBestEffortCleanupComponent(Component):
    name = __name__
    code = "redis_exercise_best_effort_cleanup"
    bound_service = RedisExerciseBestEffortCleanupService
