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
import time

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.db_meta.models import Cluster
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.scene.redis.redis_data_structure import RedisDataStructureFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis import redis_context_dataclass as flow_context
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext
from backend.utils.basic import generate_root_id

logger = logging.getLogger("flow")


class RedisFlowPollingService(BaseService):
    """
    Component to poll a single Redis rollback flow status

    This component polls the status of a rollback flow created by
    RedisRollbackFlowCreateService and waits until the flow completes.

    Polling pattern based on Redis DTS implementation:
    - Polls every 10 seconds using StaticIntervalGenerator
    - Checks FlowTree status for the sub-flow
    - Continues until flow is FINISHED or FAILED
    - Updates task status accordingly
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)
    polling_timeout = 3600

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisRollbackExerciseContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        flow_type = kwargs["cluster"].get("flow_type")
        if not flow_type:
            self.log_warning("Flow type not specified")
            return False

        self.interval = StaticIntervalGenerator(kwargs["cluster"]["polling_interval"])
        self.polling_timeout = kwargs["cluster"].get("polling_timeout", self.polling_timeout)

        trans_data.polling_start_time = time.time()
        data.outputs["trans_data"] = trans_data

        self.log_info(
            _("Starting to poll flow {} with {} minute timeout every {} secs").format(
                flow_type, self.polling_timeout // 60, kwargs["cluster"]["polling_interval"]
            )
        )
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisRollbackExerciseContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        flow_type = kwargs["cluster"].get("flow_type")
        if not flow_type:
            self.log_warning("Flow type to poll is not set")
            self.finish_schedule()
            return False

        # Check timeout
        polling_start_time = trans_data.polling_start_time if trans_data.polling_start_time else time.time()
        elapsed_time = time.time() - polling_start_time

        if elapsed_time > self.polling_timeout:
            self.log_error(
                _("Polling timeout after {} seconds for flow type {}").format(self.polling_timeout, flow_type)
            )

            # Update task status to failed on timeout
            if trans_data.task_id:
                try:
                    if flow_type == "rollback_flow_id":
                        self.log_info(
                            _("Dry-run: changing task {} state to ROLLBACK_FAILED due to timeout").format(
                                trans_data.task_id
                            )
                        )
                    elif flow_type == "delete_flow_id":
                        self.log_info(
                            _("Dry-run: changing task {} state to DELETE_FAILED due to timeout").format(
                                trans_data.task_id
                            )
                        )
                except Exception as e:
                    self.log_error(
                        _("Failed to update task {} status on timeout: {}").format(trans_data.task_id, str(e))
                    )

            self.finish_schedule()
            return False

        # Get flow ID to poll based on flow type
        flow_id = getattr(trans_data, flow_type)
        if not flow_id:
            self.log_warning(_("No flow ID found for type {}").format(flow_type))
            self.finish_schedule()
            return False

        # Poll flow status
        try:
            flow_tree = FlowTree.objects.get(root_id=flow_id)
            status = flow_tree.status

            if status not in [StateType.FINISHED.value, StateType.FAILED.value]:
                self.log_info(_("Flow {} status: {}").format(flow_id, status))
                return True

            # Flow finished
            self.finish_schedule()

            if status == StateType.FAILED.value:
                self.log_error(_("Flow {} failed").format(flow_id))

                # Update task status to failed
                if trans_data.task_id:
                    if flow_type == "rollback_flow_id":
                        self.log_info(
                            _("Dry-run: changing task {} state to ROLLBACK_FAILED").format(trans_data.task_id)
                        )
                    elif flow_type == "delete_flow_id":
                        self.log_info(_("Dry-run: changing task {} state to DELETE_FAILED").format(trans_data.task_id))
                return False

            # Flow succeeded
            self.log_info(_("Flow {} finished successfully").format(flow_id))

            # Update task status to succeeded
            if trans_data.task_id:
                if flow_type == "rollback_flow_id":
                    self.log_info(
                        _("Dry-run: changing task {} state to ROLLBACK_SUCCEEDED").format(trans_data.task_id)
                    )
                elif flow_type == "delete_flow_id":
                    self.log_info(_("Dry-run: changing task {} state to DELETE_SUCCEEDED").format(trans_data.task_id))

            return True

        except FlowTree.DoesNotExist:
            self.log_error(_("Flow {} not found in FlowTree").format(flow_id))
            self.finish_schedule()
            return False
        except Exception as e:
            self.log_error(_("Error checking flow {} status: {}").format(flow_id, str(e)))
            self.finish_schedule()
            return False


class RedisFlowPollingComponent(Component):
    name = __name__
    code = "redis_flow_polling"
    bound_service = RedisFlowPollingService


class RedisRollbackFlowCreateSerivce(BaseService):
    """
    Component to execute REDIS_DATA_STRUCTURE flow directly as sub-flow
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisRollbackExerciseContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        task_id = kwargs["cluster"].get("task_id")

        cluster_id = kwargs["cluster"].get("cluster_id")
        instance_ip = kwargs["cluster"].get("instance_ip")
        instance_port = kwargs["cluster"].get("instance_port")
        recovery_time_point = kwargs["cluster"].get("recovery_time_point")
        resource_spec = kwargs["cluster"].get("resource_spec")
        resource_applied = kwargs["cluster"].get("resource_applied", [])

        try:
            cluster = Cluster.objects.get(id=cluster_id)

            rollback_flow_id = generate_root_id()
            # Prepare data structure flow data
            data_structure_data = {
                "bk_biz_id": cluster.bk_biz_id,
                "uid": global_data["uid"],
                "created_by": global_data["created_by"],
                "ticket_type": "REDIS_DATA_STRUCTURE",
                "infos": [
                    {
                        "cluster_id": cluster_id,
                        "bk_cloud_id": cluster.bk_cloud_id,
                        "master_instances": [f"{instance_ip}:{instance_port}"],
                        "recovery_time_point": recovery_time_point,
                        "redis": resource_applied,
                        "resource_spec": resource_spec,
                    }
                ],
                "skip_mannual_confirm": True,
            }

            # Execute RedisDataStructureFlow directly
            self.log_info(_("Executing REDIS_DATA_STRUCTURE flow with data: {}").format(data_structure_data))

            flow = RedisDataStructureFlow(root_id=rollback_flow_id, data=data_structure_data)
            flow.redis_data_structure_flow()

            trans_data.rollback_flow_id = rollback_flow_id
            trans_data.task_id = task_id
            data.outputs["trans_data"] = trans_data

            self.log_info(
                _("REDIS_DATA_STRUCTURE flow {} created successfully for task {}").format(rollback_flow_id, task_id)
            )

            self.log_info(_("Dry-run: changing task {} state to ROLLBACK_FLOW_GENERATED").format(task_id))

            return True

        except Cluster.DoesNotExist:
            self.log_error(_("Cluster {} not found").format(cluster_id))
            return False
        except Exception as e:
            self.log_error(_("Generate REDIS_DATA_STRUCTURE flow failed: {}").format(str(e)))
            self.log_info(_("Dry-run: changing task {} state to ROLLBACK_FAILED due to exception").format(task_id))

            return False


class RedisRollbackFlowCreateComponent(Component):
    name = __name__
    code = "redis_rollback_flow_create"
    bound_service = RedisRollbackFlowCreateSerivce


class RedisTempInstanceDeleteService(BaseService):
    """
    Component to execute a flow deleting temporary instance
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisRollbackExerciseContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        if not trans_data.rollback_flow_id:
            self.log_warning("No temp instance to delete")
            return True

        try:
            cluster_id = kwargs["cluster"].get("cluster_id")
            cluster = Cluster.objects.get(id=cluster_id)

            bk_biz_id = cluster.bk_biz_id
            delete_flow_id = generate_root_id()
            global_data = data.get_one_of_inputs("global_data")
            task_id = kwargs["cluster"].get("task_id")

            flow_data = {
                "bk_biz_id": bk_biz_id,
                "uid": global_data["uid"],
                "created_by": global_data["created_by"],
                "ticket_type": "REDIS_DATA_STRUCTURE_TASK_DELETE",
                "infos": [
                    {
                        "related_rollback_bill_id": global_data["uid"],
                        "cluster_id": cluster.id,
                        "bk_cloud_id": cluster.bk_cloud_id,
                    }
                ],
            }

            self.log_info(_("Executing REDIS_DATA_STRUCTURE_TASK_DELETE flow with data: {}").format(flow_data))

            # Execute detetion flow directly
            flow = RedisDataStructureTaskDeleteFlow(root_id=delete_flow_id, data=flow_data)
            flow.redis_rollback_task_delete_flow()

            # Store deletion flow ID in trans_data
            trans_data.delete_flow_id = delete_flow_id
            data.outputs["trans_data"] = trans_data

            self.log_info(
                _("Successfully created delete flow {} for rollback flow {}").format(
                    delete_flow_id, trans_data.rollback_flow_id
                )
            )

            self.log_info(_("Dry-run changing task {} state to DELETE_FLOW_GENERATED").format(task_id))

            return True

        except Exception as e:
            self.log_error(_("Failed to delete resources: {}").format(str(e)))
            self.log_info(_("Dry-run changing task {} state to DELETE_FAILED due to exception").format(task_id))
            return False


class RedisTempInstanceDeleteComponent(Component):
    name = __name__
    code = "redis_temp_instance_delete"
    bound_service = RedisTempInstanceDeleteService
