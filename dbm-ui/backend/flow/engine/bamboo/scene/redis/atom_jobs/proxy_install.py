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

from backend.configuration.constants import DBType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.machine_type import MachineType
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


def ProxyBatchInstallAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    ### SubBuilder: Proxy安装原子任务
    act_kwargs.cluster = {
        "bk_biz_id": "",
        "immute_domain":"",
        "cluster_name":"",
        "bk_cloud_id":"",
        "created_by":""
        "cluster_type":"",
    }

    Args:
        param (Dict): {
            "ip":"1.1.1.x",
            "proxy_port": 30000,
            "redis_pwd":"",
            "proxy_pwd":"",
            "servers":"",

            "spec_id":0,
            "spec_config": "",
    }
    """
    app = AppCache.get_app_attr(act_kwargs.cluster["bk_biz_id"], "db_app_abbr")
    app_name = AppCache.get_app_attr(act_kwargs.cluster["bk_biz_id"], "bk_biz_name")
    #
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    exec_ip = param["ip"]

    # 下发介质包
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_cluster_apply_proxy(act_kwargs.cluster["cluster_type"])
    act_kwargs.exec_ip = exec_ip
    sub_pipeline.add_act(
        act_name=_("Proxy-001-{}-下发介质包").format(exec_ip),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(act_kwargs),
    )

    act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
    sub_pipeline.add_act(
        act_name=_("Proxy-002-{}-初始化机器").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # proxy扩容是，config从参数传过来
    if ticket_data["ticket_type"] == TicketType.PROXY_SCALE_UP.value:
        act_kwargs.cluster["conf_configs"] = param["conf_configs"]
        act_kwargs.cluster["dbconfig"] = param["conf_configs"]

    # 安装proxy实例
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
        act_kwargs.cluster["ip"] = exec_ip
        act_kwargs.cluster["db_type"] = act_kwargs.cluster["cluster_type"]
        act_kwargs.cluster["machine_type"] = MachineType.PREDIXY.value
        act_kwargs.cluster["redispasswd"] = param["redis_pwd"]
        act_kwargs.cluster["predixypasswd"] = param["proxy_pwd"]
        act_kwargs.cluster["port"] = param["proxy_port"]
        act_kwargs.cluster["servers"] = param["servers"]
        act_kwargs.get_redis_payload_func = RedisActPayload.get_install_predixy_payload.__name__
    else:
        act_kwargs.cluster["ip"] = exec_ip
        act_kwargs.cluster["db_type"] = act_kwargs.cluster["cluster_type"]
        act_kwargs.cluster["machine_type"] = MachineType.TWEMPROXY.value
        act_kwargs.cluster["redis_password"] = param["redis_pwd"]
        act_kwargs.cluster["password"] = param["proxy_pwd"]
        act_kwargs.cluster["port"] = param["proxy_port"]
        act_kwargs.cluster["servers"] = param["servers"]
        act_kwargs.get_redis_payload_func = RedisActPayload.get_install_twemproxy_payload.__name__
    sub_pipeline.add_act(
        act_name=_("Proxy-003-{}-安装实例").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 写入元数据
    act_kwargs.cluster["new_proxy_ips"] = [exec_ip]
    act_kwargs.cluster["spec_id"] = param["spec_id"]
    act_kwargs.cluster["spec_config"] = param["spec_config"]
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.proxy_install.__name__
    sub_pipeline.add_act(
        act_name=_("Proxy-004-{}-写入元数据").format(exec_ip),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 部署bkdbmon
    act_kwargs.cluster["servers"] = [
        {
            "bk_biz_id": str(act_kwargs.cluster["bk_biz_id"]),
            "bk_cloud_id": int(act_kwargs.cluster["bk_cloud_id"]),
            "server_ports": [param["proxy_port"]],
            "meta_role": act_kwargs.cluster["machine_type"],
            "cluster_domain": act_kwargs.cluster["immute_domain"],
            "app": app,
            "app_name": app_name,
            "cluster_name": act_kwargs.cluster["cluster_name"],
            "cluster_type": act_kwargs.cluster["cluster_type"],
        }
    ]
    act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
    sub_pipeline.add_act(
        act_name=_("Proxy-005-{}-安装监控").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=_("Proxy-{}-安装原子任务").format(exec_ip))
