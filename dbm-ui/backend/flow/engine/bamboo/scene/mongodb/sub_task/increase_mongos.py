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
from backend.flow.plugins.components.collections.mongodb.add_domain_to_dns import ExecAddDomainToDnsOperationComponent
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.mongos_scale_4_meta import MongosScaleMetaComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

from .mongos_install import mongos_install


def increase_mongos(root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict) -> SubBuilder:
    """
    cluster 增加mongos流程
    info 表示cluster信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 设置参数
    sub_get_kwargs.payload["db_version"] = info["db_version"]

    # 获取机器
    sub_get_kwargs.get_host_scale_mongos(info=info, increase=True)

    # 介质下发
    kwargs = sub_get_kwargs.get_send_media_kwargs(media_type="all")
    sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 创建原子任务执行目录
    kwargs = sub_get_kwargs.get_create_dir_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 机器初始化
    kwargs = sub_get_kwargs.get_os_init_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-机器初始化"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 获取信息
    sub_get_kwargs.get_cluster_info_deinstall(cluster_id=info["cluster_id"])
    sub_get_kwargs.payload["cluster_id"] = info["cluster_id"]
    sub_get_kwargs.cluster_type = sub_get_kwargs.payload["cluster_type"]
    sub_get_kwargs.mongos_info = info
    sub_get_kwargs.mongos_info["nodes"] = info["mongos"]
    sub_get_kwargs.mongos_info["port"] = sub_get_kwargs.payload["mongos_nodes"][0]["port"]
    sub_get_kwargs.payload["config"] = {}
    sub_get_kwargs.payload["config"]["nodes"] = sub_get_kwargs.payload["config_nodes"]
    sub_get_kwargs.payload["config"]["port"] = sub_get_kwargs.payload["config_nodes"][0]["port"]
    sub_get_kwargs.payload["app"] = sub_get_kwargs.payload["db_app_abbr"]
    cluster_name = info["cluster_name"]
    sub_get_kwargs.mongos_info["set_id"] = cluster_name
    sub_get_kwargs.db_main_version = str(info["db_version"].split(".")[0])
    sub_get_kwargs.payload["key_file"] = sub_get_kwargs.get_key_file(cluster_name=cluster_name)
    sub_get_kwargs.payload["nodes"] = []
    sub_get_kwargs.payload["nodes"].append(sub_get_kwargs.payload["mongos_nodes"][0])
    sub_get_kwargs.payload["mongos"] = {}
    sub_get_kwargs.payload["mongos"]["nodes"] = info["mongos"]
    sub_get_kwargs.payload["mongos"]["domain"] = sub_get_kwargs.payload["mongos_nodes"][0]["domain"]
    sub_get_kwargs.payload["mongos"]["port"] = sub_get_kwargs.payload["mongos_nodes"][0]["port"]

    # 进行mongos安装——子流程
    sub_sub_pipeline = mongos_install(
        root_id=root_id,
        ticket_data=ticket_data,
        sub_kwargs=sub_get_kwargs,
        increase_mongos=True,
    )
    sub_pipeline.add_sub_pipeline(sub_sub_pipeline)

    # dns新增实例
    kwargs = sub_get_kwargs.get_add_domain_to_dns_kwargs(cluster=True)
    sub_pipeline.add_act(
        act_name=_("MongoDB--添加domain到dns"),
        act_component_code=ExecAddDomainToDnsOperationComponent.code,
        kwargs=kwargs,
    )

    # 修改db_meta数据
    kwargs = sub_get_kwargs.get_change_meta_mongos_kwargs(increase=True)
    sub_pipeline.add_act(
        act_name=_("MongoDB--修改meta"),
        act_component_code=MongosScaleMetaComponent.code,
        kwargs=kwargs,
    )

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--{}增加mongos".format(cluster_name)))
