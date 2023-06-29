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
import logging.config
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DEFAULT_MONITOR_TIME, DEFAULT_REDIS_SYSTEM_CMDS
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


def RedisBatchShutdownAtomJob(root_id, ticket_data, sub_kwargs: ActKwargs, shutdown_param: Dict) -> SubBuilder:
    """
    SubBuilder: Redis卸载原籽任务 「暂时是整机卸载」800
    TODO 需要支持部分实例下架（扩缩容场景）

    Args:
        shutdown_param (Dict): {
            "ignore_ips":["xxx.1.2.3"],
            "ip":"1.1.1.x",
            "ports":[],
        }
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    exec_ip = shutdown_param["ip"]
    act_kwargs = deepcopy(sub_kwargs)

    # # 下发介质包
    # trans_files = GetFileList(db_type=DBType.Redis)
    # act_kwargs.file_list = trans_files.redis_cluster_apply_backend(act_kwargs.cluster["db_version"])
    # act_kwargs.exec_ip = exec_ip
    # sub_pipeline.add_act(
    #     act_name=_("Redis-{}-下发介质包").format(exec_ip),
    #     act_component_code=TransFileComponent.code,
    #     kwargs=asdict(act_kwargs),
    # )

    #  监听请求。集群是先关闭再下架，所以理论上这里是没请求才对
    act_kwargs.exec_ip = exec_ip
    act_kwargs.cluster["exec_ip"] = exec_ip
    act_kwargs.cluster["ports"] = shutdown_param["ports"]
    act_kwargs.cluster["monitor_time_ms"] = DEFAULT_MONITOR_TIME
    act_kwargs.cluster["ignore_req"] = False
    act_kwargs.cluster["ignore_keys"] = DEFAULT_REDIS_SYSTEM_CMDS
    # act_kwargs.cluster["ignore_keys"].extend(shutdown_param["ignore_ips"])
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_capturer_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-请求检查").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 干掉非活跃链接
    act_kwargs.exec_ip = exec_ip
    act_kwargs.cluster["exec_ip"] = exec_ip
    act_kwargs.cluster["instances"] = [{"ip": exec_ip, "port": p} for p in shutdown_param["ports"]]
    act_kwargs.cluster["idle_time"] = 600
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_killconn_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-干掉非活跃链接").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 下架实例
    act_kwargs.exec_ip = exec_ip
    act_kwargs.cluster["exec_ip"] = exec_ip
    act_kwargs.cluster["shutdown_ports"] = shutdown_param["ports"]
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_shutdown_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-下架实例").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 停监控
    act_kwargs.cluster["servers"] = [
        {
            "bk_biz_id": str(act_kwargs.cluster["bk_biz_id"]),
            "bk_cloud_id": act_kwargs.bk_cloud_id,
            # "domain": act_kwargs.cluster["immute_domain"],
        }
    ]
    act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-卸载监控").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 清理元数据 @这里如果是master, 需要等slave 清理后才能执行
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.instances_uninstall.__name__
    act_kwargs.cluster["ports"] = shutdown_param["ports"]
    act_kwargs.cluster["ip"] = exec_ip
    act_kwargs.cluster["bk_cloud_id"] = act_kwargs.bk_cloud_id
    act_kwargs.cluster["created_by"] = ticket_data["created_by"]
    sub_pipeline.add_act(
        act_name=_("Redis-{}-清理元数据").format(exec_ip),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(act_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=_("Redis-{}-下架原子任务").format(exec_ip))
