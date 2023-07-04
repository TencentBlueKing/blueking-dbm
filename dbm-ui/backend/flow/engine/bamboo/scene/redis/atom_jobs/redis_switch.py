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
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.api.cluster import nosqlcomm
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


def RedisClusterSwitchAtomJob(root_id, data, act_kwargs: ActKwargs, sync_params: List) -> SubBuilder:
    """### Redis 集群切换功能 TODO
    TendisCache/TendisSSD ？
    按照 Redis 实例并行切换
    {
        "switch_condition":{
            "is_check_sync":true,
            "slave_master_diff_time":61,
            "last_io_second_ago":100,
            "can_write_before_switch":true,
            "sync_type":"msms"
        }
    }
    """

    sub_pipeline = SubBuilder(root_id=root_id, data=data)
    exec_ip = act_kwargs.cluster["proxy_ips"][0]

    # 节点信息加入到集群，使的可以获取到集群的配置 （DBHA 可以提前监控）
    act_kwargs.cluster["sync_relation"] = []
    for sync_host in sync_params:
        for sync_port in sync_host["ins_link"]:
            act_kwargs.cluster["sync_relation"].append(
                {
                    "old_ejector": {  # not important , but must have.
                        "ip": sync_host["origin_1"],
                        "port": sync_port["origin_1"],
                    },
                    "ejector": {
                        "ip": sync_host["sync_dst1"],
                        "port": sync_port["sync_dst1"],
                    },
                    "receiver": {
                        "ip": sync_host["sync_dst2"],
                        "port": sync_port["sync_dst2"],
                    },
                }
            )
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_replace_pair.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-元数据加入集群"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
    )

    # # 人工确认 TODO 4 Test.
    # sub_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})

    # 下发介质包
    act_kwargs.exec_ip = exec_ip
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_dbmon()
    act_kwargs.cluster["exec_ip"] = exec_ip
    sub_pipeline.add_act(
        act_name=_("Redis-{}-下发介质包").format(exec_ip),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 实际实例切换，修改proxy指向
    act_kwargs.cluster["switch_info"] = []
    for sync_host in sync_params:
        for sync_port in sync_host["ins_link"]:
            act_kwargs.cluster["switch_info"].append(
                {
                    "master": {
                        "ip": sync_host["origin_1"],
                        "port": sync_port["origin_1"],
                    },
                    "slave": {
                        "ip": sync_host["sync_dst1"],
                        "port": sync_port["sync_dst1"],
                    },
                }
            )
    act_kwargs.cluster["domain_name"] = act_kwargs.cluster["immute_domain"]
    act_kwargs.cluster["switch_condition"] = act_kwargs.cluster["switch_condition"]
    act_kwargs.cluster["cluster_meta"] = nosqlcomm.other.get_cluster_detail(
        cluster_id=act_kwargs.cluster["cluster_id"]
    )[0]
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_twemproxy_arch_switch_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-实例切换").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 检查Proxy后端一致性
    act_kwargs.cluster["instances"] = nosqlcomm.other.get_cluster_proxies(cluster_id=act_kwargs.cluster["cluster_id"])
    act_kwargs.get_redis_payload_func = RedisActPayload.redis_twemproxy_backends_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-检查切换状态").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 修改元数据指向，并娜动CC模块
    act_kwargs.cluster["sync_relation"] = []
    for sync_host in sync_params:
        for sync_port in sync_host["ins_link"]:
            act_kwargs.cluster["sync_relation"].append(
                {
                    "ejector": {
                        "ip": sync_host["origin_1"],
                        "port": sync_port["origin_1"],
                    },
                    "receiver": {
                        "ip": sync_host["sync_dst1"],
                        "port": sync_port["sync_dst1"],
                    },
                }
            )
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.tendis_switch_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-元数据切换"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
    )

    return sub_pipeline.build_sub_process(sub_name=_("Redis-{}-实例切换").format(act_kwargs.cluster["immute_domain"]))
