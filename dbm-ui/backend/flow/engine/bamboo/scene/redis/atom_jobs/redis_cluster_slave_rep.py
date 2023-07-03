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
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_REDIS_START_PORT, SyncType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

from .redis_install import RedisBatchInstallAtomJob
from .redis_makesync import RedisMakeSyncAtomJob
from .redis_shutdown import RedisBatchShutdownAtomJob

logger = logging.getLogger("flow")


def RedisClusterSlaveReplaceJob(root_id, ticket_data, sub_kwargs: ActKwargs, slave_replace_detail: Dict) -> SubBuilder:
    """适用于 集群中Slave 机房裁撤/迁移替换场景
    步骤：   获取变更锁--> 新实例部署-->
            重建热备--> 检测同步状态-->
            Kill Dead链接--> 下架旧实例
    """
    act_kwargs = deepcopy(sub_kwargs)
    redis_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # ### 部署实例 ###############################################################################
    sub_pipelines = []
    for replace_link in slave_replace_detail:
        # "Old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
        old_slave = replace_link["old"]["ip"]
        new_slave = replace_link["new"]["ip"]
        params = {
            "ip": new_slave,
            "meta_role": InstanceRole.REDIS_SLAVE.value,
            "start_port": DEFAULT_REDIS_START_PORT,
            "ports": act_kwargs.cluster["slave_ports"][old_slave],
            "instance_numb": len(act_kwargs.cluster["slave_ports"][old_slave]),
        }
        sub_builder = RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, params)
        sub_pipelines.append(sub_builder)
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # ### 部署实例 ######################################################################## 完毕 ###

    # #### 建同步关系 ##############################################################################
    sub_pipelines = []
    for replace_link in slave_replace_detail:
        # "Old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
        old_slave = replace_link["old"]["ip"]
        new_slave = replace_link["new"]["ip"]
        install_params = {
            "sync_type": SyncType.SYNC_MS,
            "origin_1": act_kwargs.cluster["slave_master_map"][old_slave],
            "origin_2": old_slave,
            "sync_dst1": new_slave,
            "ins_link": [],
        }
        for slave_port in act_kwargs.cluster["slave_ports"][old_slave]:
            old_ins = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, slave_port)
            master_port = act_kwargs.cluster["slave_ins_map"].get(old_ins).split(IP_PORT_DIVIDER)[1]
            install_params["ins_link"].append({"origin_1": master_port, "sync_dst1": slave_port})
        sub_builder = RedisMakeSyncAtomJob(root_id, ticket_data, act_kwargs, install_params)
        sub_pipelines.append(sub_builder)
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # #### 建同步关系 ##################################################################### 完毕 ####

    # 新节点加入集群 ################################################################################
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_redo_slaves.__name__
    act_kwargs.cluster["old_slaves"] = []
    act_kwargs.cluster["created_by"] = ticket_data["created_by"]
    act_kwargs.cluster["tendiss"] = []
    for replace_link in slave_replace_detail:
        # "Old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
        old_slave = replace_link["old"]["ip"]
        new_slave = replace_link["new"]["ip"]
        act_kwargs.cluster["old_slaves"].append(
            {"ip": old_slave, "ports": act_kwargs.cluster["slave_ports"][old_slave]}
        )
        for slave_port in act_kwargs.cluster["slave_ports"][old_slave]:
            old_ins = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, slave_port)
            master = act_kwargs.cluster["slave_ins_map"].get(old_ins)
            act_kwargs.cluster["tendiss"].append(
                {
                    "ejector": {
                        "ip": master.split(IP_PORT_DIVIDER)[0],
                        "port": int(master.split(IP_PORT_DIVIDER)[1]),
                    },
                    "receiver": {"ip": new_slave, "port": int(slave_port)},
                }
            )
    redis_pipeline.add_act(
        act_name=_("Redis-新节点加入集群"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
    )
    # #### 新节点加入集群 ################################################################# 完毕 ###

    # #### 下架旧实例 ############################################################################
    sub_pipelines = []
    for replace_link in slave_replace_detail:
        # "Old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
        old_slave = replace_link["old"]["ip"]
        new_slave = replace_link["new"]["ip"]
        params = {
            "ignore_ips": act_kwargs.cluster["slave_master_map"][old_slave],
            "ip": old_slave,
            "ports": act_kwargs.cluster["slave_ports"][old_slave],
        }
        sub_builder = RedisBatchShutdownAtomJob(root_id, ticket_data, act_kwargs, params)
        sub_pipelines.append(sub_builder)
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # #### 下架旧实例 ###################################################################### 完毕 ###
    return redis_pipeline.build_sub_process(sub_name=_("Redis-{}-Slave替换").format(act_kwargs.cluster["immute_domain"]))
