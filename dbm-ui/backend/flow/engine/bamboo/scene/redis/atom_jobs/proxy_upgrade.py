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
from backend.db_services.redis.redis_dts.util import get_cluster_info_by_id
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


def ClusterProxysUpgradeAtomJob(root_id, ticket_data, sub_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    ### SubBuilder: 集群所有proxy升级版本
    Args:
        param (Dict): {
            "cluster_domain": "cache.test.testapp.db"
        }
    """
    cluster_ips_set = set()
    cluster = Cluster.objects.get(immute_domain=param["cluster_domain"])
    for proxy in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
        cluster_ips_set.add(proxy.machine.ip)
    cluster_info = get_cluster_info_by_id(bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id)

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    act_kwargs = deepcopy(sub_kwargs)
    act_kwargs.cluster = {}
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_cluster_apply_proxy(cluster.cluster_type)

    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )

    acts_list = []
    for ip in cluster_ips_set:
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
    for ip in cluster_ips_set:
        act_kwargs.exec_ip = ip
        act_kwargs.cluster = {
            "ip": ip,
            "port": cluster_info["cluster_port"],
            "password": cluster_info["cluster_password"],
            "cluster_type": cluster.cluster_type,
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_proxy_upgrade_online_payload.__name__
        acts_list.append(
            {
                "act_name": _("{}-proxy版本升级").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
    if acts_list:
        sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("{}-集群proxy版本升级").format(param["cluster_domain"]))
