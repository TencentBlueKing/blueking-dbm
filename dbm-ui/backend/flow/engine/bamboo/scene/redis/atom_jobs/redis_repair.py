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
from dataclasses import asdict
from typing import Dict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


def RedisLocalRepairAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, params: Dict) -> SubBuilder:
    """### SubBuilder: 用于网络闪断下 直接修复slave状态使用 TODO
    params (Dict): {
      "ip": "x.12.1.2",
      "ports": [],
      "wait_seconds": 600,
      "last_io_second_ago":10,
    }
    """
    exec_ip = params["ip"]
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 下发介质包 （这里可能机器真的挂了，也可能是暂时的网络不通） 需要有一段时间内的重试
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_cluster_apply_backend(act_kwargs.cluster["db_version"])
    act_kwargs.exec_ip = exec_ip
    act_kwargs.cluster["retry_times"] = 60
    act_kwargs.cluster["retry_sleep"] = 1
    sub_pipeline.add_act(
        act_name=_("Redis-301-{}-下发介质包").format(exec_ip),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(act_kwargs),
    )
    # runtime = BambooDjangoRuntime()
    # api.retry_node(runtime=runtime, node_id="node_id", data={"key": "value"}).result

    # 检查同步状态
    act_kwargs.exec_ip = exec_ip
    act_kwargs.cluster["exec_ip"] = exec_ip
    act_kwargs.cluster["instances"] = [{"ip": exec_ip, "port": p} for p in params["ports"]]
    act_kwargs.cluster["watch_seconds"] = 600
    act_kwargs.cluster["last_io_second_ago"] = params["last_io_second_ago"]
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_checksync_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-302-{}-检查同步状态").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )
    # check_sync_act = sub_pipeline.add_act(
    #     act_name=_("Redis-302-{}-检查同步状态").format(exec_ip),
    #     act_component_code=ExecuteDBActuatorScriptComponent.code,
    #     kwargs=asdict(act_kwargs),
    # )

    # # 这里需要根据返回的结果，判断下一步的动作
    # check_sync_act.add_exclusive_acts()

    # # 分支1: 修复元数据
    # act_kwargs.cluster = {
    #     "meta_func_name": RedisDBMeta.instances_status_update.__name__,
    #     "ports": params["ports"],
    #     "ip": exec_ip,
    #     "status": InstanceStatus.RUNNING,
    # }
    # fix_status_act = sub_pipeline.add_act(
    #     act_name=_("Redis-305-{}-修复元数据").format(exec_ip),
    #     act_component_code=RedisDBMetaComponent.code,
    #     kwargs=asdict(act_kwargs),
    #     extend = False,
    # )
    # fix_status_act.component.inputs.input_a = Var(type=Var.SPLICE, value='${input_a}')

    # pipeline_data = Data()
    # pipeline_data.inputs['${input_a}'] = Var(type=Var.PLAIN, value=0)
    # pipeline_data.inputs['${check_sync_act_output}'] =
    # NodeOutput(type=Var.SPLICE, source_act=check_sync_act.id, source_key='input_a')

    # eg = ExclusiveGateway(
    # conditions={
    #     0: '${check_sync_act_output} < 0',
    #     1: '${check_sync_act_output} >= 0'
    # },
    # name=_("Redis-303-{}-是否修复状态").format(exec_ip),
    # )

    # # 分支2: 撒都不干
    # empty_act = ServiceActivity(component_code='empty_component', name='Redis-303-空的')

    # check_sync_act.connect(empty_act, fix_status_act).to(eg)

    return sub_pipeline
