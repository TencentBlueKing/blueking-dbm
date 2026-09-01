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
from typing import Dict, Optional

from django.conf import settings
from django.utils.translation import gettext as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.flow.consts import DEFAULT_REDIS_START_PORT
from backend.flow.engine.bamboo.scene.common.builder import Builder, Conditions, SubBuilder
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    RedisExerciseBestEffortCleanupComponent,
    RedisExerciseFlowRunnerComponent,
    RedisExerciseReportUpdateComponent,
    RedisExerciseResourceApplyComponent,
    RedisRollbackExerciseAlarmShieldComponent,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext
from backend.flow.utils.redis.redis_rollback_exercise_resource import build_drill_resource_spec, get_instance_machine

logger = logging.getLogger("flow")


class RedisRollbackExerciseFlow(object):
    """
    Redis Rollback Exercise Flow
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        Initialize the rollback exercise flow

        Args:
            root_id (str): Unique identifier for the drill ticket
            data (Dict): Ticket data containing rollback parameters:
                {
                    "ticket_type": "REDIS_ROLLBACK_EXERCISE",
                    "infos": [
                        {
                            "cluster_id": 1,  # Cluster to exercise
                            "cluster_domain": "cache.example.db",  # Cluster domain
                            "cluster_type": "TendisCache",  # Cluster type
                            "instance_ip": "127.0.0.1",  # Instance IP
                            "instance_port": 30000,  # Instance port
                            "recovery_time_point": "2023-12-12 11:11:11",  # Recovery time point
                            "report_id": 123,  # Task record ID
                            "resource_spec": {},  # Resource specification
                        }
                    ],
                    "drill_config": {
                        "polling_interval": 10,
                        "polling_timeout": 3600,
                        # False (default): preserve the scene and wait at a manual confirmation node.
                        # True: continue and clean up immediately.
                        "error_ignorable": False,
                        "preserve_scene_shield_minutes": 4320,  # Alarm-shield minutes while the scene is preserved
                    },
                    "bk_biz_id": 123,  # Target business ID
                    "created_by": "system",
                }
        """
        self.root_id = root_id
        self.ticket_data = data

        logger.info("ticket_data: %s", self.ticket_data)

    @staticmethod
    def _enrich_drill_prod_temp_instance_pairs(info: dict) -> None:
        """Persist drill prod/temp pairs on ticket info for best-effort cleanup when task row is missing."""
        if info.get("drill_prod_temp_instance_pairs"):
            return
        resource_applied = info.get("redis") or []
        instance_ip = info.get("instance_ip")
        instance_port = info.get("instance_port")
        if not resource_applied or instance_ip is None or instance_port is None:
            return
        temp_host_ip = resource_applied[0]["ip"]
        info["drill_prod_temp_instance_pairs"] = [
            [
                "{}{}{}".format(instance_ip, IP_PORT_DIVIDER, instance_port),
                "{}{}{}".format(temp_host_ip, IP_PORT_DIVIDER, DEFAULT_REDIS_START_PORT),
            ]
        ]

    def rollback_exercise_flow(self):
        """
        Composes resource apply, per-cluster exercise sub-flows, and best-effort cleanup.
        """
        flow_data = copy.deepcopy(self.ticket_data)

        pipeline = Builder(root_id=self.root_id, data=flow_data)

        pipeline.add_act(
            act_name=_("申请演练资源"),
            act_component_code=RedisExerciseResourceApplyComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
            },
            error_ignorable=True,
        )

        sub_flows = []
        for info_index, info in enumerate(flow_data["infos"]):
            sf = self._build_exercise_sub_flow(info, info_index, flow_data)
            if sf is not None:
                sub_flows.append(sf)

        if sub_flows:
            pipeline.add_parallel_sub_pipeline(sub_flows)

        pipeline.add_act(
            act_name=_("最佳尝试清理"),
            act_component_code=RedisExerciseBestEffortCleanupComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
            },
        )

        pipeline.run_pipeline(init_trans_data_class=RedisRollbackExerciseContext())

    @staticmethod
    def build_ds_flow_data(global_data: dict, info: dict, cluster: Cluster) -> dict:
        resource_applied = info.get("redis") or []
        instance_ip = info.get("instance_ip")
        instance_port = info.get("instance_port")
        master_instances = [f"{instance_ip}{IP_PORT_DIVIDER}{instance_port}"]
        resource_spec = info.get("resource_spec") or {}
        if not resource_spec.get("redis"):
            machine = get_instance_machine(info, cluster)
            if machine is not None:
                resource_spec = build_drill_resource_spec(machine, host_count=len(resource_applied) or 1)
        return {
            "bk_biz_id": global_data["bk_biz_id"],
            "uid": global_data.get("uid", global_data.get("job_root_id")),
            "created_by": global_data.get("created_by", "system"),
            "ticket_type": "REDIS_DATA_STRUCTURE",
            "infos": [
                {
                    "cluster_id": cluster.id,
                    "bk_cloud_id": cluster.bk_cloud_id,
                    "master_instances": master_instances,
                    "redis": resource_applied,
                    "resource_spec": resource_spec,
                    "recovery_time_point": info.get("recovery_time_point"),
                }
            ],
            "skip_mannual_confirm": True,
            "is_rollback_drill": True,
        }

    @staticmethod
    def build_delete_flow_data(global_data: dict, cluster: Cluster) -> dict:
        del_info = {
            "related_rollback_bill_id": global_data.get("uid", global_data.get("job_root_id")),
            "prod_cluster": cluster.immute_domain,
        }
        return {
            "bk_biz_id": global_data["bk_biz_id"],
            "uid": global_data.get("uid", global_data.get("job_root_id")),
            "created_by": global_data.get("created_by", "system"),
            "ticket_type": "REDIS_DATA_STRUCTURE_TASK_DELETE",
            "skip_connections_check": True,
            "is_rollback_drill": True,
            "infos": [del_info],
        }

    # -------------------------------------------------------------------------
    # New flow: sub-flow builder
    # -------------------------------------------------------------------------

    def _build_exercise_sub_flow(self, info: dict, info_index: int, flow_data: dict):
        """Build a single-cluster exercise sub-flow.

        The data-structure step is wrapped in a polling runner act whose
        ``error_ignorable`` follows ``drill_config.error_ignorable``.  A
        conditional gateway then branches on the outcome:
          - success  -> report_succeeded -> task_delete -> report_done
          - failure  -> report_rollback_failed

        With ``error_ignorable=False`` (preserve mode, default), a failed/timed-out
        child pipeline completes the runner with a failure output and pauses only
        that branch at a manual confirmation node. The parent ticket stays RUNNING,
        so sibling branches can continue launching child pipelines. After the DBA
        confirms, the branch marks the failure and the main pipeline's best-effort
        cleanup runs. With ``error_ignorable=True`` there is no pause and cleanup
        runs immediately.
        """
        cluster_id = info["cluster_id"]
        instance_ip = info["instance_ip"]
        instance_port = info["instance_port"]
        report_id = info["report_id"]
        config = flow_data.get("drill_config", {})
        polling_timeout = config.get("polling_timeout", 3600)
        polling_interval = config.get("polling_interval", 10)
        error_ignorable = config.get("error_ignorable", False)
        preserve_scene_shield_minutes = config.get("preserve_scene_shield_minutes", 4320)

        report = Report.objects.get(id=report_id)
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            task_message = _("源集群 {} 不存在，跳过回档演练").format(cluster_id)
            logger.warning(task_message)
            report.mark(TaskStage.SKIPPED, task_message=task_message)
            return None

        sub_flow = SubBuilder(root_id=self.root_id, data=flow_data)

        # ---- Alarm shield ----
        # Preserve mode: stretch the shield to cover the whole scene-preserve window;
        # otherwise temp instances re-alert after the default ~1h shield.
        # Preserve branch: act name matches duration_seconds actually passed.
        # Legacy branch: act name shows polling_timeout + DISABLE_ALARM_SHIELD_DELAY,
        # but kwargs still pass polling_timeout.
        if error_ignorable:
            shield_duration_seconds = polling_timeout + settings.DISABLE_ALARM_SHIELD_DELAY
            shield_kwargs_duration = polling_timeout
        else:
            shield_duration_seconds = max(polling_timeout, preserve_scene_shield_minutes * 60)
            shield_kwargs_duration = shield_duration_seconds
        sub_flow.add_act(
            act_name=_("屏蔽演练主机告警(超时 {:.1f} mins)").format(shield_duration_seconds / 60),
            act_component_code=RedisRollbackExerciseAlarmShieldComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "info_index": info_index,
                "duration_seconds": shield_kwargs_duration,
                "description": _("Redis回档演练操作"),
                "dimensions": [
                    {"name": "appid", "values": [str(cluster.bk_biz_id)]},
                ],
            },
        )

        # ---- Report: ROLLBACK_STARTED ----
        sub_flow.add_act(
            act_name=_("标记回档开始"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "info_index": info_index,
                "stage": TaskStage.ROLLBACK_STARTED,
            },
        )

        # ================================================================
        # Data-structure & delete flow data resolved at runner runtime
        # ================================================================
        self._build_runner_flow(
            sub_flow,
            info_index,
            report_id,
            cluster_id,
            polling_timeout,
            polling_interval,
            error_ignorable,
        )

        return sub_flow.build_sub_process(
            sub_name=_("{} - {}:{}").format(cluster.immute_domain, instance_ip, instance_port)
        )

    def _build_runner_flow(
        self,
        sub_flow,
        info_index,
        report_id,
        cluster_id,
        polling_timeout,
        polling_interval,
        error_ignorable,
    ):
        """Build runner acts with conditional branching on outcomes.

        Uses ``RedisExerciseFlowRunnerComponent`` to launch child pipelines
        via Flow.flow() and poll FlowTree.status.  Conditional gateways
        branch on the outcome at each phase:
          - rollback success  -> report_succeeded -> delete runner -> conditional
          - rollback failure  -> report_rollback_failed
          - delete success    -> report_done
          - delete failure    -> no-op (best-effort cleanup reconciles)

        ``error_ignorable=False`` (preserve mode, default) keeps a failed/timed-out
        child pipeline for inspection, marks the report SCENE_PRESERVED, and routes
        ``rollback_code=1`` / ``delete_code=1`` to a manual confirmation node. The
        runner itself finishes normally, so the ticket stays RUNNING and sibling
        branches are not blocked. After confirmation, the branch marks the failure
        and the main pipeline's best-effort cleanup first revokes leftover child
        flows before removing temporary instances.
        ``error_ignorable=True`` keeps the legacy behavior without manual
        confirmation and proceeds to cleanup immediately.

        Both runner nodes are ``retryable=False`` because child failures are handled
        as business outcomes. The runner service additionally revokes any previous
        non-terminal child pipeline as a force-retry safety net before submitting a
        new one in preserve mode.
        """
        rollback_runner_act = sub_flow.add_act(
            act_name=_("回档流程"),
            act_component_code=RedisExerciseFlowRunnerComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "flow_identifier": "redis_data_structure",
                "info_index": info_index,
                "cluster_id": cluster_id,
                "build_flow_data_from_global": True,
                "report_id": report_id,
                "flow_id_field": "rollback_flow_obj_id",
                "polling_timeout": polling_timeout,
                "polling_interval": polling_interval,
                "output_var": "rollback_code",
                "preserve_scene_on_failure": not error_ignorable,
            },
            error_ignorable=error_ignorable,
            retryable=False,
            extend=False,
        )

        # ---- Success branch: report_succeeded -> delete runner -> conditional ----
        success_branch = SubBuilder(root_id=self.root_id, data=sub_flow.data)

        success_branch.add_act(
            act_name=_("标记回档成功"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "info_index": info_index,
                "stage": TaskStage.ROLLBACK_SUCCEEDED,
            },
        )

        delete_runner_act = success_branch.add_act(
            act_name=_("清理临时实例流程"),
            act_component_code=RedisExerciseFlowRunnerComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "flow_identifier": "redis_data_structure_task_delete",
                "info_index": info_index,
                "cluster_id": cluster_id,
                "build_delete_flow_data_from_global": True,
                "report_id": report_id,
                "flow_id_field": "delete_flow_obj_id",
                "polling_timeout": polling_timeout,
                "polling_interval": polling_interval,
                "output_var": "delete_code",
                "preserve_scene_on_failure": not error_ignorable,
            },
            error_ignorable=error_ignorable,
            retryable=False,
            extend=False,
        )

        delete_success_act = success_branch.add_act(
            act_name=_("标记演练完成"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "info_index": info_index,
                "stage": TaskStage.DONE,
            },
            extend=False,
        )

        if error_ignorable:
            delete_failure_act = success_branch.add_act(
                act_name=_("标记清理失败 (最佳尝试清理兜底)"),
                act_component_code=RedisExerciseReportUpdateComponent.code,
                kwargs={
                    "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                    "report_id": report_id,
                    "info_index": info_index,
                    "stage": TaskStage.CLEANUP_FAILED,
                },
                extend=False,
            )
        else:
            delete_failure_branch = SubBuilder(root_id=self.root_id, data=success_branch.data)
            delete_failure_branch.add_act(
                act_name=_("现场保留：确认清理失败并执行兜底清理"),
                act_component_code=PauseComponent.code,
                kwargs={"description": _("排查清理失败现场后，确认继续执行兜底清理")},
            )
            delete_failure_branch.add_act(
                act_name=_("标记清理失败 (最佳尝试清理兜底)"),
                act_component_code=RedisExerciseReportUpdateComponent.code,
                kwargs={
                    "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                    "report_id": report_id,
                    "info_index": info_index,
                    "stage": TaskStage.CLEANUP_FAILED,
                },
            )
            delete_failure_act = delete_failure_branch.build_sub_process(sub_name=_("清理失败现场确认"))

        success_branch.add_conditional_subs(
            source_act=delete_runner_act,
            conditions=[
                Conditions(act_object=delete_success_act, express="==0"),
                Conditions(act_object=delete_failure_act, express="==1"),
            ],
            conditions_param="delete_code",
            name=_("判断清理结果"),
        )

        success_sub = success_branch.build_sub_process(sub_name=_("回档成功处理"))

        # ---- Failure branch: optionally hold the scene, then mark rollback failed ----
        if error_ignorable:
            rollback_failure_act = sub_flow.add_act(
                act_name=_("标记回档失败"),
                act_component_code=RedisExerciseReportUpdateComponent.code,
                kwargs={
                    "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                    "report_id": report_id,
                    "info_index": info_index,
                    "stage": TaskStage.ROLLBACK_FAILED,
                },
                extend=False,
            )
        else:
            rollback_failure_branch = SubBuilder(root_id=self.root_id, data=sub_flow.data)
            rollback_failure_branch.add_act(
                act_name=_("现场保留：确认回档失败并清理"),
                act_component_code=PauseComponent.code,
                kwargs={"description": _("排查回档失败现场后，确认标记失败并清理临时实例")},
            )
            rollback_failure_branch.add_act(
                act_name=_("标记回档失败"),
                act_component_code=RedisExerciseReportUpdateComponent.code,
                kwargs={
                    "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                    "report_id": report_id,
                    "info_index": info_index,
                    "stage": TaskStage.ROLLBACK_FAILED,
                },
            )
            rollback_failure_act = rollback_failure_branch.build_sub_process(sub_name=_("回档失败现场确认"))

        # ---- Conditional gateway on rollback result ----
        sub_flow.add_conditional_subs(
            source_act=rollback_runner_act,
            conditions=[
                Conditions(act_object=success_sub, express="==0"),
                Conditions(act_object=rollback_failure_act, express="==1"),
            ],
            conditions_param="rollback_code",
            name=_("判断回档结果"),
        )

        # ---- Disable alarm shield (always runs after conditional converge) ----
        sub_flow.add_act(
            act_name=_("15 分钟后解除演练主机告警屏蔽"),
            act_component_code=DisableAlarmShieldComponent.code,
            kwargs={},
            error_ignorable=True,  # Don't let bkmonitor affect the task flow
        )
