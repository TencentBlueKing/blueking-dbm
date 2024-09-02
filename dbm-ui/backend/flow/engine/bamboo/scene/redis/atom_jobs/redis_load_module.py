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
import logging
from copy import deepcopy
from dataclasses import asdict
from typing import Dict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis.redis_modules.util import get_redis_moudles_detail
from backend.db_services.redis.util import is_predixy_proxy_type
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


def ClusterLoadModulesAtomJob(root_id, ticket_data, sub_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    @summary: 集群加载模块
    @param params(Dict):{
        "cluster_id": 11,
        "load_modules":["redisbloom","redisjson","rediscell"],
        "cluster_info": {} # 参考 get_cluster_info_by_cluster_id(cluster_id) 返回值
    }
    """
    cluster = Cluster.objects.get(id=param["cluster_id"])
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    act_kwargs = deepcopy(sub_kwargs)
    act_kwargs.cluster = {}
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_load_module()

    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )

    meata_all_ips = set()
    for inst in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
        meata_all_ips.add(f"{inst.machine.ip}")

    for inst in cluster.storageinstance_set.filter(status=InstanceStatus.RUNNING):
        meata_all_ips.add(f"{inst.machine.ip}")

    # 介质下发
    act_kwargs.exec_ip = list(meata_all_ips)
    sub_pipeline.add_act(
        act_name=_("下发介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # redis 加载module
    cluster_info = param["cluster_info"]
    acts_list = []
    for ip, ports in cluster_info["master_ports"].items():
        act_kwargs.exec_ip = ip
        act_kwargs.cluster["ip"] = ip
        act_kwargs.cluster["ports"] = ports
        act_kwargs.cluster["load_modules_detail"] = get_redis_moudles_detail(
            cluster.major_version, param["load_modules"]
        )
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_load_modules.__name__
        acts_list.append(
            {
                "act_name": _("master:{}-加载module").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )

    for ip, ports in cluster_info["slave_ports"].items():
        act_kwargs.exec_ip = ip
        act_kwargs.cluster["ip"] = ip
        act_kwargs.cluster["ports"] = ports
        act_kwargs.cluster["load_modules_detail"] = get_redis_moudles_detail(
            cluster.major_version, param["load_modules"]
        )
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_load_modules.__name__
        acts_list.append(
            {
                "act_name": _("slave:{}-加载module").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
    if acts_list:
        sub_pipeline.add_parallel_acts(acts_list)

    logger.info("===>redis acts list count:{}".format(len(acts_list)))

    # 如果predixy集群,则predixy加载module
    if is_predixy_proxy_type(cluster.cluster_type):
        acts_list = []
        proxy_port = cluster_info["proxy_port"]
        for ip in cluster_info["proxy_ips"]:
            act_kwargs.exec_ip = ip
            act_kwargs.cluster["ip"] = ip
            act_kwargs.cluster["port"] = proxy_port
            act_kwargs.cluster["load_modules"] = param["load_modules"]
            act_kwargs.cluster["cluster_type"] = cluster.cluster_type
            act_kwargs.get_redis_payload_func = RedisActPayload.predixy_add_modules_cmds.__name__
            acts_list.append(
                {
                    "act_name": _("predixy:{}-加载module命令").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        if acts_list:
            sub_pipeline.add_parallel_acts(acts_list)

    # 修改dbconfig配置
    act_kwargs.cluster = {"cluster_id": param["cluster_id"], "load_modules": param["load_modules"]}
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_add_modules_update_dbconfig.__name__
    sub_pipeline.add_act(
        act_name=_("更新集群dbconfig配置"),
        act_component_code=RedisConfigComponent.code,
        kwargs=asdict(act_kwargs),
    )
    logger.info("===>redis config")

    return sub_pipeline.build_sub_process(sub_name=_("{}-集群加载modules").format(cluster.immute_domain))
