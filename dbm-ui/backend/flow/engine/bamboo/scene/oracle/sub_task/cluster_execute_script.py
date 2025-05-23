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

from copy import deepcopy
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.oracle.oracle_actuator_job import OracleExecuteDBActuatorJobComponent
from backend.flow.utils.oracle.oracle_exec_script_dataclass import ExecuteScriptActKwargs


def cluster_execute_script(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ExecuteScriptActKwargs, info: dict
) -> SubBuilder:
    """
    oracle单个实例执行脚本
    info 表示cluster信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 执行脚本
    kwargs = sub_get_kwargs.get_execute_script_kwargs(info=info)
    sub_pipeline.add_act(
        act_name=_("Oracle-执行脚本:{}".format(info["ip"])),
        act_component_code=OracleExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    return sub_pipeline.build_sub_process(sub_name=_("Oracle--执行脚本--{}".format(info["domain"])))
