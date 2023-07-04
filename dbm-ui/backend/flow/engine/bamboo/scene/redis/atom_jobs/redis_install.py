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
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import AppCache
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.ticket.constants import TicketType

cluster_apply_ticket = [TicketType.REDIS_SINGLE_APPLY.value, TicketType.REDIS_CLUSTER_APPLY.value]

logger = logging.getLogger("flow")


def RedisBatchInstallAtomJob(root_id, ticket_data, sub_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    ### SubBuilder: Redis安装原籽任务
    #### 备注： 主从创建的时候， 不创建主从关系(包含元数据 以及真实的同步状态)

    Args:
        param (Dict): {
            "ip":"1.1.1.x",
            "ports":[],
            "meta_role":"redis_slave",
            "start_port":30000,
            "instance_numb":12,

            // 资源池新增 2023-06
            "spec_id": 0,
            "spec_config": "xx",
        }
    """
    act_kwargs = deepcopy(sub_kwargs)
    app = AppCache.get_app_attr(act_kwargs.cluster["bk_biz_id"], "db_app_abbr")
    app_name = AppCache.get_app_attr(act_kwargs.cluster["bk_biz_id"], "bk_biz_name")

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    exec_ip = param["ip"]
    if param["instance_numb"] != 0 and len(param["ports"]) == 0:
        for i in range(0, param["instance_numb"]):
            param["ports"].append(param["start_port"] + i)

    # 下发介质包
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_cluster_apply_backend(act_kwargs.cluster["db_version"])
    act_kwargs.exec_ip = exec_ip
    sub_pipeline.add_act(
        act_name=_("Redis-{}-下发介质包").format(exec_ip),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # ./dbactuator_redis --atom-job-list="sys_init"
    act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-初始化机器").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 安装Redis实例
    act_kwargs.cluster["exec_ip"] = exec_ip
    act_kwargs.cluster["start_port"] = param["start_port"]
    act_kwargs.cluster["inst_num"] = param["instance_numb"]
    act_kwargs.cluster["domain_name"] = act_kwargs.cluster["immute_domain"]
    if ticket_data["ticket_type"] in cluster_apply_ticket:
        #  集群申请单据时，下面参数需要从param中获取，不能从已有配置中获取
        act_kwargs.cluster["requirepass"] = param["requirepass"]
        act_kwargs.cluster["databases"] = param["databases"]
        act_kwargs.cluster["maxmemory"] = param["maxmemory"]
        act_kwargs.get_redis_payload_func = RedisActPayload.get_install_redis_apply_payload.__name__
    else:
        act_kwargs.get_redis_payload_func = RedisActPayload.get_redis_install_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-安装实例").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 写入元数据
    act_kwargs.cluster["spec_id"] = param.get("spec_id", 0)
    act_kwargs.cluster["spec_config"] = param.get("spec_config", {})
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_install.__name__
    if InstanceRole.REDIS_SLAVE.value == param["meta_role"]:
        act_kwargs.cluster["new_master_ips"] = []
        act_kwargs.cluster["new_slave_ips"] = [exec_ip]
    elif InstanceRole.REDIS_MASTER.value == param["meta_role"]:
        act_kwargs.cluster["new_master_ips"] = [exec_ip]
        act_kwargs.cluster["new_slave_ips"] = []
    else:
        raise Exception("unkown instance role {}:{}", param["meta_role"], exec_ip)
    sub_pipeline.add_act(
        act_name=_("Redis-{}-写入元数据").format(exec_ip),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 部署bkdbmon
    act_kwargs.cluster["servers"] = [
        {
            "app": app,
            "app_name": app_name,
            "bk_biz_id": str(act_kwargs.cluster["bk_biz_id"]),
            "bk_cloud_id": int(act_kwargs.cluster["bk_cloud_id"]),
            "server_ip": exec_ip,
            "server_ports": param["ports"],
            "meta_role": param["meta_role"],
            "cluster_type": act_kwargs.cluster["cluster_type"],
            "cluster_domain": act_kwargs.cluster["immute_domain"],
        }
    ]
    act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-安装监控").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=_("Redis-{}-安装原子任务").format(exec_ip))
