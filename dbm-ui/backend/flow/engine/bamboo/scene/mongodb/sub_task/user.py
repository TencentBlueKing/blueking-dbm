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

from backend.flow.consts import MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def user(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, cluster_id: int, create: bool, info: dict
) -> SubBuilder:
    """
    单个cluster 创建/删除用户流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取信息
    sub_get_kwargs.get_cluster_info_user(cluster_id=cluster_id, admin_user=MongoDBManagerUser.DbaUser.value)

    # 介质下发
    kwargs = sub_get_kwargs.get_send_media_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 创建或删除用户
    print("info:", info)
    kwargs = sub_get_kwargs.get_user_kwargs(create=create, admin_user=MongoDBManagerUser.DbaUser.value, info=info)
    if create:
        act_name = _("MongoDB-cluster_id:{}-创建用户:{}".format(str(cluster_id), info["username"]))
        sub_name = _(
            "MongoDB--创建用户--cluster_id:{}-{}".format(str(cluster_id), sub_get_kwargs.payload["hosts"][0]["ip"])
        )
    else:
        act_name = _("MongoDB-cluster_id:{}-删除用户:{}".format(str(cluster_id), info["username"]))
        sub_name = _(
            "MongoDB--删除用户--cluster_id:{}-{}".format(str(cluster_id), sub_get_kwargs.payload["hosts"][0]["ip"])
        )
    sub_pipeline.add_act(act_name=act_name, act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs)

    return sub_pipeline.build_sub_process(sub_name=sub_name)
