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

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


def RedisChangePwdAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    修改redis密码原子任务
    Args:
        param (Dict): {
            "change_ins":[{"ip":xx,"role":"xx"}]
            "port": 30000,
            "old_pwd": "",
            "new_pwd": "",

            "domain_name": "",
    }
    """
    domain_name = param["domain_name"]
    change_ins = param["change_ins"]
    port = param["port"]
    old_pwd = param["old_pwd"]
    new_pwd = param["new_pwd"]
    change_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    #  修改配置中心密码
    #  只有master的时候，才去修改配置中心密码
    act_kwargs.cluster = {
        "pwd_conf": {
            "proxy_pwd": new_pwd,
            "proxy_admin_pwd": new_pwd,
            "redis_pwd": new_pwd,
        },
        "domain_name": domain_name,
    }
    act_kwargs.get_redis_payload_func = RedisActPayload.update_cluster_password.__name__
    change_sub_pipeline.add_act(
        act_name=_("修改{}配置中心密码").format(domain_name),
        act_component_code=RedisConfigComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 如果是主从，修改的是master和slave的密码
    # 如果是集群，修改的是proxy的密码
    change_ins_param = [{"port": port, "old_password": old_pwd, "new_password": new_pwd}]
    acts_list = []
    for change_ins in change_ins:
        act_kwargs.exec_ip = change_ins["ip"]
        act_kwargs.cluster["role"] = change_ins["role"]
        act_kwargs.cluster["ins_param"] = change_ins_param
        act_kwargs.get_redis_payload_func = RedisActPayload.change_pwd.__name__
        acts_list.append(
            {
                "act_name": _("修改实例密码: {}:{}").format(change_ins["ip"], port),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
    change_sub_pipeline.add_parallel_acts(acts_list)
    return change_sub_pipeline.build_sub_process(sub_name=_("redis集群修改密码子任务"))
