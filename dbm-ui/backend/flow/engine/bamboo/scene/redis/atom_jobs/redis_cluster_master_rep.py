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

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.consts import (
    DEFAULT_LAST_IO_SECOND_AGO,
    DEFAULT_MASTER_DIFF_TIME,
    DEFAULT_REDIS_START_PORT,
    SyncType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellReloadMetaComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

from .redis_cluster_slave_rep import RedisClusterSlaveReplaceJob
from .redis_install import RedisBatchInstallAtomJob
from .redis_makesync import RedisMakeSyncAtomJob
from .redis_shutdown import RedisBatchShutdownAtomJob
from .redis_switch import RedisClusterSwitchAtomJob

logger = logging.getLogger("flow")


def RedisClusterMasterReplaceJob(root_id, ticket_data, sub_kwargs: ActKwargs, master_replace_info: Dict) -> SubBuilder:
    if sub_kwargs.cluster["cluster_type"] in [
        ClusterType.TwemproxyTendisSSDInstance,
        ClusterType.TendisTwemproxyRedisInstance,
    ]:
        return TwemproxyClusterMasterReplaceJob(root_id, ticket_data, sub_kwargs, master_replace_info)

    elif sub_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster:
        return TendisClusterMasterReplaceJob(root_id, ticket_data, sub_kwargs, master_replace_info)

    else:
        raise Exception(
            "unsupported cluster type {}:{}".format(
                sub_kwargs.cluster["immute_domain"], sub_kwargs.cluster["cluster_type"]
            )
        )


def TwemproxyClusterMasterReplaceJob(
    root_id, ticket_data, sub_kwargs: ActKwargs, master_replace_info: Dict
) -> SubBuilder:
    """### 适用于 集群中Master 机房裁撤/迁移替换场景 (成对替换)
    步骤：   获取变更锁--> 新实例部署-->
            建Sync关系--> 检测同步状态
            Kill Dead链接--> 下架旧实例

            master_replace_detail:[{
                {"ip": "1.1.1.c","spec_id": 17,
                  "target": {
                      "master": {"bk_cloud_id": 0,"bk_host_id": 195,"status": 1,"ip": "2.2.2.b"},
                      "slave": {"bk_cloud_id": 0,"bk_host_id": 187,"status": 1,"ip": "3.3.3.x"}}
              }]
    """
    act_kwargs = deepcopy(sub_kwargs)
    redis_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # ## 部署实例 #############################################################################
    sub_pipelines = []
    master_replace_detail = master_replace_info["redis_master"]
    for replace_info in master_replace_detail:
        old_master = replace_info["ip"]
        new_host_master = replace_info["target"]["master"]["ip"]
        new_host_slave = replace_info["target"]["slave"]["ip"]
        # 安装Master
        params = {
            "ip": new_host_master,
            "ports": [],
            "meta_role": InstanceRole.REDIS_MASTER.value,
            "start_port": DEFAULT_REDIS_START_PORT,
            "instance_numb": len(act_kwargs.cluster["master_ports"][old_master]),
            "spec_id": master_replace_info["master_spec"].get("id", 0),
            "spec_config": master_replace_info["master_spec"],
        }
        sub_pipelines.append(RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, params))

        # 安装slave
        params["ip"] = new_host_slave
        params["meta_role"] = InstanceRole.REDIS_SLAVE.value
        params["spec_id"] = master_replace_info["slave_spec"].get("id", 0)
        params["spec_config"] = master_replace_info["slave_spec"]
        sub_pipelines.append(RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, params))
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # ### 部署实例 ####################################################################### 完毕 ###

    sync_relations, new_slave_ports = [], []  # 按照机器对组合
    # #### 建同步关系 #############################################################################
    sub_pipelines, sync_kwargs, sed_links = [], deepcopy(act_kwargs), []
    for replace_info in master_replace_detail:
        old_master = replace_info["ip"]
        new_host_master = replace_info["target"]["master"]["ip"]
        new_host_slave = replace_info["target"]["slave"]["ip"]
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
            sed_links.append({"old": old_master_ins, "new": "{}:{}".format(new_host_master, new_ins_port)})
            sed_links.append({"old": old_slave_ins, "new": "{}:{}".format(new_host_slave, new_ins_port)})
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

    # predixy类型的集群需要刷新配置文件 #################################################################
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
        sed_args = ['''-e "s/{}/{}/"'''.format(sss["old"], sss["new"]) for sss in sed_links]
        sed_seed = " ".join(sed_args)

        # act_kwargs.exec_ip = act_kwargs.cluster["proxy_ips"]  # predixy ips ... 这里需要动态的获取IP 列表额。。s
        act_kwargs.cluster[
            "shell_command"
        ] = """
        cnf="$REDIS_DATA_DIR/predixy/{}/predixy.conf"
        echo "`date "+%F %T"` : before sed config $cnf: : `cat $cnf |grep  "+"|grep ":"`"
        echo "`date "+%F %T"` : exec sed -i {}"
        sed -i {} $cnf
        echo "`date "+%F %T"` : after sed configs : `cat $cnf|grep  "+"|grep ":"`"
        """.format(
            act_kwargs.cluster["proxy_port"], sed_seed, sed_seed
        )

        redis_pipeline.add_act(
            act_name=_("刷新Predixy本地配置"),
            act_component_code=ExecuteShellReloadMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )
    # predixy类型的集群需要刷新配置文件 ######################################################## 完毕 ###

    # #### 下架旧实例 #############################################################################
    sub_pipelines, shutdown_kwargs = [], deepcopy(act_kwargs)
    for replace_info in master_replace_detail:
        old_master = replace_info["ip"]
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

    return redis_pipeline.build_sub_process(sub_name=_("主从替换-{}").format(act_kwargs.cluster["cluster_type"]))


def TendisClusterMasterReplaceJob(
    root_id, ticket_data, sub_kwargs: ActKwargs, master_replace_detail: Dict
) -> SubBuilder:
    """master_replace_detail:[{
      {"ip": "1.1.1.c","spec_id": 17,
        "target": {
            "master": {"bk_cloud_id": 0,"bk_host_id": 195,"status": 1,"ip": "2.2.2.b"},
            "slave": {"bk_cloud_id": 0,"bk_host_id": 187,"status": 1,"ip": "3.3.3.x"}}
    }]
    """
    act_kwargs = deepcopy(sub_kwargs)
    redis_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # #### 替换掉旧Slave #######################################################################
    sub_pipeline = RedisClusterSlaveReplaceJob(
        root_id,
        ticket_data,
        act_kwargs,
        {
            "redis_slave": [
                {
                    "ip": act_kwargs.cluster["master_slave_map"][item["ip"]],
                    "spec_id": item["spec_id"],
                    "target": item.get("target", {}).get("master", {}),
                }
                for item in master_replace_detail["redis_master"]
            ],
            "slave_spec": master_replace_detail.get("master_spec", {}),
        },
    )
    redis_pipeline.add_sub_pipeline(sub_pipeline)
    # #### 替换掉旧Slave #######################################################################

    sync_relations, new_master_ports, new_master_old_master_map = [], {}, {}
    # 执行切换 #####################################################################################
    for replace_info in master_replace_detail["redis_master"]:
        old_master = replace_info["ip"]
        new_host_master = replace_info["target"]["master"]["ip"]
        new_host_slave = replace_info["target"]["slave"]["ip"]
        new_master_ports[new_host_master] = []
        sync_params = {
            "sync_type": SyncType.SYNC_MS.value,
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
            new_master_ports[new_host_master].append(int(new_ins_port))
            new_master_old_master_map["{}{}{}".format(old_master, IP_PORT_DIVIDER, old_master_port)] = "{}{}{}".format(
                new_host_master, IP_PORT_DIVIDER, new_ins_port
            )
            sync_params["ins_link"].append(
                {
                    "origin_1": int(old_master_port),
                    "sync_dst1": int(new_ins_port),
                    "sync_dst2": int(new_ins_port),
                }
            )
            new_ins_port = new_ins_port + 1
        sync_relations.append(sync_params)
    act_kwargs.cluster["switch_condition"] = {
        "is_check_sync": True,  # 不强制切换
        "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
        "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
        "can_write_before_switch": True,
        "sync_type": SyncType.SYNC_MS.value,
    }
    redis_pipeline.add_sub_pipeline(
        sub_flow=RedisClusterSwitchAtomJob(root_id, ticket_data, act_kwargs, sync_relations)
    )
    # #### 执行切换 ###############################################################################

    # #### 元数据角色互换 #######################################################################
    act_kwargs.cluster["role_swap_ins"] = []
    for swap_info in sync_relations:
        act_kwargs.cluster["role_swap_ins"].extend(
            [
                {
                    "new_ejector_ip": swap_info["sync_dst1"],
                    "new_ejector_port": port_link["sync_dst1"],
                    "new_receiver_ip": swap_info["origin_1"],
                    "new_receiver_port": port_link["origin_1"],
                }
                for port_link in swap_info["ins_link"]
            ]
        )
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_role_swap_4_scene.__name__
    redis_pipeline.add_act(
        act_name=_("元数据角色互换-{}").format(old_master),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(act_kwargs),
    )
    # #### 元数据角色互换 ###############################################################################

    # #### 重新加载集群元数据 #######################################################################
    logger.info(
        "before switch | slave ports : {}, slave's master : {}, slave's master addr : {} ".format(
            act_kwargs.cluster["slave_ports"],
            act_kwargs.cluster["slave_master_map"],
            act_kwargs.cluster["slave_ins_map"],
        )
    )
    for replace_info in master_replace_detail["redis_master"]:
        old_master = replace_info["ip"]
        new_host_master = replace_info["target"]["master"]["ip"]
        act_kwargs.cluster["slave_ports"][old_master] = act_kwargs.cluster["master_ports"][old_master]
        act_kwargs.cluster["slave_master_map"][old_master] = new_host_master
    # add new-master --> old-master
    act_kwargs.cluster["slave_ins_map"].update(new_master_old_master_map)
    logger.info(
        "after switch | slave ports : {}, slave's master : {}, slave's master addr : {} ".format(
            act_kwargs.cluster["slave_ports"],
            act_kwargs.cluster["slave_master_map"],
            act_kwargs.cluster["slave_ins_map"],
        )
    )
    # #### 重新加载集群元数据 ###########################################################################

    # #### 替换掉旧Master #######################################################################
    sub_pipeline = RedisClusterSlaveReplaceJob(
        root_id,
        ticket_data,
        act_kwargs,
        {
            "redis_slave": [
                {"ip": item["ip"], "spec_id": item["spec_id"], "target": item.get("target", {}).get("slave", {})}
                for item in master_replace_detail["redis_master"]
            ],
            "slave_spec": master_replace_detail.get("slave_spec", {}),
        },
    )
    redis_pipeline.add_sub_pipeline(sub_pipeline)
    # #### 替换掉旧Master #######################################################################

    return redis_pipeline.build_sub_process(sub_name=_("主从替换-{}").format(act_kwargs.cluster["cluster_type"]))
