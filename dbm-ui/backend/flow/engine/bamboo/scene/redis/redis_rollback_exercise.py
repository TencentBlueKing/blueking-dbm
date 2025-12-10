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
from dataclasses import asdict
from typing import Dict, Optional

from django.conf import settings
from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    RedisFlowPollingComponent,
    RedisRollbackExerciseFinishingComponent,
    RedisRollbackFlowCreateComponent,
    RedisRollbackTaskCleanupComponent,
    RedisTempInstanceDeleteComponent,
)
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisRollbackExerciseContext

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
                    "bk_biz_id": 123,  # Target business ID
                    "created_by": "system",
                }
        """
        self.root_id = root_id
        self.ticket_data = data

        logger.info("ticket_data:", self.ticket_data)

    def rollback_exercise_flow(self):
        """
        Execute the rollback exercise workflow
        """
        pipeline = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
        )

        sub_flows = self._build_sub_flows()
        pipeline.add_parallel_sub_pipeline(sub_flows)

        # Clean up task records for this rollback exercise ticket to prevent accumulation
        pipeline.add_act(
            act_name=_("清理任务记录"),
            act_component_code=RedisRollbackTaskCleanupComponent.code,
            kwargs={},
        )

        pipeline.run_pipeline(init_trans_data_class=RedisRollbackExerciseContext())

    def _build_sub_flows(self):
        """
        Build the rollback exercise sub-flows
        """
        infos = self.ticket_data["infos"]
        config = self.ticket_data["drill_config"]
        sub_flows = []

        for info in infos:
            logger.info(_("Rollback exercise info: {}".format(info)))

            sub_flow = SubBuilder(root_id=self.root_id, data=self.ticket_data)
            cluster = Cluster.objects.get(id=info["cluster_id"])
            ip = info["instance_ip"]
            port = info["instance_port"]
            report_id = info["report_id"]
            resource_applied = info.get("redis", [])  # Should be a list with len == 1

            # Step 1: TaskRecordUpdate - Initialize task status
            report = Report.objects.get(id=report_id)
            if not resource_applied or len(resource_applied) != 1:
                logger.warning(
                    _("Resource applied is abnormal: {}").format(resource_applied if resource_applied else "None")
                )
                report.mark(TaskStage.RESOURCE_APPLI_FAILED, task_message=_("资源申请异常"))
                raise ValueError(_("资源申请异常"))
            else:
                report.mark(TaskStage.RESOURCE_APPLI_SUCCEEDED)

            polling_timeout = config.get("polling_timeout", 3600)

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = RedisRollbackExerciseContext.__name__
            act_kwargs.cluster = {
                "bk_biz_id": self.ticket_data["bk_biz_id"],
                "report_id": report_id,
                "cluster_id": cluster.id,
                "instance_ip": ip,
                "instance_port": port,
                "recovery_time_point": info.get("recovery_time_point"),
                "resource_spec": info.get("resource_spec"),
                "resource_applied": resource_applied,
                "polling_interval": config.get("polling_interval", 10),
                "polling_timeout": polling_timeout,
            }

            # Step 2: RollbackFlowCreate - Generate a rollback flow
            # Note: This must run before AddAlarmShield to properly initialize trans_data in sub-pipeline
            sub_flow.add_act(
                act_name=_("生成构造任务"),
                act_component_code=RedisRollbackFlowCreateComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 3: Add alert shield for the applied machine
            shield_duration_seconds = polling_timeout + settings.DISABLE_ALARM_SHIELD_DELAY
            sub_flow.add_act(
                act_name=_("屏蔽主机 {} 告警(超时 {:.1f} mins)").format(
                    resource_applied[0]["ip"], shield_duration_seconds / 60
                ),
                act_component_code=AddAlarmShieldComponent.code,
                kwargs={
                    "duration_seconds": polling_timeout,
                    "description": _("主机 {} Redis回档演练操作").format(resource_applied[0]["ip"]),
                    "dimensions": [
                        {
                            "name": "bk_target_ip",
                            "values": [resource_applied[0]["ip"]],
                        }
                    ],
                },
            )

            # Step 4: FlowPoll - Poll until the rollback flow creation is done
            act_kwargs.cluster["flow_type"] = "rollback_flow_id"
            sub_flow.add_act(
                act_name=_("等待构造完成"),
                act_component_code=RedisFlowPollingComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 5: TempInstanceDelete - Delete temp instance after rollback completes
            sub_flow.add_act(
                act_name=_("销毁临时实例"),
                act_component_code=RedisTempInstanceDeleteComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 6: FlowPoll - Poll until the temp instance deletion is done
            act_kwargs.cluster["flow_type"] = "delete_flow_id"
            sub_flow.add_act(
                act_name=_("等待销毁完成"),
                act_component_code=RedisFlowPollingComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 7: Finish the rollback exercise and update report status
            sub_flow.add_act(
                act_name=_("演练收尾工作"),
                act_component_code=RedisRollbackExerciseFinishingComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 8: Remove alert shield for the applied machine after exercise completes
            sub_flow.add_act(
                act_name=_("15 分钟后解除主机 {} 告警屏蔽").format(resource_applied[0]["ip"]),
                act_component_code=DisableAlarmShieldComponent.code,
                kwargs={},
            )

            sub_flows.append(
                sub_flow.build_sub_process(sub_name=_("{} - {}:{}").format(cluster.immute_domain, ip, port))
            )

        return sub_flows
