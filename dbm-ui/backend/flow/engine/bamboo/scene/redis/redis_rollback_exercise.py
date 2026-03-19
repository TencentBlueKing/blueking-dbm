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
from backend.flow.engine.bamboo.scene.common.builder import Builder, Conditions, SubBuilder
from backend.flow.engine.bamboo.scene.redis.redis_data_structure import RedisDataStructureFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    RedisExerciseBestEffortCleanupComponent,
    RedisExerciseFlowRunnerComponent,
    RedisExerciseReportUpdateComponent,
    RedisRollbackExerciseAlarmShieldComponent,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext

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
                        "error_ignorable": True,  # Whether to continue when one cluster fails
                    },
                    "bk_biz_id": 123,  # Target business ID
                    "created_by": "system",
                }
        """
        self.root_id = root_id
        self.ticket_data = data

        logger.info("ticket_data: %s", self.ticket_data)

    def rollback_exercise_flow(self):
        """
        Composes data-structure + cleanup steps directly instead of spawning inner pipelines and polling.
        """
        pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))

        sub_flows = []
        for info in self.ticket_data["infos"]:
            sf = self._build_exercise_sub_flow(info)
            if sf is not None:
                sub_flows.append(sf)

        if not sub_flows:
            logger.warning("No valid sub-flows to run")
            return

        pipeline.add_parallel_sub_pipeline(sub_flows)

        pipeline.add_act(
            act_name=_("最佳尝试清理"),
            act_component_code=RedisExerciseBestEffortCleanupComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
            },
        )

        pipeline.run_pipeline(init_trans_data_class=RedisRollbackExerciseContext())

    # -------------------------------------------------------------------------
    # New flow: sub-flow builder
    # -------------------------------------------------------------------------

    def _build_exercise_sub_flow(self, info: dict):
        """Build a single-cluster exercise sub-flow that reuses RedisDataStructureFlow
        and RedisDataStructureTaskDeleteFlow, exercising the actual production code paths.

        When ``error_ignorable`` is True (from drill_config), the data-structure
        step is wrapped in a polling runner act with ``error_ignorable=True``.
        A conditional gateway then branches on the outcome:
          - success  -> report_succeeded -> task_delete -> report_done
          - failure  -> report_rollback_failed
        This ensures the sub-flow never hard-fails, so the best-effort cleanup
        at the main pipeline level always runs.
        """
        cluster_id = info["cluster_id"]
        cluster = Cluster.objects.get(id=cluster_id)
        instance_ip = info["instance_ip"]
        instance_port = info["instance_port"]
        report_id = info["report_id"]
        resource_applied = info.get("redis", [])
        recovery_time_point = info.get("recovery_time_point")
        config = self.ticket_data.get("drill_config", {})
        polling_timeout = config.get("polling_timeout", 3600)
        polling_interval = config.get("polling_interval", 10)
        error_ignorable = config.get("error_ignorable", True)

        report = Report.objects.get(id=report_id)
        if not resource_applied or len(resource_applied) != 1:
            logger.warning(_("Resource applied is abnormal: {}").format(resource_applied or "None"))
            report.mark(TaskStage.RESOURCE_APPLI_FAILED, task_message=_("资源申请异常"))
            return None
        report.mark(TaskStage.RESOURCE_APPLI_SUCCEEDED)

        temp_host_ip = resource_applied[0]["ip"]
        master_instances = [f"{instance_ip}{IP_PORT_DIVIDER}{instance_port}"]

        sub_flow = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))

        # ---- Alarm shield ----
        shield_duration_seconds = polling_timeout + settings.DISABLE_ALARM_SHIELD_DELAY
        sub_flow.add_act(
            act_name=_("屏蔽主机 {} 告警(超时 {:.1f} mins)").format(temp_host_ip, shield_duration_seconds / 60),
            act_component_code=RedisRollbackExerciseAlarmShieldComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "duration_seconds": polling_timeout,
                "description": _("主机 {} Redis回档演练操作").format(temp_host_ip),
                "dimensions": [
                    {"name": "appid", "values": [str(cluster.bk_biz_id)]},
                    {"name": "bk_target_ip", "values": [temp_host_ip]},
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
                "stage": TaskStage.ROLLBACK_STARTED,
            },
        )

        # ================================================================
        # Data-structure & delete flow data (shared by both branches)
        # ================================================================
        ds_data = {
            "bk_biz_id": self.ticket_data["bk_biz_id"],
            "uid": self.ticket_data.get("uid", self.root_id),
            "created_by": self.ticket_data.get("created_by", "system"),
            "ticket_type": "REDIS_DATA_STRUCTURE",
            "infos": [
                {
                    "cluster_id": cluster_id,
                    "bk_cloud_id": cluster.bk_cloud_id,
                    "master_instances": master_instances,
                    "redis": resource_applied,
                    "resource_spec": info.get("resource_spec", {}),
                    "recovery_time_point": recovery_time_point,
                }
            ],
            "skip_mannual_confirm": True,
            "is_rollback_drill": True,
        }

        del_info = {
            "related_rollback_bill_id": self.ticket_data.get("uid", self.root_id),
            "prod_cluster": cluster.immute_domain,
        }
        del_data = {
            "bk_biz_id": self.ticket_data["bk_biz_id"],
            "uid": self.ticket_data.get("uid", self.root_id),
            "created_by": self.ticket_data.get("created_by", "system"),
            "ticket_type": "REDIS_DATA_STRUCTURE_TASK_DELETE",
            "skip_connections_check": True,
            "infos": [del_info],
        }

        if error_ignorable:
            self._build_error_ignorable_flow(
                sub_flow,
                ds_data,
                del_data,
                report_id,
                polling_timeout,
                polling_interval,
                temp_host_ip,
            )
        else:
            self._build_strict_flow(sub_flow, ds_data, del_data, del_info, report_id, temp_host_ip)

        return sub_flow.build_sub_process(
            sub_name=_("{} - {}:{}").format(cluster.immute_domain, instance_ip, instance_port)
        )

    # -----------------------------------------------------------------
    # error_ignorable=True: runner act + conditional branching
    # -----------------------------------------------------------------

    def _build_error_ignorable_flow(
        self,
        sub_flow,
        ds_data,
        del_data,
        report_id,
        polling_timeout,
        polling_interval,
        temp_host_ip,
    ):
        """Build a flow where data-structure failure does not block the pipeline.

        Uses ``RedisExerciseFlowRunnerComponent`` (with error_ignorable=True)
        that launches child pipelines via Flow.flow() and polls FlowTree.status.
        Conditional gateways branch on the outcome at each phase:
          - rollback success  -> report_succeeded -> delete runner -> conditional
          - rollback failure  -> report_rollback_failed
          - delete success    -> report_done
          - delete failure    -> no-op (best-effort cleanup reconciles)
        """
        # ---- Data-structure runner (error_ignorable) ----
        rollback_runner_act = sub_flow.add_act(
            act_name=_("数据构造(可忽略错误)"),
            act_component_code=RedisExerciseFlowRunnerComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "flow_identifier": "redis_data_structure",
                "flow_data": ds_data,
                "report_id": report_id,
                "flow_id_field": "rollback_flow_obj_id",
                "polling_timeout": polling_timeout,
                "polling_interval": polling_interval,
                "output_var": "rollback_code",
            },
            error_ignorable=True,
            extend=False,
        )

        # ---- Success branch: report_succeeded -> delete runner -> conditional ----
        success_branch = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))

        success_branch.add_act(
            act_name=_("标记回档成功"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "stage": TaskStage.ROLLBACK_SUCCEEDED,
            },
        )

        delete_runner_act = success_branch.add_act(
            act_name=_("清理临时实例(可忽略错误)"),
            act_component_code=RedisExerciseFlowRunnerComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "flow_identifier": "redis_data_structure_task_delete",
                "flow_data": del_data,
                "report_id": report_id,
                "flow_id_field": "delete_flow_obj_id",
                "polling_timeout": polling_timeout,
                "polling_interval": polling_interval,
                "output_var": "delete_code",
            },
            error_ignorable=True,
            extend=False,
        )

        delete_success_act = success_branch.add_act(
            act_name=_("标记演练完成"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "stage": TaskStage.DONE,
            },
            extend=False,
        )

        delete_failure_act = success_branch.add_act(
            act_name=_("清理失败(最佳尝试清理兜底)"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "stage": TaskStage.CLEANUP_FAILED,
            },
            extend=False,
        )

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

        # ---- Failure branch: mark rollback failed ----
        rollback_failure_act = sub_flow.add_act(
            act_name=_("标记回档失败"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "stage": TaskStage.ROLLBACK_FAILED,
            },
            extend=False,
        )

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
            act_name=_("15 分钟后解除主机 {} 告警屏蔽").format(temp_host_ip),
            act_component_code=DisableAlarmShieldComponent.code,
            kwargs={},
        )

    # -----------------------------------------------------------------
    # error_ignorable=False: direct sub-pipeline (original behaviour)
    # -----------------------------------------------------------------

    def _build_strict_flow(self, sub_flow, ds_data, del_data, del_info, report_id, temp_host_ip):
        """Build a flow where data-structure failure stops the sub-flow."""

        # ---- Data-structure sub-pipeline (inline) ----
        ds_flow = RedisDataStructureFlow(root_id=self.root_id, data=ds_data)
        sub_flow.add_sub_pipeline(ds_flow.build_cluster_data_structure(ds_data["infos"][0]))

        # ---- Report: ROLLBACK_SUCCEEDED ----
        sub_flow.add_act(
            act_name=_("标记回档成功"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "stage": TaskStage.ROLLBACK_SUCCEEDED,
            },
        )

        # ---- Task delete sub-pipeline ----
        del_flow = RedisDataStructureTaskDeleteFlow(root_id=self.root_id, data=del_data)
        del_sub = del_flow.build_cluster_task_delete(del_info)
        sub_flow.add_sub_pipeline(del_sub)

        # ---- Report: DONE ----
        sub_flow.add_act(
            act_name=_("标记演练完成"),
            act_component_code=RedisExerciseReportUpdateComponent.code,
            kwargs={
                "set_trans_data_dataclass": RedisRollbackExerciseContext.__name__,
                "report_id": report_id,
                "stage": TaskStage.DONE,
            },
        )

        # ---- Disable alarm shield ----
        sub_flow.add_act(
            act_name=_("15 分钟后解除主机 {} 告警屏蔽").format(temp_host_ip),
            act_component_code=DisableAlarmShieldComponent.code,
            kwargs={},
        )
