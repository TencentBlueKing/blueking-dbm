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
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import DestroyedStatus
from backend.db_services.redis.rollback.constants import DATASTRUCTURE_VERSION, ROLLBACK_VERSION
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.db_services.redis.util import is_have_proxy
from backend.flow.consts import DBActuatorTypeEnum, RedisActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisBatchShutdownAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisRollbackDestroyFlow:
    """Destroy v2 rollback temp instances. Locate by PK, refuse v1 records, never pass passwords."""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    @staticmethod
    def load_task(info: dict) -> TbTendisRollbackTasks:
        task_id = info.get("task_id") or info.get("rollback_task_id")
        if not task_id:
            raise RollbackPlanError(context={"message": _("销毁必须提供构造记录主键 task_id")})
        try:
            task = TbTendisRollbackTasks.objects.get(id=task_id)
        except TbTendisRollbackTasks.DoesNotExist:
            raise RollbackPlanError(context={"message": _("构造记录 {} 不存在").format(task_id)})
        version = getattr(task, "rollback_version", None) or DATASTRUCTURE_VERSION
        if version != ROLLBACK_VERSION:
            raise RollbackPlanError(
                context={"message": _("记录 {} 是 {} 构造产物，请改用 REDIS_DATA_STRUCTURE_TASK_DELETE").format(task.id, version)}
            )
        return task

    @staticmethod
    def task_payload(task: TbTendisRollbackTasks) -> dict:
        proxies = []
        raw = task.temp_cluster_proxy or ""
        for part in raw.replace(",", " ").split():
            part = part.strip()
            if part and ":" in part:
                proxies.append(part)
        return {
            "task_id": task.id,
            "related_rollback_bill_id": task.related_rollback_bill_id,
            "bk_biz_id": task.bk_biz_id,
            "bk_cloud_id": task.bk_cloud_id,
            "prod_cluster": task.prod_cluster,
            "prod_cluster_id": task.prod_cluster_id,
            "temp_cluster_type": task.temp_cluster_type,
            "temp_instance_range": task.temp_instance_range,
            "temp_cluster_proxies": proxies,
            "rollback_version": task.rollback_version,
        }

    def redis_rollback_destroy(self):
        pipeline = Builder(root_id=self.root_id, data=self.data)
        subs = [self.build_cluster_destroy(info) for info in self.data["infos"]]
        pipeline.add_parallel_sub_pipeline(sub_flow_list=subs)
        return pipeline.run_pipeline()

    def build_cluster_destroy(self, info: dict):
        is_drill = self.data.get("is_rollback_drill", False)
        task = self.load_task(info)
        payload = self.task_payload(task)

        redis_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = GetFileList(db_type=DBType.Redis).redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **payload,
            "operate": self.data["ticket_type"],
            "cluster_type": payload["temp_cluster_type"],
        }

        status_kwargs = deepcopy(act_kwargs)
        status_kwargs.cluster = {
            "related_rollback_bill_id": payload["related_rollback_bill_id"],
            "bk_biz_id": payload["bk_biz_id"],
            "prod_cluster": payload["prod_cluster"],
            "task_id": payload["task_id"],
            "meta_func_name": RedisDBMeta.update_rollback_task_status.__name__,
            "cluster_type": payload["temp_cluster_type"],
            "destroyed_status": DestroyedStatus.DESTROYING,
        }
        redis_pipeline.add_act(
            act_name=_("更新构造记录为销毁中"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(status_kwargs)
        )
        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        master_ports = {}
        for instance in payload["temp_instance_range"]:
            ip, port = instance.split(":")
            master_ports.setdefault(ip, []).append(int(port))
        act_kwargs.cluster["master_ports"] = master_ports

        tool_acts = []
        for ip_address in master_ports:
            tool_kwargs = deepcopy(act_kwargs)
            tool_kwargs.file_list = GetFileList(db_type=DBType.Redis).redis_dbmon()
            tool_kwargs.exec_ip = ip_address
            tool_acts.append(
                {
                    "act_name": _("Redis-{}-下发工具包").format(ip_address),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(tool_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=tool_acts)

        shutdown_subs = []
        for ip_address, ports in master_ports.items():
            shutdown_subs.append(
                RedisBatchShutdownAtomJob(
                    self.root_id,
                    self.data,
                    act_kwargs,
                    {
                        "ip": ip_address,
                        "ports": ports,
                        "skip_connections_check": self.data.get("skip_connections_check", False),
                        "skip_dbmon_uninstall": is_drill,
                        "is_cluster_shutdown": True,
                    },
                )
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=shutdown_subs)

        act_kwargs.cluster["cluster_type"] = payload["temp_cluster_type"]
        if is_have_proxy(payload["temp_cluster_type"]):
            act_kwargs.cluster["operate"] = "{}_{}".format(
                DBActuatorTypeEnum.Proxy.value, RedisActuatorActionEnum.Shutdown.value
            )
            for proxy in payload["temp_cluster_proxies"]:
                proxy_ip, proxy_port = proxy.split(":")
                proxy_kwargs = deepcopy(act_kwargs)
                proxy_kwargs.cluster["proxy_ip"] = proxy_ip
                proxy_kwargs.cluster["proxy_port"] = int(proxy_port)
                proxy_kwargs.exec_ip = proxy_ip
                proxy_kwargs.get_redis_payload_func = RedisActPayload.proxy_shutdown_payload.__name__
                redis_pipeline.add_act(
                    act_name=_("{}下架proxy实例").format(proxy_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(proxy_kwargs),
                )

        done_kwargs = deepcopy(act_kwargs)
        done_kwargs.cluster = {
            "related_rollback_bill_id": payload["related_rollback_bill_id"],
            "bk_biz_id": payload["bk_biz_id"],
            "prod_cluster": payload["prod_cluster"],
            "task_id": payload["task_id"],
            "meta_func_name": RedisDBMeta.update_rollback_task_status.__name__,
            "cluster_type": payload["temp_cluster_type"],
            "destroyed_status": DestroyedStatus.DESTROYED,
        }
        redis_pipeline.add_act(
            act_name=_("更新构造记录为已销毁"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(done_kwargs)
        )
        return redis_pipeline.build_sub_process(sub_name=_("集群[{}]回档销毁").format(payload["prod_cluster"]))
