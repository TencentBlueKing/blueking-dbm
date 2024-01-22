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
from typing import Dict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_predixy_proxy_type
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


def ClusterPredixyConfigServersRewriteAtomJob(root_id, ticket_data, sub_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    ### SubBuilder: 集群Predixy配置文件servers rewrite
    注意: 可能返回 None,所以返回结果需判断一下
    Args:
        param (Dict): {
            "cluster_domain": "cache.test.testapp.db",
            "to_remove_servers": ["a.a.a.a:30000","b.b.b.b:30000"]
    """
    cluster = Cluster.objects.get(immute_domain=param["cluster_domain"])
    if not is_predixy_proxy_type(cluster.cluster_type):
        return None
    predixy_ips = set()
    predixy_port = 0
    for proxy in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
        predixy_ips.add(proxy.machine.ip)
        predixy_port = proxy.port
    if not predixy_ips:
        return None

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    act_kwargs = deepcopy(sub_kwargs)
    act_kwargs.cluster = {}
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_actuator_backend()

    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )

    acts_list = []
    for ip in predixy_ips:
        # 下发介质
        act_kwargs.exec_ip = ip
        acts_list.append(
            {
                "act_name": _("{}-下发介质包").format(ip),
                "act_component_code": TransFileComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
    if acts_list:
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    acts_list = []
    for ip in predixy_ips:
        act_kwargs.exec_ip = ip
        act_kwargs.cluster = {
            "predixy_ip": ip,
            "predixy_port": predixy_port,
            "to_remove_servers": param.get("to_remove_servers", []),
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.predixy_config_servers_rewrite.__name__
        acts_list.append(
            {
                "act_name": _("{}-rewrite配置servers").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
    if acts_list:
        sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("{}-predixy rewrite配置servers").format(param["cluster_domain"]))
