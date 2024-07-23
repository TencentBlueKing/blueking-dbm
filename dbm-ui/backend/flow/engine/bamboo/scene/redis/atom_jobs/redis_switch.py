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
from typing import List

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import SwitchType, SyncType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

from .redis_dbmon import ClusterDbmonInstallAtomJob

logger = logging.getLogger("flow")


# 统一入口，兼容多种集群切换方案
def RedisClusterSwitchAtomJob(root_id, data, act_kwargs: ActKwargs, sync_params: List) -> SubBuilder:
    """
        sub_kwargs.cluster["switch_condition"] = {
            "switch_option":"",
            "is_check_sync": force,  # 强制切换
            "sync_type": SyncType.SYNC_MS.value,
            "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
            "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
            "can_write_before_switch": True,
        }
        sync_params = [{
            "origin_1": "master_ip",
            "origin_2": "slave_ip",
            "sync_dst1": "slave_ip",
            "sync_dst2": "slave_ip",
            "ins_link": [
                {"origin_1": 30000,
                "origin_2": 30000,
                "sync_dst1": 30000,
                "sync_dst2": 30000},],
        }]
    ## Redis 集群切换功能
    #### A. TendisCache
    #### B. TendisSSD
    #### C. Tendisplus
    #### D. RedisCluster
    #### 切换按照 Redis 实例并行搞

    ## RedisInstance 主从版-切换功能
    ####  A. 故障切换场景:
    ####  B. 整机替换场景:
    ####  C. 实例扩容场景:
       1. slave上:检查同步/(master 可能挂掉了)
       2. slave上:执行切换
       3. 修改dns,dbm元数据,bkcc
       4. slave上:远程连接master,尝试关闭master
    """

    sub_pipeline, exec_ip = SubBuilder(root_id=root_id, data=data), "127.0.0.x"
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value:
        exec_ip = sync_params[0]["sync_dst1"]
    else:
        exec_ip = act_kwargs.cluster["proxy_ips"][0]

    # 节点信息加入到集群，使的可以获取到集群的配置 （DBHA 可以提前监控）
    if not SyncType.SYNC_MS.value == act_kwargs.cluster["switch_condition"]["sync_type"]:
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

    # 人工确认
    if (
        act_kwargs.cluster.get("switch_option", SwitchType.SWITCH_WITH_CONFIRM.value)
        == SwitchType.SWITCH_WITH_CONFIRM.value
    ):
        sub_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})

    # 实际实例切换，修改proxy指向
    act_kwargs.cluster["switch_info"] = []
    for sync_host in sync_params:
        for sync_port in sync_host["ins_link"]:
            act_kwargs.cluster["switch_info"].append(
                {
                    "master": {
                        "ip": sync_host["origin_1"],
                        "port": int(sync_port["origin_1"]),
                    },
                    "slave": {
                        "ip": sync_host["sync_dst1"],
                        "port": int(sync_port["sync_dst1"]),
                    },
                }
            )
    act_kwargs.cluster["db_version"] = act_kwargs.cluster["db_version"]
    act_kwargs.cluster["domain_name"] = act_kwargs.cluster["immute_domain"]
    act_kwargs.cluster["switch_condition"] = act_kwargs.cluster["switch_condition"]
    act_kwargs.get_redis_payload_func = RedisActPayload.redis__switch_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-{}-实例切换").format(exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # 检查Proxy后端一致性
    if act_kwargs.cluster["cluster_type"] in [
        ClusterType.TwemproxyTendisSSDInstance,
        ClusterType.TendisTwemproxyRedisInstance,
    ]:
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_twemproxy_backends_4_scene.__name__
        sub_pipeline.add_act(
            act_name=_("{}-检查切换状态").format(exec_ip),
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
                        "port": int(sync_port["origin_1"]),
                    },
                    "receiver": {
                        "ip": sync_host["sync_dst1"],
                        "port": int(sync_port["sync_dst1"]),
                    },
                }
            )
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.tendis_switch_4_scene.__name__
    sub_pipeline.add_act(act_name=_("元数据切换"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs))

    sub_pipeline.add_sub_pipeline(
        ClusterDbmonInstallAtomJob(
            root_id,
            data,
            act_kwargs,
            {
                "cluster_domain": act_kwargs.cluster["immute_domain"],
                "is_stop": False,
            },
        )
    )

    return sub_pipeline.build_sub_process(sub_name=_("{}-实例切换").format(act_kwargs.cluster["immute_domain"]))
