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

from backend.flow.consts import MongoDBManagerUser, MongoDBTask
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.add_domain_to_dns import ExecAddDomainToDnsOperationComponent
from backend.flow.plugins.components.collections.mongodb.add_password_to_db import (
    ExecAddPasswordToDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.get_manager_user_password import (
    ExecGetPasswordOperationComponent,
)
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def replicaset_install(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_kwargs: ActKwargs,
    cluster: bool,
    cluster_role: str,
    config_svr: bool,
) -> SubBuilder:
    """
    单个replicaset安装流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)
    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # mongod安装——并行
    acts_list = []
    for node in sub_get_kwargs.replicaset_info["nodes"]:
        kwargs = sub_get_kwargs.get_install_mongod_kwargs(node=node, cluster_role=cluster_role)
        acts_list.append(
            {
                "act_name": _("MongoDB-{}-mongod安装".format(node["ip"])),
                "act_component_code": ExecuteDBActuatorJobComponent.code,
                "kwargs": kwargs,
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 创建复制集
    kwargs = sub_get_kwargs.get_replicaset_init_kwargs(config_svr=config_svr)
    sub_pipeline.add_act(
        act_name=_("MongoDB-{}-replicaset初始化".format(sub_get_kwargs.replicaset_info["nodes"][0]["ip"])),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    if not cluster:
        # 密码服务获取管理用户密码
        kwargs = sub_get_kwargs.get_get_manager_password_kwargs()
        sub_pipeline.add_act(
            act_name=_("MongoDB--获取管理员用户密码"), act_component_code=ExecGetPasswordOperationComponent.code, kwargs=kwargs
        )

    # 创建dba用户
    kwargs = sub_get_kwargs.get_add_manager_user_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB--创建dba用户"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 创建appdba，monitor，monitor用户
    kwargs = sub_get_kwargs.get_init_exec_script_kwargs(script_type=MongoDBTask.MongoDBExtraUserCreate)
    sub_pipeline.add_act(
        act_name=_("MongoDB--创建额外管理用户"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # dba, appdba，monitor，monitor用户密码写入密码服务
    kwargs = sub_get_kwargs.get_add_password_to_db_kwargs(
        usernames=[
            MongoDBManagerUser.DbaUser.value,
            MongoDBManagerUser.AppDbaUser.value,
            MongoDBManagerUser.MonitorUser.value,
            MongoDBManagerUser.AppMonitorUser.value,
        ],
        info=sub_get_kwargs.replicaset_info,
    )
    sub_pipeline.add_act(
        act_name=_("MongoDB--保存dba用户及额外管理用户密码"),
        act_component_code=ExecAddPasswordToDBOperationComponent.code,
        kwargs=kwargs,
    )

    # 进行初始配置
    # 创建oplog重放权限的role，把role授权给dba，appdba 把admin库的gcs_heartbeat授予给monitor用户
    # 3.x版本修改验证方式
    kwargs = sub_get_kwargs.get_init_exec_script_kwargs(script_type=MongoDBTask.MongoDBInitSet)
    sub_pipeline.add_act(
        act_name=_("MongoDB-{}-db初始设置".format(sub_get_kwargs.replicaset_info["nodes"][0]["ip"])),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    if not cluster:
        # 域名写入dns
        kwargs = sub_get_kwargs.get_add_domain_to_dns_kwargs(cluster=False)
        sub_pipeline.add_act(
            act_name=_("MongoDB--添加domain到dns"),
            act_component_code=ExecAddDomainToDnsOperationComponent.code,
            kwargs=kwargs,
        )

    # 安装监控

    return sub_pipeline.build_sub_process(
        sub_name=_(
            "MongoDB--安装复制集--{}-{}".format(sub_get_kwargs.payload["app"], sub_get_kwargs.replicaset_info["set_id"])
        )
    )
