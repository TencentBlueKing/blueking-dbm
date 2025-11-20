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

from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.models import Cluster
from backend.db_services.cmdb.biz import get_or_create_resource_module, get_resource_biz
from backend.db_services.ipchooser.constants import BkOsTypeCode
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.machine_os_init import insert_host_event
from backend.flow.plugins.components.collections.common.exec_clear_machine import ClearMachineScriptComponent
from backend.flow.plugins.components.collections.common.external_service import ExternalServiceComponent
from backend.flow.plugins.components.collections.common.transfer_host_service import TransferHostServiceComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    RedisFlowPollingComponent,
    RedisRollbackFlowCreateComponent,
    RedisTempInstanceDeleteComponent,
)
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, RedisRollbackExerciseContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

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
                            "task_id": 123,  # Task record ID
                            "resource_spec": {},  # Resource specification
                        }
                    ],
                    "bk_biz_id": 123,  # Target business ID
                    "created_by": "system",
                }
        """
        self.root_id = root_id
        self.ticket_data = data

        # For resource recycling
        self.ticket_data["db_type"] = "redis"
        self.ticket_data["os_type"] = BkOsTypeCode.LINUX
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
            task_record_id = info["task_id"]
            resource_applied = info.get("redis", [])  # Should be a list with len == 1

            # Step 1: TaskRecordUpdate - Initialize task status
            if not resource_applied or len(resource_applied) != 1:
                logger.warning(
                    _("Resource applied is abonormal: {}").format(resource_applied if resource_applied else "None")
                )
                logger.info(_("Dry-run: Changing task state to RESOURCE_APPLI_FAILED"))
                raise ValueError(_("资源申请异常"))
            else:
                logger.info(_("Dry-run: Changing task state to RESOURCE_APPLI_SUCCEEDED"))

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = RedisRollbackExerciseContext.__name__
            act_kwargs.cluster = {
                "task_id": task_record_id,
                "cluster_id": cluster.id,
                "instance_ip": ip,
                "instance_port": port,
                "recovery_time_point": info.get("recovery_time_point"),
                "resource_spec": info.get("resource_spec"),
                "resource_applied": resource_applied,
                "polling_interval": config.get("polling_interval", 10),
                "polling_timeout": config.get("polling_timeout", 3600),
            }

            # Step 2: RollbackFlowCreate - Generate a rollback flow
            sub_flow.add_act(
                act_name=_("生成构造任务"),
                act_component_code=RedisRollbackFlowCreateComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 3: FlowPoll - Poll until the creation is done
            act_kwargs.cluster["flow_type"] = "rollback_flow_id"
            sub_flow.add_act(
                act_name=_("等待构造完成"),
                act_component_code=RedisFlowPollingComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 4: TempInstanceDelete - Delete temp instance
            sub_flow.add_act(
                act_name=_("销毁临时实例"),
                act_component_code=RedisTempInstanceDeleteComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 5: FlowPoll - Poll until the deletion is done
            act_kwargs.cluster["flow_type"] = "delete_flow_id"
            sub_flow.add_act(
                act_name=_("等待销毁完成"),
                act_component_code=RedisFlowPollingComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # Step 6: Clear meta info and delete data on machine
            clear_host = resource_applied[0]
            clear_hosts = [{"ip": clear_host["ip"], "bk_cloud_id": clear_host["bk_cloud_id"]}]
            # Note: RedisDBMeta.clear_machines expects ticket_data["clear_hosts"]
            self.ticket_data["clear_hosts"] = clear_hosts
            clear_meta_kwargs = ActKwargs(
                cluster={"meta_func_name": RedisDBMeta.clear_machines.__name__},
                set_trans_data_dataclass=CommonContext.__name__,
            )
            sub_flow.add_act(
                act_name=_("删除元数据 - {}").format(clear_host["ip"]),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(clear_meta_kwargs),
            )
            sub_flow.add_act(
                act_name=_("清理机器上的数据"),
                act_component_code=ClearMachineScriptComponent.code,
                kwargs={"exec_ips": clear_hosts},
            )

            # Step 7: Return machine to resource pool
            import_data = {
                "resource_type": self.ticket_data["db_type"],
                "for_biz": 0,  # Return to public resource pool
                "bk_biz_id": get_resource_biz(),
                "hosts": [
                    {
                        "ip": clear_host["ip"],
                        "host_id": clear_host["bk_host_id"],
                        "bk_cloud_id": clear_host["bk_cloud_id"],
                    }
                ],
                "labels": {},
                "operator": self.ticket_data["created_by"],
            }
            sub_flow.add_act(
                act_name=_("退回资源池"),
                act_component_code=ExternalServiceComponent.code,
                kwargs={
                    "params": import_data,
                    "api_import_path": DBResourceApi.__module__,
                    "api_import_module": "DBResourceApi",
                    "api_call_func": "resource_import",
                    "success_callback_path": f"{insert_host_event.__module__}.{insert_host_event.__name__}",
                },
            )
            sub_flow.add_act(
                act_name=_("转移CC模块"),
                act_component_code=TransferHostServiceComponent.code,
                kwargs={
                    "bk_biz_id": get_resource_biz(),
                    "bk_module_ids": [get_or_create_resource_module()],
                    "bk_host_ids": [clear_host["bk_host_id"]],
                    "update_host_properties": {"dbm_meta": [], "need_monitor": False, "update_operator": False},
                },
            )

            sub_flows.append(
                sub_flow.build_sub_process(sub_name=_("{} - {}:{}").format(cluster.immute_domain, ip, port))
            )

        return sub_flows
