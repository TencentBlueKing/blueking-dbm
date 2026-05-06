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

from django.utils.translation import gettext as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.api.cluster.nosqlcomm.other import get_cluster_ins_dns
from backend.db_meta.enums import ClusterEntryRole, ClusterType, InstanceRole
from backend.db_services.redis.util import is_predixy_proxy_type, is_redis_cluster_protocal
from backend.flow.consts import DEFAULT_REDIS_START_PORT, DnsOpType, SyncType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellReloadMetaComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode, get_twemproxy_cluster_server_shards

from .access_manager import AccessManagerAtomJob
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


def _setup_alarm_shield(redis_pipeline, act_kwargs, replace_ips):
    """设置告警屏蔽"""
    import datetime

    now = datetime.datetime.now()
    default_duration = 3 * 3600  # 默认屏蔽3小时
    end_time_default = now + datetime.timedelta(seconds=default_duration)
    end_time_20 = now.replace(hour=20, minute=0, second=0, microsecond=0)

    if end_time_default <= end_time_20:
        duration_seconds = default_duration
    else:
        duration_seconds = int((end_time_20 - now).total_seconds())
        if duration_seconds < 0:
            duration_seconds = 0

    redis_pipeline.add_act(
        act_name=_("屏蔽集群告警-{}").format(act_kwargs.cluster["immute_domain"]),
        act_component_code=AddAlarmShieldComponent.code,
        kwargs={
            **asdict(act_kwargs),
            "description": _("Redis Slave替换-屏蔽告警-{}").format(act_kwargs.cluster["immute_domain"]),
            "dimensions": [
                {"name": "appid", "values": [act_kwargs.cluster["bk_biz_id"]]},
                {"name": "cluster_domain", "values": [act_kwargs.cluster["immute_domain"]]},
                {"name": "bk_target_ip", "values": list(replace_ips)},
            ],
            "duration_seconds": duration_seconds,
        },
    )


def _collect_replace_info(slave_replace_detail, act_kwargs):
    """收集替换信息"""
    newslave_to_master, replace_link_info, old_slaves, new_slaves = {}, {}, [], []
    replace_ips = set()

    for replace_link in slave_replace_detail:
        old_slave, new_slave = replace_link["ip"], replace_link["target"]["ip"]
        replace_ips.add(old_slave)
        replace_ips.add(new_slave)
        master_ip = act_kwargs.cluster["slave_master_map"].get(old_slave)
        if master_ip:
            replace_ips.add(master_ip)

        old_slaves.append(old_slave)
        new_slaves.append(new_slave)
        new_ins_port = DEFAULT_REDIS_START_PORT
        if act_kwargs.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value:
            new_ins_port = min(act_kwargs.cluster["slave_ports"][old_slave])

        old_ports = act_kwargs.cluster["slave_ports"][old_slave]
        old_ports.sort()
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

    return newslave_to_master, replace_link_info, old_slaves, new_slaves, replace_ips


def _deploy_new_instances(
    root_id, ticket_data, act_kwargs, slave_replace_detail, slave_replace_info, twemproxy_server_shards
):
    """部署新实例"""
    sub_pipelines = []
    for replace_link in slave_replace_detail:
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
        if act_kwargs.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value:
            params["start_port"] = min(act_kwargs.cluster["slave_ports"][old_slave])
        sub_builder = RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, params)
        sub_pipelines.append(sub_builder)
    return sub_pipelines


def _setup_sync_relations(
    root_id, ticket_data, act_kwargs, slave_replace_detail, replace_link_info, twemproxy_server_shards
):
    """建立同步关系"""
    sub_pipelines = []
    for replace_link in slave_replace_detail:
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
    return sub_pipelines


def _add_new_nodes_to_cluster(act_kwargs, ticket_data, slave_replace_detail, replace_link_info):
    """新节点加入集群"""
    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_redo_slaves.__name__
    act_kwargs.cluster["old_slaves"] = []
    act_kwargs.cluster["created_by"] = ticket_data["created_by"]
    act_kwargs.cluster["tendiss"] = []

    for replace_link in slave_replace_detail:
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


def _refresh_monitoring_and_dns(redis_pipeline, act_kwargs, slave_replace_detail):
    """刷新监控和DNS"""
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value:
        for replace_link in slave_replace_detail:
            old_slave, new_slave = replace_link["ip"], replace_link["target"]["ip"]
            for slave_port in act_kwargs.cluster["slave_ports"][old_slave]:
                domain = get_cluster_ins_dns(act_kwargs.cluster["cluster_id"], replace_link["ip"], int(slave_port))
                if domain != "":
                    redis_pipeline.add_act(
                        act_name=_("刷新域名-{}").format(domain),
                        act_component_code=RedisDnsManageComponent.code,
                        kwargs={
                            "bk_biz_id": act_kwargs.cluster["bk_biz_id"],
                            "bk_cloud_id": act_kwargs.cluster["bk_cloud_id"],
                            "dns_op_type": DnsOpType.UPDATE,
                            "old_instance": "{}#{}".format(old_slave, slave_port),
                            "new_instance": "{}#{}".format(new_slave, slave_port),
                            "update_domain_name": domain,
                        },
                    )

            act_kwargs.exec_ip = new_slave
            act_kwargs.cluster["ip"] = new_slave
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
            redis_pipeline.add_act(
                act_name=_("{}-刷新监控").format(new_slave),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )


def _handle_redis_cluster_specifics(redis_pipeline, root_id, ticket_data, act_kwargs, old_slaves, new_slaves):
    """处理Redis Cluster特定逻辑"""
    if is_redis_cluster_protocal(act_kwargs.cluster["cluster_type"]):
        act_kwargs.cluster["nodes_domain"] = "nodes." + act_kwargs.cluster["immute_domain"]
        act_kwargs.cluster["meta_func_name"] = RedisDBMeta.update_cluster_entry.__name__
        redis_pipeline.add_act(
            act_name=_("Redis-更新sbind_entry元数据"),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )

        access_sub_builder = AccessManagerAtomJob(
            root_id,
            ticket_data,
            act_kwargs,
            {
                "cluster_id": act_kwargs.cluster["cluster_id"],
                "port": DEFAULT_REDIS_START_PORT,
                "add_ips": new_slaves,
                "op_type": DnsOpType.CREATE,
                "role": [ClusterEntryRole.NODE_ENTRY.value],
            },
        )
        if access_sub_builder:
            redis_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)
        else:
            act_kwargs.exec_ip = new_slaves
            redis_pipeline.add_act(
                act_name=_("Redis-初始化nodes域名"),
                act_component_code=RedisDnsManageComponent.code,
                kwargs={
                    **asdict(act_kwargs),
                    **asdict(
                        DnsKwargs(
                            dns_op_type=DnsOpType.CREATE,
                            add_domain_name="nodes." + act_kwargs.cluster["immute_domain"],
                            dns_op_exec_port=DEFAULT_REDIS_START_PORT,
                        )
                    ),
                },
            )

        access_sub_builder = AccessManagerAtomJob(
            root_id,
            ticket_data,
            act_kwargs,
            {
                "cluster_id": act_kwargs.cluster["cluster_id"],
                "port": DEFAULT_REDIS_START_PORT,
                "del_ips": old_slaves,
                "op_type": DnsOpType.RECYCLE_RECORD,
                "role": [ClusterEntryRole.NODE_ENTRY.value],
            },
        )
        if access_sub_builder:
            redis_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)


def _handle_predixy_specifics(redis_pipeline, act_kwargs, slave_replace_detail):
    """处理Predixy特定逻辑"""
    if is_predixy_proxy_type(act_kwargs.cluster["cluster_type"]):
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

        act_kwargs.cluster[
            "shell_command"
        ] = """
        cnf="$REDIS_DATA_DIR/predixy/{}/predixy.conf"
        echo "`date \"+%F %T\"` : before sed config $cnf: : `cat $cnf |grep  \"+\"|grep \":\"`"
        echo "`date \"+%F %T\"` : exec sed -i {}"
        sed -i {} $cnf
        echo "`date \"+%F %T\"` : after sed configs : `cat $cnf |grep \"+\"|grep \":\"`"
        """.format(
            act_kwargs.cluster["proxy_port"], sed_seed, sed_seed
        )

        redis_pipeline.add_act(
            act_name=_("刷新Predixy本地配置"),
            act_component_code=ExecuteShellReloadMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )


def _shutdown_old_instances(root_id, ticket_data, act_kwargs, slave_replace_detail):
    """下架旧实例"""
    sub_pipelines = []
    for replace_link in slave_replace_detail:
        old_slave = replace_link["ip"]
        params = {
            "ignore_ips": [act_kwargs.cluster["slave_master_map"][old_slave]],
            "ip": old_slave,
            "ports": act_kwargs.cluster["slave_ports"][old_slave],
        }
        sub_builder = RedisBatchShutdownAtomJob(root_id, ticket_data, act_kwargs, params)
        sub_pipelines.append(sub_builder)
    return sub_pipelines


def _disable_alarm_shield(redis_pipeline, act_kwargs):
    """解除告警屏蔽"""
    redis_pipeline.add_act(
        act_name=_("解除集群告警屏蔽-{}").format(act_kwargs.cluster["immute_domain"]),
        act_component_code=DisableAlarmShieldComponent.code,
        kwargs=asdict(act_kwargs),
    )


def RedisClusterSlaveReplaceJob(root_id, ticket_data, sub_kwargs: ActKwargs, slave_replace_info: Dict) -> SubBuilder:
    """适用于 集群中Slave 机房裁撤/迁移替换场景
    步骤：   获取变更锁--> 新实例部署-->
            重建热备--> 检测同步状态-->
            Kill Dead链接--> 下架旧实例
    """
    act_kwargs = deepcopy(sub_kwargs)
    redis_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    slave_replace_detail = slave_replace_info["redis_slave"]

    # 收集替换信息
    newslave_to_master, replace_link_info, old_slaves, new_slaves, replace_ips = _collect_replace_info(
        slave_replace_detail, act_kwargs
    )

    # 设置告警屏蔽
    _setup_alarm_shield(redis_pipeline, act_kwargs, replace_ips)

    # 获取twemproxy服务器分片信息
    twemproxy_server_shards = get_twemproxy_cluster_server_shards(
        act_kwargs.cluster["bk_biz_id"], act_kwargs.cluster["cluster_id"], newslave_to_master
    )

    # 部署新实例
    deploy_sub_pipelines = _deploy_new_instances(
        root_id, ticket_data, act_kwargs, slave_replace_detail, slave_replace_info, twemproxy_server_shards
    )
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=deploy_sub_pipelines)

    # 建立同步关系
    sync_sub_pipelines = _setup_sync_relations(
        root_id, ticket_data, act_kwargs, slave_replace_detail, replace_link_info, twemproxy_server_shards
    )
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_sub_pipelines)

    # 新节点加入集群
    _add_new_nodes_to_cluster(act_kwargs, ticket_data, slave_replace_detail, replace_link_info)
    redis_pipeline.add_act(
        act_name=_("Redis-新节点加入集群"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
    )

    # 刷新监控和DNS
    _refresh_monitoring_and_dns(redis_pipeline, act_kwargs, slave_replace_detail)

    # 处理Redis Cluster特定逻辑
    _handle_redis_cluster_specifics(redis_pipeline, root_id, ticket_data, act_kwargs, old_slaves, new_slaves)

    # 处理Predixy特定逻辑
    _handle_predixy_specifics(redis_pipeline, act_kwargs, slave_replace_detail)

    # 下架旧实例
    shutdown_sub_pipelines = _shutdown_old_instances(root_id, ticket_data, act_kwargs, slave_replace_detail)
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=shutdown_sub_pipelines)

    # 解除告警屏蔽
    _disable_alarm_shield(redis_pipeline, act_kwargs)

    return redis_pipeline.build_sub_process(sub_name=_("Slave替换-{}").format(act_kwargs.cluster["cluster_type"]))
