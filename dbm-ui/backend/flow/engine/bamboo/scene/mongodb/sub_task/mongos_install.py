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

from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.add_password_to_db import (
    ExecAddPasswordToDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def mongos_install(root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs) -> SubBuilder:
    """
    多个mongos安装流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)
    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # mongod安装——并行
    acts_list = []
    for node in sub_get_kwargs.mongos_info["nodes"]:
        kwargs = sub_get_kwargs.get_install_mongos_kwargs(node=node)
        acts_list.append(
            {
                "act_name": _("MongoDB-{}-mongos安装".format(node["ip"])),
                "act_component_code": ExecuteDBActuatorJobComponent.code,
                "kwargs": kwargs,
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # dba，appdba，monitor，monitor用户用户密码写入密码服务
    kwargs = sub_get_kwargs.get_add_password_to_db_kwargs(
        usernames=[MediumEnum.DbaUser, MediumEnum.AppDbaUser, MediumEnum.MonitorUser, MediumEnum.AppMonitorUser],
        info=sub_get_kwargs.mongos_info,
    )
    sub_pipeline.add_act(
        act_name=_("MongoDB--保存dba用户及额外管理用户密码"),
        act_component_code=ExecAddPasswordToDBOperationComponent.code,
        kwargs=kwargs,
    )

    # 安装监控

    return sub_pipeline.build_sub_process(
        sub_name=_(
            "MongoDB--安装mongos--{}-{}".format(sub_get_kwargs.payload["app"], sub_get_kwargs.replicaset_info["areaId"])
        )
    )
