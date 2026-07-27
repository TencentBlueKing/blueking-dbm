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
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_services.redis.util import is_redis_cluster_protocal
from backend.flow.consts import (
    DEFAULT_LAST_IO_SECOND_AGO,
    DEFAULT_MASTER_DIFF_TIME,
    DEFAULT_REDIS_START_PORT,
    SyncType,
)
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_update_version import RedisUpdateVersionComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode, get_twemproxy_cluster_server_shards

from .redis_cluster_slave_rep import RedisClusterSlaveReplaceJob, StorageRepLink
from .redis_install import RedisBatchInstallAtomJob
from .redis_makesync import RedisMakeSyncAtomJob
from .redis_shutdown import RedisBatchShutdownAtomJob
from .redis_switch import RedisClusterSwitchAtomJob

logger = logging.getLogger("flow")


def _cluster_label(act_kwargs):
    """生成单集群/多集群场景下的展示标签。"""
    cluster_ids = act_kwargs.cluster.get("cluster_ids")
    if cluster_ids and len(cluster_ids) > 1:
        return ",".join(str(cluster_id) for cluster_id in cluster_ids)
    return act_kwargs.cluster.get("immute_domain") or act_kwargs.cluster.get("cluster_id", "")


def _first_cluster_id(act_kwargs):
    """获取单集群/多集群场景下的首个集群ID。"""
    cluster_ids = act_kwargs.cluster.get("cluster_ids")
    if cluster_ids:
        return cluster_ids[0]
    return act_kwargs.cluster["cluster_id"]


def _master_relation_cluster(act_kwargs, old_master_ins):
    """获取 master 实例所属集群，兼容未构造 master_cid_relation 的单集群路径。"""
    master_cid_relation = act_kwargs.cluster.get("master_cid_relation", {})
    if isinstance(master_cid_relation, dict) and old_master_ins in master_cid_relation:
        return master_cid_relation[old_master_ins]
    return {"id": act_kwargs.cluster["cluster_id"], "immute_domain": act_kwargs.cluster["immute_domain"]}


def _extract_master_replace_params(master_replace_info, act_kwargs):
    master_replace_detail = master_replace_info["redis_master"]
    new_instances_to_master, replace_link_info = {}, {}

    for replace_link in master_replace_detail:
        old_master_ip = replace_link["ip"]
        old_slave_ip = act_kwargs.cluster["master_slave_map"][old_master_ip]
        new_master_ip, new_slave_ip = replace_link["target"]["master"]["ip"], replace_link["target"]["slave"]["ip"]

        new_ins_port = DEFAULT_REDIS_START_PORT
        old_ports = act_kwargs.cluster["master_ports"][old_master_ip]
        if act_kwargs.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value:
            new_ins_port = min(old_ports)
        old_ports.sort()
        for port in old_ports:  # 升序
            if act_kwargs.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value:
                new_ins_port = int(port)

            one_link = StorageRepLink()
            one_link.old_master_port, one_link.old_master_ip = int(port), old_master_ip
            one_link.old_slave_ip = old_slave_ip
            one_link.new_master_port, one_link.new_master_ip = new_ins_port, new_master_ip
            one_link.new_slave_port, one_link.new_slave_ip = new_ins_port, new_slave_ip

            old_master_addr = "{}{}{}".format(old_master_ip, IP_PORT_DIVIDER, port)
            old_slave_addr = act_kwargs.cluster["ins_pair_map"].get(
                old_master_addr, "none.old.ip.{}:0".format(old_master_addr)
            )
            one_link.old_slave_port = int(old_slave_addr.split(IP_PORT_DIVIDER)[1])

            new_slave_addr = "{}{}{}".format(new_slave_ip, IP_PORT_DIVIDER, new_ins_port)
            new_master_addr = "{}{}{}".format(new_master_ip, IP_PORT_DIVIDER, new_ins_port)
            new_instances_to_master[new_slave_addr] = old_master_addr
            new_instances_to_master[new_master_addr] = old_master_addr
            replace_link_info[old_master_addr] = one_link
            new_ins_port += 1
    return master_replace_detail, new_instances_to_master, replace_link_info


def _setup_alarm_shield(redis_pipeline, act_kwargs, replace_ips):
    """设置告警屏蔽

    Args:
        redis_pipeline (Pipeline): 流程编排流水线对象
        act_kwargs (ActKwargs): 活动参数对象，需包含 cluster 属性，cluster 中应包含以下字段：
            - bk_biz_id (int): 业务ID
            - immute_domain (str, optional): 集群域名，未传入时不添加 cluster_domain 维度
        replace_ips (set[str]): 需要屏蔽告警的IP地址集合
    """
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

    # 兼容未传入 immute_domain 的场景；多集群主从版不按单一域名维度屏蔽
    immute_domain = act_kwargs.cluster.get("immute_domain")
    cluster_ids = act_kwargs.cluster.get("cluster_ids")
    shield_label = _cluster_label(act_kwargs)
    dimensions = [
        {"name": "appid", "values": [act_kwargs.cluster["bk_biz_id"]]},
        {"name": "bk_target_ip", "values": list(replace_ips)},
    ]
    if immute_domain and not (cluster_ids and len(cluster_ids) > 1):
        dimensions.insert(1, {"name": "cluster_domain", "values": [immute_domain]})
    redis_pipeline.add_act(
        act_name=_("屏蔽集群告警-{}").format(shield_label or replace_ips),
        act_component_code=AddAlarmShieldComponent.code,
        kwargs={
            **asdict(act_kwargs),
            "description": _("Redis Master替换-屏蔽告警-{}").format(shield_label or ""),
            "dimensions": dimensions,
            "duration_seconds": duration_seconds,
        },
    )


# /********************************************************/
# /********************************************************/
# /********************************************************/


def RedisClusterMasterReplaceJob(root_id, ticket_data, sub_kwargs: ActKwargs, master_replace_info: Dict) -> SubBuilder:
    if sub_kwargs.cluster["cluster_type"] in [
        ClusterType.TwemproxyTendisSSDInstance,
        ClusterType.TendisTwemproxyRedisInstance,
        # tendisplus 主从版(predixy)，替换流程与twemproxy-cache/ssd一致
        ClusterType.TendisPredixyTendisplusInstance,
    ]:
        return TwemproxyClusterMasterReplaceJob(root_id, ticket_data, sub_kwargs, master_replace_info)

    elif is_redis_cluster_protocal(sub_kwargs.cluster["cluster_type"]):
        return TendisClusterMasterReplaceJob(root_id, ticket_data, sub_kwargs, master_replace_info)

    elif sub_kwargs.cluster["cluster_type"] in [ClusterType.TendisRedisInstance.value]:
        return TendisSingleMasterReplaceJob(root_id, ticket_data, sub_kwargs, master_replace_info)

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
    master_replace_detail, new_instances_to_master, replace_link_info = _extract_master_replace_params(
        master_replace_info, act_kwargs
    )

    twemproxy_server_shards = get_twemproxy_cluster_server_shards(
        act_kwargs.cluster["bk_biz_id"], act_kwargs.cluster["cluster_id"], new_instances_to_master
    )
    cache_backup_mode = get_cache_backup_mode(act_kwargs.cluster["bk_biz_id"], act_kwargs.cluster["cluster_id"])

    # ## 部署实例 #############################################################################
    sub_pipelines = []
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
            "server_shards": twemproxy_server_shards.get(new_host_master, {}),
            "cache_backup_mode": cache_backup_mode,
        }
        if act_kwargs.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value:
            params["start_port"] = min(act_kwargs.cluster["master_ports"][old_master])
        sub_pipelines.append(RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, params))

        # 安装slave
        slave_params = deepcopy(params)
        slave_params["ip"] = new_host_slave
        slave_params["meta_role"] = InstanceRole.REDIS_SLAVE.value
        slave_params["spec_id"] = master_replace_info["slave_spec"].get("id", 0)
        slave_params["spec_config"] = master_replace_info["slave_spec"]
        slave_params["server_shards"] = twemproxy_server_shards.get(new_host_slave, {})
        sub_pipelines.append(RedisBatchInstallAtomJob(root_id, ticket_data, act_kwargs, slave_params))
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # ### 部署实例 ####################################################################### 完毕 ###

    # 在流程开始时添加告警屏蔽
    replace_ips = set()
    for replace_info in master_replace_detail:
        old_master = replace_info["ip"]
        old_slave = act_kwargs.cluster["master_slave_map"][old_master]
        new_master = replace_info["target"]["master"]["ip"]
        new_slave = replace_info["target"]["slave"]["ip"]

        replace_ips.add(old_master)
        replace_ips.add(old_slave)
        replace_ips.add(new_master)
        replace_ips.add(new_slave)

    # 在流程开始时添加告警屏蔽
    # 动态计算屏蔽时长，默认屏蔽3小时但不能超过20点
    _setup_alarm_shield(redis_pipeline, act_kwargs, replace_ips)

    sync_relations = []  # 按照机器对组合
    # #### 建同步关系 #############################################################################
    sub_pipelines, sync_kwargs = [], deepcopy(act_kwargs)
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

        for old_master_port in act_kwargs.cluster["master_ports"][old_master]:
            old_master_ins = "{}{}{}".format(old_master, IP_PORT_DIVIDER, old_master_port)
            rep_link = replace_link_info.get(old_master_ins, StorageRepLink())
            sync_params["ins_link"].append(
                {
                    "origin_1": rep_link.old_master_port,
                    "origin_2": rep_link.old_slave_port,
                    "sync_dst1": rep_link.new_master_port,
                    "sync_dst2": rep_link.new_slave_port,
                    "server_shards": twemproxy_server_shards.get(rep_link.new_master_ip, {}),
                    "cache_backup_mode": cache_backup_mode,
                }
            )
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

    # 这里高版本的Redis Slave 还需要重新同步一下数据
    if act_kwargs.cluster["cluster_type"] in [
        ClusterType.TendisTwemproxyRedisInstance.value,
    ]:
        sub_pipelines, resync_args = [], deepcopy(act_kwargs)
        resync_args.cluster = {
            "bk_biz_id": int(act_kwargs.cluster["bk_biz_id"]),
            "cluster_id": int(act_kwargs.cluster["cluster_id"]),
            "cluster_type": act_kwargs.cluster["cluster_type"],
            "immute_domain": act_kwargs.cluster["immute_domain"],
            "bk_cloud_id": int(act_kwargs.cluster["bk_cloud_id"]),
            "instances": [],
        }
        for sync_link in sync_relations:
            one_resync_args = deepcopy(resync_args)
            new_master, new_slave = sync_link["sync_dst1"], sync_link["sync_dst2"]
            for instances in sync_link["ins_link"]:
                master_port, slave_port = instances["sync_dst1"], instances["sync_dst2"]
                one_resync_args.cluster["instances"].append(
                    {
                        "master_ip": new_master,
                        "master_port": int(master_port),
                        "slave_ip": new_slave,
                        "slave_port": int(slave_port),
                    }
                )
            one_resync_args.exec_ip = new_slave
            one_resync_args.get_redis_payload_func = RedisActPayload.redis_local_redo_dr.__name__
            sub_pipelines.append(
                {
                    "act_name": _("{}-本地重建Slave").format(new_slave),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(one_resync_args),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=sub_pipelines)

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

    # 在流程结束时解除告警屏蔽
    redis_pipeline.add_act(
        act_name=_("解除集群告警屏蔽-{}").format(act_kwargs.cluster["immute_domain"]),
        act_component_code=DisableAlarmShieldComponent.code,
        kwargs=asdict(act_kwargs),
    )

    return redis_pipeline.build_sub_process(sub_name=_("主从替换-{}").format(act_kwargs.cluster["cluster_type"]))


# /********************************************************/
# /********************************************************/
# /********************************************************/


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


# /********************************************************/
# /********************************************************/
# /********************************************************/


def TendisSingleMasterReplaceJob(root_id, ticket_data, sub_kwargs: ActKwargs, master_repl_info: Dict) -> SubBuilder:
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
    master_repl_detail, _, repl_link_info = _extract_master_replace_params(master_repl_info, act_kwargs)
    cache_backup_mode = get_cache_backup_mode(act_kwargs.cluster["bk_biz_id"], _first_cluster_id(act_kwargs))

    # ## 部署实例 #############################################################################
    old_master = master_repl_detail[0]["ip"]
    old_slave = act_kwargs.cluster["master_slave_map"][old_master]
    new_master, new_slave = (
        master_repl_detail[0]["target"]["master"]["ip"],
        master_repl_detail[0]["target"]["slave"]["ip"],
    )
    sub_pipelines = []
    sub_pipelines.append(
        RedisBatchInstallAtomJob(
            root_id,
            ticket_data,
            act_kwargs,
            params={
                "ip": new_master,
                "meta_role": InstanceRole.REDIS_MASTER.value,
                "start_port": DEFAULT_REDIS_START_PORT,
                "ports": act_kwargs.cluster["master_ports"][old_master],
                "instance_numb": 0,  # 这里主从的可能会不连续
                "spec_id": master_repl_info["master_spec"].get("id", 0),
                "spec_config": master_repl_info["master_spec"],
                "server_shards": {},  # 主从版本 没有这个信息
                "cache_backup_mode": cache_backup_mode,
            },
        )
    )

    sub_pipelines.append(
        RedisBatchInstallAtomJob(
            root_id,
            ticket_data,
            act_kwargs,
            params={
                "ip": new_slave,
                "meta_role": InstanceRole.REDIS_SLAVE.value,
                "start_port": DEFAULT_REDIS_START_PORT,
                "ports": act_kwargs.cluster["master_ports"][old_master],
                "instance_numb": 0,  # 这里主从的可能会不连续
                "spec_id": master_repl_info["slave_spec"].get("id", 0),
                "spec_config": master_repl_info["slave_spec"],
                "server_shards": {},  # 主从版本 没有这个信息
                "cache_backup_mode": cache_backup_mode,
            },
        )
    )
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # ### 部署实例 ####################################################################### 完毕 ###

    # 在流程开始时添加告警屏蔽
    replace_ips = set([old_master, old_slave, new_master, new_slave])
    # 动态计算屏蔽时长，默认屏蔽3小时但不能超过20点
    _setup_alarm_shield(redis_pipeline, act_kwargs, replace_ips)

    sync_relations = []  # 给切换流程使用，单机多实例按一个集群（实例）一个元素拆分
    # #### 建同步关系 #############################################################################
    sync_kwargs = deepcopy(act_kwargs)
    sync_params = {
        "sync_type": act_kwargs.cluster["sync_type"],
        "origin_1": old_master,
        "origin_2": act_kwargs.cluster["master_slave_map"][old_master],
        "sync_dst1": new_master,
        "sync_dst2": new_slave,
        "ins_link": [],
    }

    for old_master_port in act_kwargs.cluster["master_ports"][old_master]:
        old_master_ins = "{}{}{}".format(old_master, IP_PORT_DIVIDER, old_master_port)
        rep_link = repl_link_info.get(old_master_ins, StorageRepLink())
        ins_link = {
            "origin_1": rep_link.old_master_port,
            "origin_2": rep_link.old_slave_port,
            "sync_dst1": rep_link.new_master_port,
            "sync_dst2": rep_link.new_slave_port,
            "server_shards": {},
            "cache_backup_mode": cache_backup_mode,
        }
        sync_params["ins_link"].append(ins_link)

        cluster_info = _master_relation_cluster(act_kwargs, old_master_ins)
        sync_relations.append(
            {
                "cluster_id": cluster_info["id"],
                "immute_domain": cluster_info["immute_domain"],
                "origin_1": old_master,
                "origin_2": act_kwargs.cluster["master_slave_map"][old_master],
                "sync_dst1": new_master,
                "sync_dst2": new_slave,
                "ins_link": [deepcopy(ins_link)],
            }
        )
    sub_builder = RedisMakeSyncAtomJob(root_id, ticket_data, sync_kwargs, sync_params)
    redis_pipeline.add_sub_pipeline(sub_flow=sub_builder)
    # ### 建同步关系 ####################################################################### 完毕 ###

    # 执行切换 #####################################################################################
    act_kwargs.cluster["switch_condition"] = {
        "is_check_sync": True,  # 不强制切换
        "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
        "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
        "can_write_before_switch": True,
        "sync_type": act_kwargs.cluster["sync_type"],
    }
    switch_sub_pipelines = []
    for sync_relation in sync_relations:
        switch_kwargs = deepcopy(act_kwargs)
        switch_kwargs.cluster["cluster_id"] = sync_relation["cluster_id"]
        switch_kwargs.cluster["immute_domain"] = sync_relation["immute_domain"]
        switch_sub_pipelines.append(RedisClusterSwitchAtomJob(root_id, ticket_data, switch_kwargs, [sync_relation]))
    redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipelines)
    # #### 执行切换 ###############################################################################

    # 刷新bkdbmon
    for replace_info in master_repl_detail:
        new_host_master = replace_info["target"]["master"]["ip"]
        act_kwargs.exec_ip = new_host_master
        act_kwargs.cluster["ip"] = new_host_master
        act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
        redis_pipeline.add_act(
            act_name=_("{}-刷新监控").format(new_host_master),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        new_host_slave = replace_info["target"]["slave"]["ip"]
        act_kwargs.exec_ip = new_host_slave
        act_kwargs.cluster["ip"] = new_host_slave
        act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
        redis_pipeline.add_act(
            act_name=_("{}-刷新监控").format(new_host_slave),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

    # 这里高版本的Redis Slave 还需要重新同步一下数据
    sub_pipelines, resync_args = [], deepcopy(act_kwargs)
    resync_args.cluster = {
        "bk_biz_id": int(act_kwargs.cluster["bk_biz_id"]),
        "cluster_type": act_kwargs.cluster["cluster_type"],
        "bk_cloud_id": int(act_kwargs.cluster["bk_cloud_id"]),
        "instances": [],
    }
    slave_resync_instances = {}
    for sync_link in sync_relations:
        new_master, new_slave = sync_link["sync_dst1"], sync_link["sync_dst2"]
        slave_resync_instances.setdefault(new_slave, [])
        for instances in sync_link["ins_link"]:
            master_port, slave_port = instances["sync_dst1"], instances["sync_dst2"]
            slave_resync_instances[new_slave].append(
                {
                    "master_ip": new_master,
                    "master_port": int(master_port),
                    "slave_ip": new_slave,
                    "slave_port": int(slave_port),
                }
            )
    for new_slave, instances in slave_resync_instances.items():
        one_resync_args = deepcopy(resync_args)
        one_resync_args.cluster["instances"] = instances
        one_resync_args.exec_ip = new_slave
        one_resync_args.get_redis_payload_func = RedisActPayload.redis_local_redo_dr.__name__
        sub_pipelines.append(
            {
                "act_name": _("{}-本地重建Slave").format(new_slave),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(one_resync_args),
            }
        )
    redis_pipeline.add_parallel_acts(acts_list=sub_pipelines)

    # #### 下架旧实例 #############################################################################
    sub_pipelines, shutdown_kwargs = [], deepcopy(act_kwargs)
    for replace_info in master_repl_detail:
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

    # 新实例刷新版本
    version_acts = []
    for sync_relation in sync_relations:
        version_kwargs = deepcopy(act_kwargs)
        version_kwargs.cluster["cluster_id"] = sync_relation["cluster_id"]
        version_kwargs.cluster["immute_domain"] = sync_relation["immute_domain"]
        version_kwargs.cluster["update_storage"] = True
        version_acts.append(
            {
                "act_name": _("{}-新实例更新版本").format(sync_relation["immute_domain"]),
                "act_component_code": RedisUpdateVersionComponent.code,
                "kwargs": asdict(version_kwargs),
            }
        )
    redis_pipeline.add_parallel_acts(acts_list=version_acts)

    # 在流程结束时解除告警屏蔽
    redis_pipeline.add_act(
        act_name=_("解除集群告警屏蔽-{}").format(_cluster_label(act_kwargs)),
        act_component_code=DisableAlarmShieldComponent.code,
        kwargs=asdict(act_kwargs),
    )

    return redis_pipeline.build_sub_process(sub_name=_("主从替换-{}").format(act_kwargs.cluster["cluster_type"]))
