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
from datetime import datetime
from typing import Optional

from django.core.cache import cache
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

    def _finish_by_child_state(self, data, child_root_id: str, child_state) -> bool:
        if child_state == StateType.FINISHED:
            self.log_info(_("Child pipeline {} finished successfully").format(child_root_id))
            self._set_result(data, 0)
            self.finish_schedule()
            return True

        if child_state in (StateType.FAILED, StateType.REVOKED):
            self.log_error(_("Child pipeline {} ended with status {}").format(child_root_id, child_state))
            # FAILED means the pipeline errored out but sibling/pending nodes may still be running.
            # Revoke to ensure the whole tree is terminated. REVOKED is already terminal, skip.
            if child_state == StateType.FAILED:
                self._terminate_child_pipeline(child_root_id)
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        return False

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
                if self._finish_by_child_state(data, child_root_id, callback_child_state):
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
            self._terminate_child_pipeline(child_root_id)
            self._set_result(data, 1)
            self.finish_schedule()
            return True

        try:
            flow_tree = FlowTree.objects.get(root_id=child_root_id)
        except FlowTree.DoesNotExist:
            return True

        self._finish_by_child_state(data, child_root_id, flow_tree.status)
        return True


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

        return {
            "ip": ip,
            "bk_cloud_id": bk_cloud_id,
            "bk_host_id": bk_host_id,
            "remark": host.get("remark", _("Redis rollback exercise revoked")),
        }

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
        return list(hosts_by_id.values())

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
            task_temp_addrs = self._parse_instance_set(task.temp_instance_range)
            task_prod_addrs = self._parse_instance_set(task.prod_instance_range)
            pair_prod_addrs, pair_temp_addrs = self._parse_prod_temp_pairs(task.prod_temp_instance_pairs)
            if not pair_temp_addrs:
                self.log_warning(
                    _("Rollback task {} has no prod/temp instance pairs, skipping work-dir cleanup").format(task.id)
                )
                continue

            allowed_temp_addrs = task_temp_addrs & pair_temp_addrs
            unsafe_addrs = allowed_temp_addrs & (task_prod_addrs | pair_prod_addrs)
            if unsafe_addrs:
                self.log_warning(
                    _("Rollback task {} temp addresses overlap source/prod addresses {}, skipping them").format(
                        task.id, sorted("{}:{}".format(ip, port) for ip, port in unsafe_addrs)
                    )
                )
                allowed_temp_addrs -= unsafe_addrs

            for ip, port in allowed_temp_addrs:
                if ip == temp_host_ip:
                    ports.add(port)
        return sorted(ports)

    def _collect_cleanup_hosts(self, global_data: dict) -> list:
        ticket_id = global_data.get("uid")
        ticket_bk_biz_id = global_data.get("bk_biz_id")
        cleanup_hosts = []

        for info in global_data.get("infos", []):
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

    def _execute_inner_captured(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}

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
        ticket_id = global_data.get("uid")
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

        cleanup_msg = "\n".join(self.trans_data.task_msg) if self.trans_data and self.trans_data.task_msg else ""
        merged_msg = self._merge_task_message(report.task_message, cleanup_msg)

        terminal_stages = {
            TaskStage.DONE,
            TaskStage.RESOURCE_APPLI_FAILED,
            TaskStage.ROLLBACK_FAILED,
            TaskStage.CLEANUP_FAILED,
        }
        if report.task_stage in {s.value for s in terminal_stages}:
            if merged_msg != (report.task_message or ""):
                report.mark(task_message=merged_msg)
            return
        report.mark(TaskStage.CLEANUP_FAILED, task_message=merged_msg)
        self.log_info(_("Report {} marked CLEANUP_FAILED by best-effort cleanup").format(report_id))

    @staticmethod
    def _merge_task_message(existing_msg: str, appended_msg: str) -> str:
        """
        Merge report task logs without clobbering historical content.

        Rules:
        1. Keep existing logs first.
        2. Append new block only when non-empty.
        3. Deduplicate when the existing message already ends with the same block.
        """
        existing = (existing_msg or "").strip()
        appended = (appended_msg or "").strip()

        if not existing:
            return appended
        if not appended:
            return existing
        if existing.endswith(appended):
            return existing
        return "{}\n{}".format(existing, appended)


class RedisExerciseBestEffortCleanupComponent(Component):
    name = __name__
    code = "redis_exercise_best_effort_cleanup"
    bound_service = RedisExerciseBestEffortCleanupService
