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
import time
from datetime import datetime
from typing import Optional

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.db_meta.models import Cluster
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.scene.redis.redis_data_structure import RedisDataStructureFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis import redis_context_dataclass as flow_context
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext
from backend.ticket.models import TicketType
from backend.utils.basic import generate_root_id


class RedisLogCapturingService(BaseService):
    """
    Enhanced BaseService that automatically captures all log messages to trans_data.task_info.
    Only works with `RedisRollbackExerciseContext`.
    """

    trans_data: Optional[RedisRollbackExerciseContext] = None

    def init_trans_data(self, data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisRollbackExerciseContext = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        self.trans_data = trans_data

    def _append_to_task_info(self, msg: str, log_level: str):
        """Internal method to append formatted message to task_info"""
        if self.trans_data is None:
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{current_time}] [{log_level.upper()}]: {msg}"

        if self.trans_data.task_msg is None:
            self.trans_data.task_info = []
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
        # Automatically set error flag when logging errors
        if self.trans_data is not None:
            self.trans_data.error_occurred = True

    def log_debug(self, msg: str):
        """Override to auto-capture debug logs"""
        super().log_debug(msg)
        self._append_to_task_info(msg, "debug")


class RedisFlowPollingService(RedisLogCapturingService):
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

    def __execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        if self.trans_data.error_occurred:
            self.log_warning("Skipping RedisFlowPollingService due to previous error")
            return False

        flow_type = kwargs["cluster"].get("flow_type")
        if not flow_type:
            self.log_error("Flow type not specified")
            return False

        self.interval = StaticIntervalGenerator(kwargs["cluster"]["polling_interval"])
        self.polling_timeout = kwargs["cluster"].get("polling_timeout", self.polling_timeout)

        self.trans_data.polling_start_time = time.time()

        self.log_info(
            _("Starting to poll flow {} with {} minute timeout every {} secs").format(
                flow_type, self.polling_timeout // 60, kwargs["cluster"]["polling_interval"]
            )
        )
        return True

    def _execute(self, data, parent_data) -> bool:
        self.init_trans_data(data)
        result = self.__execute(data, parent_data)
        data.outputs["trans_data"] = self.trans_data
        return result

    def _update_task_status(self, flow_type: str, flow_succeeded: bool = False):
        """Update task status"""
        if not self.trans_data.report_id:
            self.log_warning(_("report_id is not set!"))
            return

        try:
            report = Report.objects.get(id=self.trans_data.report_id)
            if flow_type == "rollback_flow_id":
                stage = TaskStage.ROLLBACK_SUCCEEDED if flow_succeeded else TaskStage.ROLLBACK_FAILED
            elif flow_type == "delete_flow_id":
                stage = TaskStage.DELETE_SUCCEEDED if flow_succeeded else TaskStage.DELETE_FAILED
            else:
                self.log_warning(_("Unknown flow type: {}").format(flow_type))
                return

            task_msg = "\n".join(self.trans_data.task_msg) if self.trans_data.task_msg else ""
            report.mark(stage, task_message=task_msg)
            self.log_info(_("Report {} state changed to {}").format(self.trans_data.report_id, stage))
        except Report.DoesNotExist:
            self.log_warning(_("Report {} not found for status update").format(self.trans_data.report_id))

    def _check_timeout(self, flow_type: str) -> bool:
        """Check if polling has timed out"""
        polling_start_time = self.trans_data.polling_start_time if self.trans_data.polling_start_time else time.time()
        elapsed_time = time.time() - polling_start_time

        if elapsed_time > self.polling_timeout:
            self.log_error(
                _("Polling timeout after {} seconds for flow type {}").format(self.polling_timeout, flow_type)
            )
            self._update_task_status(flow_type, self.FAILED)
            return True
        return False

    def _handle_flow_status(self, flow_id: str, status: StateType, flow_type: str) -> bool:
        """Handle different flow statuses. Returns True if should continue polling."""
        match status:
            case StateType.FINISHED:
                self.log_info(_("Flow {} finished successfully").format(flow_id))
                self._update_task_status(flow_type, self.SUCCEEDED)
                self.finish_schedule()
                return True
            case StateType.FAILED:
                self.log_error(_("Flow {} failed").format(flow_id))
                self._update_task_status(flow_type, self.FAILED)
                return flow_type == "rollback_flow_id"  # We don't allow delete failure
            case StateType.REVOKED:
                self.log_error(_("Flow {} was cancelled or stopped with state: {}").format(flow_id, status))
                self._update_task_status(flow_type, self.FAILED)
                return False
            case _:
                self.log_info(_("Polling: flow {} with status: {}").format(flow_id, status))
                return True

    def __schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        if self.trans_data.error_occurred:
            self.log_warning("Skipping RedisFlowPollingService due to previous error")
            return False

        flow_type = kwargs["cluster"].get("flow_type")
        if not flow_type:
            self.log_error("Flow type to poll is not set")
            return False

        if self._check_timeout(flow_type):
            return False

        flow_id = getattr(self.trans_data, flow_type)
        if not flow_id:
            self.log_error(_("No flow ID found for type {}").format(flow_type))
            return False

        try:
            flow_tree = FlowTree.objects.get(root_id=flow_id)
            return self._handle_flow_status(flow_id, flow_tree.status, flow_type)

        except FlowTree.DoesNotExist:
            self.log_error(_("Flow {} not found in FlowTree").format(flow_id))
            self.finish_schedule()
            return False
        except Exception as e:
            self.log_error(_("Error checking flow {} status: {}").format(flow_id, str(e)))
            self.finish_schedule()
            return False

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        self.init_trans_data(data)
        result = self.__schedule(data, parent_data, callback_data)
        data.outputs["trans_data"] = self.trans_data
        return result


class RedisFlowPollingComponent(Component):
    name = __name__
    code = "redis_flow_polling"
    bound_service = RedisFlowPollingService


class RedisRollbackFlowCreateSerivce(RedisLogCapturingService):
    """
    Component to execute REDIS_DATA_STRUCTURE flow directly as sub-flow
    """

    def __execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # Check if error occurred in previous steps
        if self.trans_data.error_occurred:
            self.log_warning("Skipping RedisRollbackFlowCreateSerivce due to previous error")
            return True

        report_id = kwargs["cluster"].get("report_id")
        self.trans_data.report_id = report_id

        bk_biz_id = kwargs["cluster"].get("bk_biz_id")  # biz_id of the ticket, not cluster
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
                "bk_biz_id": bk_biz_id,
                "uid": global_data["uid"],
                "created_by": global_data["created_by"],
                "ticket_type": TicketType.REDIS_DATA_STRUCTURE.value,
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

            self.trans_data.rollback_flow_id = rollback_flow_id

            self.log_info(
                _("REDIS_DATA_STRUCTURE flow {} created successfully for task {}").format(rollback_flow_id, report_id)
            )

            # Update task status to ROLLBACK_FLOW_GENERATED
            report = Report.objects.get(id=report_id)
            report.rollback_flow_obj_id = rollback_flow_id
            report.mark(TaskStage.ROLLBACK_FLOW_GENERATED)
            self.log_info(_("Report {} state changed to ROLLBACK_FLOW_GENERATED").format(report_id))

            return True

        except Cluster.DoesNotExist:
            self.log_error(_("Cluster {} not found").format(cluster_id))
            return True
        except Report.DoesNotExist:
            self.log_error(_("Report {} not found for status update").format(report_id))
            return True
        except Exception as e:
            self.log_error(_("Generate REDIS_DATA_STRUCTURE flow failed: {}").format(str(e)))
            # Update task status to ROLLBACK_FLOW_GEN_FAILED
            try:
                report = Report.objects.get(id=report_id)
                task_msg = "\n".join(self.trans_data.task_msg) if self.trans_data.task_msg else ""
                report.mark(TaskStage.ROLLBACK_FLOW_GEN_FAILED, task_msg)
                self.log_info(_("Report {} state changed to ROLLBACK_FLOW_GEN_FAILED").format(report_id))
            except Report.DoesNotExist:
                self.log_warning(_("Report {} not found for failure status update").format(report_id))
            return True

    def _execute(self, data, parent_data) -> bool:
        self.init_trans_data(data)
        result = self.__execute(data, parent_data)
        data.outputs["trans_data"] = self.trans_data
        return result


class RedisRollbackFlowCreateComponent(Component):
    name = __name__
    code = "redis_rollback_flow_create"
    bound_service = RedisRollbackFlowCreateSerivce


class RedisTempInstanceDeleteService(RedisLogCapturingService):
    """
    Component to execute a flow deleting temporary instance
    """

    def __execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        # Check if error occurred in previous steps
        if self.trans_data.error_occurred:
            self.log_warning("Skipping RedisTempInstanceDeleteService due to previous error")
            return True

        if not self.trans_data.rollback_flow_id:
            self.log_error("No temp instance to delete")
            return True

        try:
            cluster_id = kwargs["cluster"].get("cluster_id")
            cluster = Cluster.objects.get(id=cluster_id)

            delete_flow_id = generate_root_id()
            global_data = data.get_one_of_inputs("global_data")
            bk_biz_id = kwargs["cluster"].get("bk_biz_id")  # biz_id of the ticket, not cluster
            report_id = self.trans_data.report_id

            flow_data = {
                "bk_biz_id": bk_biz_id,
                "uid": global_data["uid"],
                "created_by": global_data["created_by"],
                "ticket_type": TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE.value,
                "infos": [
                    {
                        "related_rollback_bill_id": global_data["uid"],
                        "cluster_id": cluster.id,
                        "bk_cloud_id": cluster.bk_cloud_id,
                        "prod_cluster": cluster.immute_domain,
                    }
                ],
                "skip_connections_check": True,
            }

            self.log_info(_("Executing REDIS_DATA_STRUCTURE_TASK_DELETE flow with data: {}").format(flow_data))

            # Execute detetion flow directly
            flow = RedisDataStructureTaskDeleteFlow(root_id=delete_flow_id, data=flow_data)
            flow.redis_rollback_task_delete_flow()

            # Store deletion flow ID in trans_data
            self.trans_data.delete_flow_id = delete_flow_id

            self.log_info(
                _("Successfully created delete flow {} for rollback flow {}").format(
                    delete_flow_id, self.trans_data.rollback_flow_id
                )
            )

            # Update task status to DELETE_FLOW_GENERATED
            task = Report.objects.get(id=report_id)
            task.delete_flow_obj_id = delete_flow_id
            task.mark(TaskStage.DELETE_FLOW_GENERATED)
            self.log_info(_("Report {} state changed to DELETE_FLOW_GENERATED").format(report_id))

            return True

        except Report.DoesNotExist:
            self.log_error(_("Report {} not found for status update").format(report_id))
            return True
        except Exception as e:
            self.log_error(_("Failed to delete resources: {}").format(str(e)))
            # Update task status to DELETE_FLOW_GEN_FAILED
            try:
                task = Report.objects.get(id=report_id)
                task.mark(TaskStage.DELETE_FLOW_GEN_FAILED, task_message=str(e))
                self.log_info(_("Report {} state changed to DELETE_FLOW_GEN_FAILED").format(report_id))
            except Report.DoesNotExist:
                self.log_warning(_("Report {} not found for failure status update").format(report_id))
            return True

    def _execute(self, data, parent_data) -> bool:
        self.init_trans_data(data)
        result = self.__execute(data, parent_data)
        data.outputs["trans_data"] = self.trans_data
        return result


class RedisTempInstanceDeleteComponent(Component):
    name = __name__
    code = "redis_temp_instance_delete"
    bound_service = RedisTempInstanceDeleteService


class RedisRollbackExerciseFinishingService(RedisLogCapturingService):
    """
    Component to perform post action after a task is complete.
    This component:
    1. If previously error occurred, performs error cleanup (currently no-op)
    2. Otherwise, updates the report stage to DONE
    """

    def __execute(self, data, parent_data) -> bool:
        if not self.trans_data.report_id:
            self.log_warning(_("report_id is not set, skipping finishing step"))
            return True

        try:
            report = Report.objects.get(id=self.trans_data.report_id)

            if self.trans_data.error_occurred:
                # Error cleanup - for now just log and leave the report in its current state
                self.log_warning(
                    _("Error occurred during rollback exercise for report {}, skipping DONE status").format(
                        self.trans_data.report_id
                    )
                )
                return True

            # Update report stage to DONE
            task_msg = "\n".join(self.trans_data.task_msg) if self.trans_data.task_msg else ""
            report.mark(TaskStage.DONE, task_message=task_msg)
            self.log_info(_("Report {} state changed to DONE").format(self.trans_data.report_id))
            return True

        except Report.DoesNotExist:
            self.log_warning(_("Report {} not found for finishing").format(self.trans_data.report_id))
            return True
        except Exception as e:
            self.log_error(_("Failed to finish rollback exercise: {}").format(str(e)))
            return True

    def _execute(self, data, parent_data) -> bool:
        self.init_trans_data(data)
        result = self.__execute(data, parent_data)
        data.outputs["trans_data"] = self.trans_data
        return result


class RedisRollbackExerciseFinishingComponent(Component):
    name = __name__
    code = "redis_rollback_exercise_finishing"
    bound_service = RedisRollbackExerciseFinishingService


class RedisRollbackTaskCleanupService(BaseService):
    """
    Component to clean up task records after successful rollback exercise completion.
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")

        ticket_id = global_data.get("uid")
        if not ticket_id:
            self.log_error("No ticket ID found for cleanup")
            return True

        try:
            deleted_count, _d = TbTendisRollbackTasks.objects.filter(related_rollback_bill_id=ticket_id).delete()

            if deleted_count > 0:
                self.log_info(
                    _("Successfully cleaned up {} task record(s) for ticket {}").format(deleted_count, ticket_id)
                )
            else:
                self.log_info(_("No task records found to clean up for ticket {}").format(ticket_id))

            return True

        except Exception as e:
            self.log_error(_("Failed to clean up task records: {}").format(str(e)))
            return True


class RedisRollbackTaskCleanupComponent(Component):
    name = __name__
    code = "redis_rollback_task_cleanup"
    bound_service = RedisRollbackTaskCleanupService
