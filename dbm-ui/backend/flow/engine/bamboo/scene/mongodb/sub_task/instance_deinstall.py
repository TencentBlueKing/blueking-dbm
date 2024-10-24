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

from backend.flow.consts import MongoDBInstanceType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def instance_deinstall(root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict) -> SubBuilder:
    """
    instance deinstall流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取参数
    instance_type = ""
    if info["role"] == MongoDBInstanceType.MongoD.value:
        instance_type = MongoDBInstanceType.MongoD.value
    elif info["role"] == MongoDBInstanceType.MongoS.value:
        instance_type = MongoDBInstanceType.MongoS.value
    sub_get_kwargs.payload["bk_cloud_id"] = info["bk_cloud_id"]
    sub_get_kwargs.payload["set_id"] = ""
    # 下架实例
    kwargs = sub_get_kwargs.get_mongo_deinstall_kwargs(
        node_info=info,
        instance_type=instance_type,
        nodes_info=[info],
        force=True,
        rename_dir=True,
    )
    sub_sub_pipeline.add_act(
        act_name=_("实例下架-{}:{}".format(info["ip"], str(info["port"]))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    return sub_sub_pipeline.build_sub_process(sub_name=_("MongoDB--实例下架--{}:{}".format(info["ip"], str(info["port"]))))
