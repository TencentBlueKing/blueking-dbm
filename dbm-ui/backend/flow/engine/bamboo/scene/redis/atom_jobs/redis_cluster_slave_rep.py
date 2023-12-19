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

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.consts import DEFAULT_REDIS_START_PORT, SyncType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellReloadMetaComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode, get_twemproxy_cluster_server_shards

from .redis_install import RedisBatchInstallAtomJob
from .redis_makesync import RedisMakeSyncAtomJob
from .redis_shutdown import RedisBatchShutdownAtomJob

logger = logging.getLogger("flow")


class StorageRepLink:
    old_master_ip: str = ""
    old_master_port: int = 0
    old_slave_ip: str = ""
    old_slave_port: int = 0
    new_master_ip: str = ""
    new_master_port: int = 0
    new_slave_ip: str = ""
    new_slave_port: int = 0


def RedisClusterSlaveReplaceJob(root_id, ticket_data, sub_kwargs: ActKwargs, slave_replace_info: Dict) -> SubBuilder:
    """适用于 集群中Slave 机房裁撤/迁移替换场景
    步骤：   获取变更锁--> 新实例部署-->
            重建热备--> 检测同步状态-->
            Kill Dead链接--> 下架旧实例
    """
    act_kwargs = deepcopy(sub_kwargs)
    redis_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    sub_pipelines, newslave_to_master, replace_link_info = [], {}, {}
    slave_replace_detail = slave_replace_info["redis_slave"]

    for replace_link in slave_replace_detail:
        old_slave, new_slave = replace_link["ip"], replace_link["target"]["ip"]
        new_ins_port = DEFAULT_REDIS_START_PORT
        old_ports = act_kwargs.cluster["slave_ports"][old_slave]
        old_ports.sort()  # 升序
        for port in old_ports:
            one_link = StorageRepLink()
            one_link.old_slave_port, one_link.old_slave_ip = int(port), old_slave
            one_link.new_slave_port, one_link.new_slave_ip = new_ins_port, new_slave

            old_slave_addr = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, port)
            new_slave_addr = "{}{}{}".format(new_slave, IP_PORT_DIVIDER, new_ins_port)
            old_master_addr = act_kwargs.cluster["slave_ins_map"].get(
                old_slave_addr, "none.old.ip.{}:0".format(old_slave_addr)
            )

            one_link.old_master_ip = old_master_addr.split(IP_PORT_DIVIDER)[0]
            one_link.old_master_port = int(old_master_addr.split(IP_PORT_DIVIDER)[1])

            newslave_to_master[new_slave_addr] = old_master_addr
            replace_link_info[old_slave_addr] = one_link
            new_ins_port += 1

    twemproxy_server_shards = get_twemproxy_cluster_server_shards(
        act_kwargs.cluster["bk_biz_id"], act_kwargs.cluster["cluster_id"], newslave_to_master
    )

    # ### 部署实例 ###############################################################################
    for replace_link in slave_replace_detail:
        # {"ip": "1.1.1.a","spec_id": 17,"target": {"bk_cloud_id": 0,"bk_host_id": 216,"status": 1,"ip": "2.2.2.b"}}
        old_slave = replace_link["ip"]
        new_slave = replace_link["target"]["ip"]
        params = {
            "ip": new_slave,
            "meta_role": InstanceRole.REDIS_SLAVE.value,
            "start_port": DEFAULT_REDIS_START_PORT,
            "ports": act_kwargs.cluster["slave_ports"][old_slave],
            "instance_numb": len(act_kwargs.cluster["slave_ports"][old_slave]),
            "spec_id": slave_replace_info["slave_spec"].get("id", 0),
            "spec_config": slave_replace_info["slave_spec"],
            "server_shards": twemproxy_server_shards.get(new_slave, {}),
            "cache_backup_mode": get_cache_backup_mode(
                act_kwargs.cluster["bk_biz_id"], act_kwargs.cluster["cluster_id"]
            ),
        }
        sub_builder = RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, params)
        sub_pipelines.append(sub_builder)
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # ### 部署实例 ######################################################################## 完毕 ###

    # #### 建同步关系 ##############################################################################
    sub_pipelines = []
    for replace_link in slave_replace_detail:
        # "Old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
        old_slave = replace_link["ip"]
        new_slave = replace_link["target"]["ip"]
        install_params = {
            "sync_type": SyncType.SYNC_MS,
            "origin_1": act_kwargs.cluster["slave_master_map"][old_slave],
            "origin_2": old_slave,
            "sync_dst1": new_slave,
            "ins_link": [],
            "server_shards": twemproxy_server_shards.get(new_slave, {}),
            "cache_backup_mode": get_cache_backup_mode(
                act_kwargs.cluster["bk_biz_id"], act_kwargs.cluster["cluster_id"]
            ),
        }
        for slave_port in act_kwargs.cluster["slave_ports"][old_slave]:
            old_ins = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, slave_port)
            # master_port = act_kwargs.cluster["slave_ins_map"].get(old_ins).split(IP_PORT_DIVIDER)[1]
            rep_link = replace_link_info.get(old_ins, StorageRepLink())
            install_params["ins_link"].append(
                {
                    "origin_1": rep_link.old_master_port,
                    "origin_2": rep_link.old_slave_port,
                    "sync_dst1": rep_link.new_slave_port,
                }
            )
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
        old_slave = replace_link["ip"]
        act_kwargs.cluster["old_slaves"].append(
            {"ip": old_slave, "ports": act_kwargs.cluster["slave_ports"][old_slave]}
        )
        for slave_port in act_kwargs.cluster["slave_ports"][old_slave]:
            old_ins = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, slave_port)
            rep_link = replace_link_info.get(old_ins, StorageRepLink())
            act_kwargs.cluster["tendiss"].append(
                {
                    "ejector": {
                        "ip": rep_link.old_master_ip,
                        "port": rep_link.old_master_port,
                    },
                    "receiver": {"ip": rep_link.new_slave_ip, "port": int(rep_link.new_slave_port)},
                }
            )

    redis_pipeline.add_act(
        act_name=_("Redis-新节点加入集群"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
    )
    # #### 新节点加入集群 ################################################################# 完毕 ###

    # predixy类型的集群需要刷新配置文件 #################################################################
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
        sed_args = []
        for replace_link in slave_replace_detail:
            old_slave, new_slave = replace_link["ip"], replace_link["target"]["ip"]
            for slave_port in act_kwargs.cluster["slave_ports"][old_slave]:
                sed_args.append(
                    _('''-e "s/{}{}{}/{}{}{}/"''').format(
                        old_slave, IP_PORT_DIVIDER, slave_port, new_slave, IP_PORT_DIVIDER, slave_port
                    )
                )
            sed_seed = " ".join(sed_args)

        # act_kwargs.exec_ip = act_kwargs.cluster["proxy_ips"]  # predixy ips ...
        act_kwargs.cluster[
            "shell_command"
        ] = """
        cnf="$REDIS_DATA_DIR/predixy/{}/predixy.conf"
        echo "`date "+%F %T"` : before sed config $cnf: : `cat $cnf |grep  "+"|grep ":"`"
        echo "`date "+%F %T"` : exec sed -i {}"
        sed -i {} $cnf
        echo "`date "+%F %T"` : after sed configs : `cat $cnf |grep "+"|grep ":"`"
        """.format(
            act_kwargs.cluster["proxy_port"], sed_seed, sed_seed
        )

        redis_pipeline.add_act(
            act_name=_("刷新Predixy本地配置"),
            act_component_code=ExecuteShellReloadMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )
    # predixy类型的集群需要刷新配置文件 ######################################################## 完毕 ###

    # #### 下架旧实例 ############################################################################
    sub_pipelines = []
    for replace_link in slave_replace_detail:
        # "Old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
        old_slave = replace_link["ip"]
        params = {
            "ignore_ips": [act_kwargs.cluster["slave_master_map"][old_slave]],
            "ip": old_slave,
            "ports": act_kwargs.cluster["slave_ports"][old_slave],
        }
        sub_builder = RedisBatchShutdownAtomJob(root_id, ticket_data, act_kwargs, params)
        sub_pipelines.append(sub_builder)
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # #### 下架旧实例 ###################################################################### 完毕 ###

    return redis_pipeline.build_sub_process(sub_name=_("Slave替换-{}").format(act_kwargs.cluster["cluster_type"]))
