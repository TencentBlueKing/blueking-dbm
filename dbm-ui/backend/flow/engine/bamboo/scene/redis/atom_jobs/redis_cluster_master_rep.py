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
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_LAST_IO_SECOND_AGO, DEFAULT_MASTER_DIFF_TIME, DEFAULT_REDIS_START_PORT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

from .redis_install import RedisBatchInstallAtomJob
from .redis_makesync import RedisMakeSyncAtomJob
from .redis_shutdown import RedisBatchShutdownAtomJob
from .redis_switch import RedisClusterSwitchAtomJob

logger = logging.getLogger("flow")


def RedisClusterMasterReplaceJob(
    root_id, ticket_data, sub_kwargs: ActKwargs, master_replace_detail: Dict
) -> SubBuilder:
    """### 适用于 集群中Master 机房裁撤/迁移替换场景 (成对替换)
    步骤：   获取变更锁--> 新实例部署-->
            建Sync关系--> 检测同步状态
            Kill Dead链接--> 下架旧实例

            master_replace_detail:[{
                "old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
                "new": [
                    {"ip": "2.b.3.4", "bk_cloud_id": 0, "bk_host_id": 123},
                    {"ip": "2.b.3.4", "bk_cloud_id": 0, "bk_host_id": 123}
                ]
            }]
    """
    act_kwargs = deepcopy(sub_kwargs)
    redis_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # ## 部署实例 #############################################################################
    sub_pipelines = []
    for replace_info in master_replace_detail:
        old_master = replace_info["old"]["ip"]
        new_host_master = replace_info["new"][0]["ip"]
        new_host_slave = replace_info["new"][1]["ip"]
        # 安装Master
        params = {
            "ip": new_host_master,
            "ports": [],
            "meta_role": InstanceRole.REDIS_MASTER.value,
            "start_port": DEFAULT_REDIS_START_PORT,
            "instance_numb": len(act_kwargs.cluster["master_ports"][old_master]),
        }
        sub_pipelines.append(RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, params))

        # 安装slave
        params["ip"] = new_host_slave
        params["meta_role"] = InstanceRole.REDIS_SLAVE.value
        sub_pipelines.append(RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, params))
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # ### 部署实例 ####################################################################### 完毕 ###

    sync_relations, new_slave_ports = [], []  # 按照机器对组合
    # #### 建同步关系 #############################################################################
    sub_pipelines, sync_kwargs = [], deepcopy(act_kwargs)
    for replace_info in master_replace_detail:
        old_master = replace_info["old"]["ip"]
        new_host_master = replace_info["new"][0]["ip"]
        new_host_slave = replace_info["new"][1]["ip"]
        sync_params = {
            "sync_type": act_kwargs.cluster["sync_type"],
            "origin_1": old_master,
            "origin_2": act_kwargs.cluster["master_slave_map"][old_master],
            "sync_dst1": new_host_master,
            "sync_dst2": new_host_slave,
            "ins_link": [],
        }
        new_ins_port = DEFAULT_REDIS_START_PORT
        master_ports = act_kwargs.cluster["master_ports"][old_master]
        master_ports.sort()
        for old_master_port in master_ports:
            old_master_ins = "{}{}{}".format(old_master, IP_PORT_DIVIDER, old_master_port)
            old_slave_ins = act_kwargs.cluster["ins_pair_map"][old_master_ins]
            new_slave_ports.append(new_ins_port)
            sync_params["ins_link"].append(
                {
                    "origin_1": old_master_port,
                    "origin_2": old_slave_ins.split(IP_PORT_DIVIDER)[1],
                    "sync_dst1": new_ins_port,
                    "sync_dst2": new_ins_port,
                }
            )
            new_ins_port = new_ins_port + 1
        sync_relations.append(sync_params)
        sub_builder = RedisMakeSyncAtomJob(root_id, ticket_data, sync_kwargs, sync_params)
        sub_pipelines.append(sub_builder)
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # ### 建同步关系 ####################################################################### 完毕 ###

    # 执行切换 #####################################################################################
    act_kwargs.cluster["switch_condition"] = {
        "is_check_sync": True,  # 不强制切换
        "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
        "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
        "can_write_before_switch": True,
        "sync_type": act_kwargs.cluster["sync_type"],
    }
    sub_pipeline = RedisClusterSwitchAtomJob(root_id, ticket_data, act_kwargs, sync_relations)
    redis_pipeline.add_sub_pipeline(sub_flow=sub_pipeline)
    # #### 执行切换 ###############################################################################

    # #### 下架旧实例 #############################################################################
    sub_pipelines, shutdown_kwargs = [], deepcopy(act_kwargs)
    for replace_info in master_replace_detail:
        old_master = replace_info["old"]["ip"]
        params = {
            "ip": old_master,
            "ports": act_kwargs.cluster["master_ports"][old_master],
        }
        sub_builder = RedisBatchShutdownAtomJob(root_id, ticket_data, shutdown_kwargs, params)
        sub_pipelines.append(sub_builder)
        # 旧的slave 实例也要一起下架
        old_slave = act_kwargs.cluster["master_slave_map"][old_master]
        params = {
            "ip": old_slave,
            "ports": act_kwargs.cluster["slave_ports"][old_slave],
        }
        sub_builder = RedisBatchShutdownAtomJob(root_id, ticket_data, shutdown_kwargs, params)
        sub_pipelines.append(sub_builder)
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # #### 下架旧实例 ###################################################################### 完毕 ###

    return redis_pipeline.build_sub_process(
        sub_name=_("Redis-{}-Master替换").format(act_kwargs.cluster["immute_domain"])
    )
