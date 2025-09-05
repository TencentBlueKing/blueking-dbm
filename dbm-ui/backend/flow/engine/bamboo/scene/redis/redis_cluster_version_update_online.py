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
import logging
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.api.cluster import nosqlcomm
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.db_meta.models import Cluster
from backend.db_services.redis.redis_dts.constants import REDIS_CONF_DEL_SLAVEOF
from backend.db_services.redis.util import is_redis_cluster_protocal, is_twemproxy_proxy_type
from backend.flow.consts import (
    DEFAULT_LAST_IO_SECOND_AGO,
    DEFAULT_MASTER_DIFF_TIME,
    SwitchType,
    SyncType,
    WriteContextOpType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ClusterIPsDbmonInstallAtomJob, ClusterProxysUpgradeAtomJob
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_makesync import RedisMakeSyncAtomJob
from backend.flow.plugins.components.collections.common.empty_node import EmptyNodeComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_update_version import RedisUpdateVersionComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import (
    async_multi_clusters_precheck,
    get_cache_backup_mode,
    get_cluster_info_by_cluster_id,
    get_cluster_info_by_ip,
    get_major_version_by_version_name,
    get_proxy_version_names_by_cluster_type,
    get_redis_version_by_ip,
    get_storage_version_names_by_cluster_type,
    get_twemproxy_cluster_server_shards,
)
from backend.flow.utils.redis.redis_util import version_ge, version_gt

logger = logging.getLogger("flow")


class RedisClusterVersionUpdateOnline(object):
    """
    redis集群在线版本升级
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        """
        self.root_id = root_id
        self.data = data
        self.cluster_cache = {}
        self.precheck()

    def precheck(self):
        """
        1. 集群是否存在
        2. 版本信息是否变化
        3. 是否存在非 running 状态的 proxy;
        4. 是否存在非 running 状态的 redis;
        5. 连接 proxy 是否正常;
        6. 连接 redis 是否正常;
        7. 是否所有master 都有 slave;
        8. 指定升级的 master 对应的 slave 目标也是升级到或者已经是同样版本;
        """
        bk_biz_id = self.data["bk_biz_id"]
        to_precheck_cluster_ids = []
        for input_item in self.data["infos"]:
            cluster_ids = RedisClusterVersionUpdateOnline.get_cluster_ids_from_info_item(input_item)
            to_precheck_cluster_ids.extend(cluster_ids)
        # 并发检查多个cluster的proxy、redis实例状态
        async_multi_clusters_precheck(to_precheck_cluster_ids)

        for input_item in self.data["infos"]:
            node_type = input_item["node_type"]
            if node_type not in (RedisVerUpdateNodeType.Proxy, RedisVerUpdateNodeType.Backend):
                raise Exception(
                    _(
                        "未知的结点类型: '{}' 必须是 '{}' 或 '{}'".format(
                            node_type, RedisVerUpdateNodeType.Proxy.value, RedisVerUpdateNodeType.Backend.value
                        )
                    )
                )

            cluster_ids = []
            if "cluster_ids" in input_item and input_item["cluster_ids"]:
                cluster_ids = input_item["cluster_ids"]
            else:
                cluster_ids.append(input_item["cluster_id"])

            if not input_item.get("target_versions"):
                raise Exception(_("redis集群 {} 目标版本为空?").format(cluster_ids))

            # Map version to IPs.
            version_ips = defaultdict(set)
            for cluster_id in cluster_ids:
                cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)

                # 检查版本是否合法
                valid_versions = (
                    get_proxy_version_names_by_cluster_type(cluster.cluster_type, True)
                    if node_type == RedisVerUpdateNodeType.Proxy
                    else get_storage_version_names_by_cluster_type(cluster.cluster_type, True)
                )

                for version_obj in input_item["target_versions"]:
                    ver = version_obj["version"]
                    ip = version_obj["ip"]
                    if ver not in valid_versions:
                        raise Exception(
                            _("Redis集群 {},节点类型: {},目标版本 {} 不合法,合法的版本:{}").format(
                                cluster.immute_domain,
                                node_type,
                                ver,
                                valid_versions,
                            )
                        )
                    version_ips[ver].add(ip)

                def collect_ip_cur_ver(ips) -> dict:
                    return {ip: get_redis_version_by_ip(cluster_id, ip) for ip in ips}

                # 进一步检查各IP机器上的版本
                if node_type == RedisVerUpdateNodeType.Proxy:
                    for target_version, ips in version_ips.items():
                        ip_cur_ver = collect_ip_cur_ver(ips)

                        if all(target_version == ip_cur_ver[ip] for ip in ips):
                            raise Exception(
                                _("集群 {} 所有proxy当前版本等于目标版本: {},无需升级").format(cluster.immute_domain, target_version)
                            )
                else:
                    for target_version, ips in version_ips.items():
                        ip_cur_ver = collect_ip_cur_ver(ips)
                        cluster_info = get_cluster_info_by_cluster_id(cluster_id)
                        master_ip_to_slave_ip = cluster_info.get("master_ip_to_slave_ip", {})

                        if any(version_gt(ip_cur_ver[ip], target_version) for ip in ips):
                            raise Exception(
                                _("集群 {} storage IP {} 当前版本 {} > 目标版本: {},不支持降级").format(
                                    cluster.immute_domain, ip, ip_cur_ver[ip], target_version
                                )
                            )

                        for ip in ips:
                            # 检查 Master 对应 Slave 也升级到对应版本或者已经是目标版本
                            if ip in cluster_info.get("master_ports", {}):
                                slave_ip = master_ip_to_slave_ip.get(ip)
                                if not slave_ip:
                                    raise Exception(
                                        _("集群 {} Master {} 没有找到对应的 Slave").format(cluster.immute_domain, ip)
                                    )
                                slave_upgrading_too = slave_ip in ips
                                slave_already_upgraded = version_ge(
                                    get_redis_version_by_ip(cluster_id, slave_ip), target_version
                                )
                                if not slave_upgrading_too and not slave_already_upgraded:
                                    raise Exception(
                                        _("集群 {} 的Master {} 对应的 Slave {} 版本小于目标版本且不在升级列表中").format(
                                            cluster.immute_domain, ip, slave_ip
                                        )
                                    )
                            elif ip not in cluster_info.get("slave_ports", {}):
                                raise Exception(_("集群 {} IP {} 既不是master也不是slave").format(cluster.immute_domain, ip))

    @staticmethod
    def get_cluster_ids_from_info_item(info_item: Dict) -> List[int]:
        # 兼容传入cluster_id 和 cluster_ids 两种方式
        cluster_ids = []
        if "cluster_ids" in info_item and info_item["cluster_ids"]:
            cluster_ids = info_item["cluster_ids"]
        else:
            cluster_ids.append(info_item["cluster_id"])
        return cluster_ids

    def version_update_flow(self):
        """
        Redis集群在线版本升级流程
        ========================

        升级过程包含两个步骤：Proxy升级 和 Backend升级

        Proxy升级流程
        --------------
        1. 将参数解析为 [{target_version: ips}] 格式
        2. 遍历任务列表并行执行Proxy升级原子任务

        Backend升级流程
        ----------------
        1. Backend升级涉及多种架构
           ┌─ RedisCluster 集群架构
           │  ├─ Twemproxy 架构
           │  └─ Predixy 架构
           └─ TendisRedisInstance 主从架构

        2. 升级步骤详述
           - 对于 RedisCluster 架构：
             1. 先升级所有指定的 Slave 节点
             2. 对指定的 Master (如果有) 实例发起主从切换或 Failover 操作
             3. 升级指定的 Master 节点

           - 对于 TendisRedisInstance 架构：
             1. 类似 Twemproxy，但一个 cluster_id 只涉及一个 Master 和一个 Slave
             2. 仅升级 Slave：无需切换操作
             3. 同时升级 Master 和 Slave：
                - 先升级 Slave 节点
                - 执行切换操作
                - 升级 Master 节点
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        bk_biz_id = self.data["bk_biz_id"]

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        # 先升级 proxy
        for input_item in self.data["infos"]:
            cluster_ids = RedisClusterVersionUpdateOnline.get_cluster_ids_from_info_item(input_item)

            if input_item["node_type"] == RedisVerUpdateNodeType.Proxy:
                self._create_proxy_upgrade_sub_pipelines(input_item, cluster_ids, redis_pipeline)

        # 再升级 storage
        sub_pipelines = self._create_storage_upgrade_sub_pipelines(trans_files, bk_biz_id)
        if sub_pipelines:
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()

    def _create_proxy_upgrade_sub_pipelines(self, input_item, cluster_ids, redis_pipeline):
        """Create sub-pipelines for proxy upgrades."""
        sub_pipelines = []
        for cluster_id in cluster_ids:
            cluster_meta_data = get_cluster_info_by_cluster_id(int(cluster_id))
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True

            versions = defaultdict(set)
            for target in input_item["target_versions"]:
                versions[target["version"]].add(target["ip"])

            for version, ips in versions.items():
                sub_builder = ClusterProxysUpgradeAtomJob(
                    self.root_id,
                    self.data,
                    act_kwargs,
                    {
                        "cluster_domain": cluster_meta_data["immute_domain"],
                        "target_ips": ips,
                        "target_version": version,
                    },
                )
                sub_pipelines.append(sub_builder)

        if sub_pipelines:
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

    def _create_storage_upgrade_sub_pipelines(self, trans_files, bk_biz_id):
        """创建存储升级子流水线"""
        sub_pipelines = []
        for input_item in self.data["infos"]:
            if input_item["node_type"] != RedisVerUpdateNodeType.Backend:
                continue

            # 兼容传入cluster_id 和 cluster_ids 两种方式
            cluster_ids = RedisClusterVersionUpdateOnline.get_cluster_ids_from_info_item(input_item)
            cluster_id = int(cluster_ids[0])

            versions = defaultdict(set)
            for target in input_item["target_versions"]:
                versions[target["version"]].add(target["ip"])

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            # 加个缓存
            if not self.cluster_cache.get(cluster_id):
                self.cluster_cache[cluster_id] = get_cluster_info_by_cluster_id(cluster_id)
            cluster_meta_data = self.cluster_cache[cluster_id]
            act_kwargs.bk_cloud_id = cluster_meta_data["bk_cloud_id"]
            act_kwargs.cluster.update(cluster_meta_data)

            target_pipelines = []
            for target_version, ips in versions.items():
                target_major_version = get_major_version_by_version_name(target_version)

                # 主从结构(RedisInstance), 专门处理
                if cluster_meta_data["cluster_type"] == ClusterType.TendisRedisInstance:
                    sub_builder = self.redisinstance_version_update_sub_flow(
                        act_kwargs, cluster_meta_data["cluster_id"], target_major_version, ips
                    )
                    target_pipelines.append(sub_builder)
                    continue

                # 非主从架构(RedisCluster), 继续执行
                target_pipeline = self._create_redis_cluster_upgrade_pipeline(
                    act_kwargs, cluster_meta_data, cluster_id, target_major_version, ips, trans_files, bk_biz_id
                )
                target_pipelines.append(
                    target_pipeline.build_sub_process(sub_name=_("目标版本{}在线升级".format(target_major_version)))
                )
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=target_pipelines)
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("集群{}在线升级".format(cluster_meta_data["cluster_name"])))
            )
        return sub_pipelines

    def _create_redis_cluster_upgrade_pipeline(
        self, act_kwargs, cluster_meta_data, cluster_id, target_major_version, ips, trans_files, bk_biz_id
    ):
        """创建Redis集群升级流水线"""
        target_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        # 初始化配置和下发介质包
        self._add_initialization_acts(target_pipeline, act_kwargs, ips, trans_files, target_major_version)

        # 卸载 dbmon
        self._add_dbmon_uninstall_act(target_pipeline, act_kwargs, cluster_meta_data, ips)

        # 升级 Slave 节点
        self._add_slave_upgrade_acts(target_pipeline, act_kwargs, cluster_meta_data, ips, target_major_version)

        # 获取需要切换的主从对
        pairs_to_switch = self._get_pairs_to_switch(cluster_meta_data, ips)

        # 处理不同类型的集群升级
        if is_redis_cluster_protocal(cluster_meta_data["cluster_type"]) and pairs_to_switch:
            self._handle_redis_cluster_upgrade(
                target_pipeline, act_kwargs, cluster_meta_data, ips, target_major_version, pairs_to_switch
            )
        elif is_twemproxy_proxy_type(cluster_meta_data["cluster_type"]) and pairs_to_switch:
            self._handle_twemproxy_cluster_upgrade(
                target_pipeline,
                act_kwargs,
                cluster_meta_data,
                cluster_id,
                ips,
                target_major_version,
                pairs_to_switch,
                bk_biz_id,
            )

        # 更新元数据（如果有切换发生）
        if pairs_to_switch:
            self._add_metadata_update_acts(
                target_pipeline, act_kwargs, cluster_meta_data, cluster_id, ips, target_major_version, bk_biz_id
            )

        # 重装 dbmon
        self._add_dbmon_reinstall_act(target_pipeline, act_kwargs, cluster_meta_data, ips)

        return target_pipeline

    def _add_initialization_acts(self, target_pipeline, act_kwargs, ips, trans_files, target_major_version):
        """添加初始化配置和下发介质包的动作"""
        target_pipeline.add_act(
            act_name=_("初始化配置"),
            act_component_code=GetRedisActPayloadComponent.code,
            kwargs=asdict(act_kwargs),
        )

        all_ips = list(ips)
        act_kwargs.exec_ip = all_ips
        act_kwargs.file_list = trans_files.redis_cluster_version_update(target_major_version)
        target_pipeline.add_act(
            act_name=_("目标IP 下发介质包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(act_kwargs),
        )

    def _add_dbmon_uninstall_act(self, target_pipeline, act_kwargs, cluster_meta_data, ips):
        """添加卸载dbmon的动作"""
        act_kwargs.cluster = {}
        sub_builder = ClusterIPsDbmonInstallAtomJob(
            self.root_id,
            self.data,
            act_kwargs,
            {
                "cluster_domain": cluster_meta_data["immute_domain"],
                "ips": list(ips),
                "is_stop": True,
            },
        )
        target_pipeline.add_sub_pipeline(sub_builder)

    def _add_slave_upgrade_acts(self, target_pipeline, act_kwargs, cluster_meta_data, ips, target_major_version):
        """添加Slave升级动作"""
        act_kwargs.cluster = {}
        acts_list = []
        for ip, ports in cluster_meta_data["slave_ports"].items():
            # 跳过没有指定的 Slave
            if ip not in ips:
                continue
            act_kwargs.exec_ip = ip
            act_kwargs.cluster["ip"] = ip
            act_kwargs.cluster["ports"] = ports
            act_kwargs.cluster["password"] = cluster_meta_data["redis_password"]
            act_kwargs.cluster["db_version"] = target_major_version
            act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
            act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_online_payload.__name__
            acts_list.append(
                {
                    "act_name": _("old_slave:{} 版本升级").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        if acts_list:
            target_pipeline.add_parallel_acts(acts_list=acts_list)
        else:
            target_pipeline.add_act(
                act_name=_("无Slave需随Master升级"), act_component_code=EmptyNodeComponent.code, kwargs={}
            )

    def _get_pairs_to_switch(self, cluster_meta_data, ips):
        """获取需要切换的主从对"""
        pairs_to_switch = []
        for pair in cluster_meta_data["master_slave_ins_pairs"]:
            if pair["master"]["ip"] in ips:
                pairs_to_switch.append(pair)
        return pairs_to_switch

    def _handle_redis_cluster_upgrade(
        self, target_pipeline, act_kwargs, cluster_meta_data, ips, target_major_version, pairs_to_switch
    ):
        """处理Redis Cluster类型的升级"""
        # 切换
        first_master_ip = list(cluster_meta_data["master_ports"].keys())[0]
        act_kwargs.exec_ip = first_master_ip
        act_kwargs.cluster = {
            "redis_password": cluster_meta_data["redis_password"],
            "redis_master_slave_pairs": pairs_to_switch,
            "force": False,
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_failover.__name__
        target_pipeline.add_act(
            act_name=_("{} 集群:{}执行 cluster failover").format(first_master_ip, cluster_meta_data["cluster_name"]),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 升级
        act_kwargs.cluster = {}
        acts_list = []
        for ip, ports in cluster_meta_data["master_ports"].items():
            if ip not in ips:
                continue
            act_kwargs.exec_ip = ip
            act_kwargs.cluster["ip"] = ip
            act_kwargs.cluster["ports"] = ports
            act_kwargs.cluster["password"] = cluster_meta_data["redis_password"]
            act_kwargs.cluster["db_version"] = target_major_version
            act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
            act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_online_payload.__name__
            acts_list.append(
                {
                    "act_name": _("new slave:{} 版本升级").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        target_pipeline.add_parallel_acts(acts_list=acts_list)

    def _handle_twemproxy_cluster_upgrade(
        self,
        target_pipeline,
        act_kwargs,
        cluster_meta_data,
        cluster_id,
        ips,
        target_major_version,
        pairs_to_switch,
        bk_biz_id,
    ):
        """处理Twemproxy类型的集群升级"""
        first_master_ip = list(cluster_meta_data["master_ports"].keys())[0]

        # 主从切换
        self._add_twemproxy_switch_acts(
            target_pipeline, act_kwargs, cluster_meta_data, cluster_id, first_master_ip, pairs_to_switch
        )

        # 清理slaveof配置
        self._add_slaveof_cleanup_acts(target_pipeline, act_kwargs, cluster_meta_data, ips)

        # 升级old_master
        self._add_old_master_upgrade_acts(target_pipeline, act_kwargs, cluster_meta_data, ips, target_major_version)

        # 清档old_master
        self._add_old_master_flush_acts(target_pipeline, act_kwargs, cluster_meta_data, ips)

        # old_master做new_slave
        self._add_master_to_slave_sync_acts(target_pipeline, act_kwargs, cluster_meta_data, cluster_id, ips, bk_biz_id)

    def _add_twemproxy_switch_acts(
        self, target_pipeline, act_kwargs, cluster_meta_data, cluster_id, first_master_ip, pairs_to_switch
    ):
        """添加Twemproxy主从切换动作"""
        act_kwargs.exec_ip = first_master_ip
        act_kwargs.cluster = {}
        act_kwargs.cluster["cluster_id"] = cluster_id
        act_kwargs.cluster["immute_domain"] = cluster_meta_data["immute_domain"]
        act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
        act_kwargs.cluster["switch_condition"] = {
            "is_check_sync": True,  # 不强制切换
            "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
            "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
            "can_write_before_switch": True,
            "sync_type": SyncType.SYNC_MS.value,
        }
        # 先将 old_slave 切换成 new_master
        act_kwargs.cluster["switch_info"] = pairs_to_switch
        act_kwargs.get_redis_payload_func = RedisActPayload.redis__switch_4_scene.__name__
        target_pipeline.add_act(
            act_name=_("集群:{} 主从切换").format(cluster_meta_data["cluster_name"]),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.cluster["instances"] = nosqlcomm.other.get_cluster_proxies(
            cluster_id=act_kwargs.cluster["cluster_id"]
        )
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_twemproxy_backends_4_scene.__name__
        target_pipeline.add_act(
            act_name=_("Redis-{}-检查切换状态").format(first_master_ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

    def _add_slaveof_cleanup_acts(self, target_pipeline, act_kwargs, cluster_meta_data, ips):
        """添加清理slaveof配置的动作"""
        acts_list = []
        act_kwargs.cluster = {}
        for master_ip, master_ports in cluster_meta_data["master_ports"].items():
            if master_ip not in ips:
                continue
            slave_ip = cluster_meta_data["master_ip_to_slave_ip"][master_ip]
            slave_ports = cluster_meta_data["slave_ports"][slave_ip]

            act_kwargs.exec_ip = master_ip
            act_kwargs.write_op = WriteContextOpType.APPEND.value
            ports_str = "\n".join(str(port) for port in master_ports)
            act_kwargs.cluster["shell_command"] = REDIS_CONF_DEL_SLAVEOF.format(ports_str)
            acts_list.append(
                {
                    "act_name": _("old_master:{} 删除slaveof配置").format(master_ip),
                    "act_component_code": ExecuteShellScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

            act_kwargs.exec_ip = slave_ip
            act_kwargs.write_op = WriteContextOpType.APPEND.value
            ports_str = "\n".join(str(port) for port in slave_ports)
            act_kwargs.cluster["shell_command"] = REDIS_CONF_DEL_SLAVEOF.format(ports_str)
            acts_list.append(
                {
                    "act_name": _("old_slave:{} 删除slaveof配置").format(slave_ip),
                    "act_component_code": ExecuteShellScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        target_pipeline.add_parallel_acts(acts_list=acts_list)

    def _add_old_master_upgrade_acts(self, target_pipeline, act_kwargs, cluster_meta_data, ips, target_major_version):
        """添加old_master升级动作"""
        act_kwargs.cluster = {}
        act_kwargs.write_op = None
        acts_list = []
        for ip, ports in cluster_meta_data["master_ports"].items():
            if ip not in ips:
                continue
            act_kwargs.exec_ip = ip
            act_kwargs.cluster["ip"] = ip
            act_kwargs.cluster["ports"] = ports
            act_kwargs.cluster["password"] = cluster_meta_data["redis_password"]
            act_kwargs.cluster["db_version"] = target_major_version
            act_kwargs.cluster["role"] = InstanceRole.REDIS_MASTER.value
            act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_online_payload.__name__
            acts_list.append(
                {
                    "act_name": _("new slave:{} 版本升级").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        target_pipeline.add_parallel_acts(acts_list=acts_list)

    def _add_old_master_flush_acts(self, target_pipeline, act_kwargs, cluster_meta_data, ips):
        """添加清档old_master的动作"""
        acts_list = []
        for ip, ports in cluster_meta_data["master_ports"].items():
            if ip not in ips:
                continue
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {}
            act_kwargs.cluster["domain_name"] = cluster_meta_data["immute_domain"]
            act_kwargs.cluster["db_version"] = cluster_meta_data["major_version"]
            act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
            act_kwargs.cluster["ip"] = ip
            act_kwargs.cluster["ports"] = ports
            act_kwargs.cluster["force"] = False
            act_kwargs.cluster["db_list"] = [0]
            act_kwargs.cluster["flushall"] = True
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_flush_data_payload.__name__
            acts_list.append(
                {
                    "act_name": _("old_master:{} 清档").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        target_pipeline.add_parallel_acts(acts_list=acts_list)

    def _add_master_to_slave_sync_acts(
        self, target_pipeline, act_kwargs, cluster_meta_data, cluster_id, ips, bk_biz_id
    ):
        """添加old_master做new_slave的同步动作"""
        twemproxy_server_shards = get_twemproxy_cluster_server_shards(bk_biz_id, cluster_id, {})
        child_pipelines = []
        act_kwargs.cluster = {}
        act_kwargs.cluster["bk_biz_id"] = bk_biz_id
        act_kwargs.cluster["bk_cloud_id"] = cluster_meta_data["bk_cloud_id"]
        act_kwargs.cluster["immute_domain"] = cluster_meta_data["immute_domain"]
        act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
        act_kwargs.cluster["cluster_name"] = cluster_meta_data["cluster_name"]
        masterip_to_slaveip = cluster_meta_data["master_ip_to_slave_ip"]
        for master_ip, ports in cluster_meta_data["master_ports"].items():
            if master_ip not in ips:
                continue
            master_ports = cluster_meta_data["master_ports"][master_ip]
            slave_ip = masterip_to_slaveip[master_ip]
            slave_ports = cluster_meta_data["slave_ports"][slave_ip]
            sync_param = {
                "sync_type": SyncType.SYNC_MS,
                "origin_1": slave_ip,
                "sync_dst1": master_ip,
                "ins_link": [],
                "server_shards": twemproxy_server_shards.get(slave_ip, {}),
                "cache_backup_mode": get_cache_backup_mode(bk_biz_id, cluster_id),
            }
            for idx, port in enumerate(master_ports):
                sync_param["ins_link"].append(
                    {
                        "origin_1": str(slave_ports[idx]),
                        "sync_dst1": str(port),
                    }
                )
            sync_builder = RedisMakeSyncAtomJob(
                root_id=self.root_id, ticket_data=self.data, sub_kwargs=act_kwargs, params=sync_param
            )
            child_pipelines.append(sync_builder)
        target_pipeline.add_parallel_sub_pipeline(child_pipelines)

    def _add_metadata_update_acts(
        self, target_pipeline, act_kwargs, cluster_meta_data, cluster_id, ips, target_major_version, bk_biz_id
    ):
        """添加元数据更新动作"""
        # 修改元数据指向(old_masters和proxy关系断开,new_master增加和proxy关系)
        # 更新 cluster.nosqlstoragesetdtl_set
        # new_masters 设置 instance_role 为 InstanceRole.REDIS_MASTER.value
        # 最后娜动CC模块
        act_kwargs.cluster = {}
        act_kwargs.cluster["bk_biz_id"] = bk_biz_id
        act_kwargs.cluster["bk_cloud_id"] = cluster_meta_data["bk_cloud_id"]
        act_kwargs.cluster["immute_domain"] = cluster_meta_data["immute_domain"]
        act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
        act_kwargs.cluster["cluster_name"] = cluster_meta_data["cluster_name"]
        act_kwargs.cluster["cluster_id"] = cluster_id
        act_kwargs.cluster["switch_condition"] = {
            "is_check_sync": True,  # 不强制切换
            "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
            "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
            "can_write_before_switch": True,
            "sync_type": SyncType.SYNC_MS.value,
        }
        act_kwargs.cluster["sync_relation"] = []
        masterip_to_slaveip = cluster_meta_data["master_ip_to_slave_ip"]
        for master_ip, ports in cluster_meta_data["master_ports"].items():
            # Master 没升级的情况下没有发生切换，跳过
            if master_ip not in ips:
                continue
            master_ports = cluster_meta_data["master_ports"][master_ip]
            slave_ip = masterip_to_slaveip[master_ip]
            slave_ports = cluster_meta_data["slave_ports"][slave_ip]
            for idx, port in enumerate(master_ports):
                act_kwargs.cluster["sync_relation"].append(
                    {
                        "ejector": {
                            "ip": master_ip,
                            "port": int(port),
                        },
                        "receiver": {
                            "ip": slave_ip,
                            "port": int(slave_ports[idx]),
                        },
                    }
                )
        act_kwargs.cluster["meta_func_name"] = RedisDBMeta.tendis_switch_4_scene.__name__
        target_pipeline.add_act(
            act_name=_("Redis-元数据切换"),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 主从元数据交换,StorageInstanceTuple中,master变slave,slave变master
        acts_list = []
        for master_ip, master_ports in cluster_meta_data["master_ports"].items():
            # Master 没有升级的情况下没有切换发生，跳过
            if master_ip not in ips:
                continue
            act_kwargs.cluster["meta_update_ip"] = master_ip
            slave_ip = masterip_to_slaveip[master_ip]
            act_kwargs.cluster["meta_update_ports"] = master_ports
            act_kwargs.cluster["meta_update_status"] = InstanceStatus.RUNNING.value
            act_kwargs.cluster["meta_func_name"] = RedisDBMeta.instances_failover_4_scene.__name__
            acts_list.append(
                {
                    "act_name": _("master:{}-slave:{}-主从交换".format(master_ip, slave_ip)),
                    "act_component_code": RedisDBMetaComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        target_pipeline.add_parallel_acts(acts_list=acts_list)

        # 更新元数据中集群版本
        act_kwargs.cluster["bk_biz_id"] = bk_biz_id
        act_kwargs.cluster["bk_cloud_id"] = cluster_meta_data["bk_cloud_id"]
        act_kwargs.cluster["immute_domain"] = cluster_meta_data["immute_domain"]
        act_kwargs.cluster["cluster_ids"] = [cluster_meta_data["cluster_id"]]
        # 版本记录为集群当中存在的最新版本
        newest_version = (
            target_major_version
            if version_ge(target_major_version, cluster_meta_data["major_version"])
            else cluster_meta_data["major_version"]
        )
        act_kwargs.cluster["db_version"] = newest_version
        act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_cluster_version_update.__name__
        target_pipeline.add_act(
            act_name=_("Redis-元数据更新集群版本"),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 更新 dbconfig 中版本信息
        act_kwargs.cluster = {
            "bk_biz_id": bk_biz_id,
            "cluster_domain": cluster_meta_data["immute_domain"],
            "current_version": cluster_meta_data["major_version"],
            "target_version": newest_version,
            "cluster_type": cluster_meta_data["cluster_type"],
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_dbconfig.__name__
        target_pipeline.add_act(
            act_name=_("Redis-更新dbconfig中集群版本"),
            act_component_code=RedisConfigComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 更新集群 集群 版本
        act_kwargs.cluster["update_all"] = True
        act_kwargs.cluster["cluster_id"] = cluster_meta_data["cluster_id"]
        act_kwargs.cluster["bk_biz_id"] = bk_biz_id
        target_pipeline.add_act(
            act_name=_("{}-更新版本").format(cluster_meta_data["immute_domain"]),
            act_component_code=RedisUpdateVersionComponent.code,
            kwargs=asdict(act_kwargs),
        )

    def _add_dbmon_reinstall_act(self, target_pipeline, act_kwargs, cluster_meta_data, ips):
        """添加重装dbmon的动作"""
        act_kwargs.cluster = {}
        sub_builder = ClusterIPsDbmonInstallAtomJob(
            self.root_id,
            self.data,
            act_kwargs,
            {
                "cluster_domain": cluster_meta_data["immute_domain"],
                "ips": list(ips),
                "is_stop": False,
            },
        )
        target_pipeline.add_sub_pipeline(sub_builder)

    @staticmethod
    def get_master_meta_for_redisinstance(cluster_id: int) -> dict:
        cluster = Cluster.objects.get(id=cluster_id)
        master_inst = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value).first()
        if not master_inst:
            raise Exception(
                "cluster_id:{} immute_domain:{} master instance not found".format(cluster.id, cluster.immute_domain)
            )
        # 找到master ip
        master_ip = master_inst.machine.ip
        return get_cluster_info_by_ip(master_ip)

    def redisinstance_version_update_sub_flow(
        self, sub_kwargs: ActKwargs, cluster_id: int, target_major_version: str, ips: set
    ) -> SubBuilder:
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        act_kwargs = deepcopy(sub_kwargs)
        act_kwargs.cluster = {}
        cluster_meta_data = get_cluster_info_by_cluster_id(cluster_id)
        act_kwargs.bk_cloud_id = cluster_meta_data["bk_cloud_id"]
        act_kwargs.cluster.update(cluster_meta_data)

        master_meta = RedisClusterVersionUpdateOnline.get_master_meta_for_redisinstance(cluster_id)
        if len(master_meta["instance_role"]) != 1:
            raise Exception(_("master ip:{} 包含了两种角色{}".format(master_meta["ip"], master_meta["instance_role"])))

        sub_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        master_ip = master_meta["ip"]
        master_ports = master_meta["ports"]
        slave_ip = master_meta["pair_ip"]
        slave_ports = master_meta["pair_ports"]

        all_ips = [master_ip, slave_ip]
        only_upgrade_slave = master_ip not in ips
        if only_upgrade_slave:
            all_ips = [
                slave_ip,
            ]

        act_kwargs.exec_ip = all_ips
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs.file_list = trans_files.redis_cluster_version_update(target_major_version)
        sub_pipeline.add_act(
            act_name=_("主从IP 下发介质包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 关闭bkdbmon
        acts_list = []
        for ip in all_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {"ip": ip, "is_stop": True}
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
            acts_list.append(
                {
                    "act_name": _("{}-暂停bkdbmon").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

        # 升级slave
        act_kwargs.cluster = {}
        act_kwargs.exec_ip = slave_ip
        act_kwargs.cluster["ip"] = slave_ip
        act_kwargs.cluster["ports"] = slave_ports
        act_kwargs.cluster["db_version"] = target_major_version
        act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
        act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_online_payload.__name__
        sub_pipeline.add_act(
            act_name=_("old_slave:{} 版本升级至 {}").format(slave_ip, target_major_version),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 如果主从都升级才进行下面的步骤
        if not only_upgrade_slave:
            # slave上执行config set
            act_kwargs.cluster = {}
            act_kwargs.exec_ip = slave_ip
            act_kwargs.cluster["ip"] = slave_ip
            act_kwargs.cluster["ports"] = slave_ports
            act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
            act_kwargs.cluster["sync_to_config_file"] = True
            act_kwargs.cluster["config_set_map"] = {"slave-read-only": "no", "appendonly": "no"}
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_config_set.__name__
            sub_pipeline.add_act(
                act_name=_("old_slave:{} slave-read-only设置为yes").format(slave_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 人工确认
            sub_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})

            # 更新域名信息
            cluster_ids = []
            for cluster in master_meta["clusters"]:
                cluster_ids.append(cluster["cluster_id"])
            act_kwargs.cluster = {
                "cluster_ids": cluster_ids,
                "meta_func_name": RedisDBMeta.switch_dns_for_redis_instance_version_upgrade.__name__,
            }
            sub_pipeline.add_act(
                act_name=_("cluster:{} 域名指向修改").format(cluster_ids),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 执行切换
            # slave执行 slaveof no one
            # 关闭master
            acts_list = []
            act_kwargs.cluster = {
                "db_version": "",  # 每个redisinstance主从架构immute_domain等不一样
                "immute_domain": "",
                "cluster_type": "",
                "switch_condition": {
                    "switch_option": SwitchType.SWITCH_WITH_CONFIRM.value,
                    "is_check_sync": True,
                    "sync_type": SyncType.SYNC_MS.value,
                    "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
                    "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
                    "can_write_before_switch": True,
                },
                "switch_info": [],
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.redis__switch_4_scene.__name__
            for cluster in master_meta["clusters"]:
                tmp_cluster_meta = get_cluster_info_by_cluster_id(cluster["cluster_id"])
                act_kwargs.cluster["cluster_id"] = tmp_cluster_meta["cluster_id"]
                act_kwargs.cluster["db_version"] = tmp_cluster_meta["major_version"]
                act_kwargs.cluster["immute_domain"] = tmp_cluster_meta["immute_domain"]
                act_kwargs.cluster["cluster_type"] = tmp_cluster_meta["cluster_type"]
                act_kwargs.cluster["switch_info"] = tmp_cluster_meta["master_slave_ins_pairs"]
                acts_list.append(
                    {
                        "act_name": _("{}-slave提升为master".format(tmp_cluster_meta["immute_domain"])),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 这个地方需要增加一个人工确认节点。并且尽量慢点执行。否则client可能还会访问到old master
            sub_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})

            # 升级old master
            act_kwargs.cluster = {}
            act_kwargs.exec_ip = master_ip
            act_kwargs.cluster["ip"] = master_ip
            act_kwargs.cluster["ports"] = master_ports
            act_kwargs.cluster["db_version"] = target_major_version
            act_kwargs.cluster["role"] = InstanceRole.REDIS_MASTER.value
            act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_online_payload.__name__
            sub_pipeline.add_act(
                act_name=_("new_slave:{} 版本升级至 {}").format(master_ip, target_major_version),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 更新元数据信息
            act_kwargs.cluster = {
                "cluster_ids": cluster_ids,
                "meta_func_name": RedisDBMeta.update_meta_for_redis_instance_version_upgrade.__name__,
            }
            sub_pipeline.add_act(
                act_name=_("cluster:{} 元数据master和slave互换").format(cluster_ids),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 清档old_master
            # 清档的原因是,下一步建立同步关系时,如果old_master上还有数据,会报错
            acts_list = []
            act_kwargs.cluster = {}
            for cluster in master_meta["clusters"]:
                tmp_cluster_meta = get_cluster_info_by_cluster_id(cluster["cluster_id"])
                act_kwargs.cluster["domain_name"] = tmp_cluster_meta["immute_domain"]
                act_kwargs.cluster["db_version"] = tmp_cluster_meta["major_version"]
                act_kwargs.cluster["cluster_type"] = tmp_cluster_meta["cluster_type"]
                for master_ip, master_ports in tmp_cluster_meta["master_ports"].items():
                    act_kwargs.exec_ip = master_ip
                    act_kwargs.cluster["ip"] = master_ip
                    act_kwargs.cluster["ports"] = master_ports
                    act_kwargs.cluster["force"] = False
                    act_kwargs.cluster["db_list"] = [0]
                    act_kwargs.cluster["flushall"] = True
                    act_kwargs.get_redis_payload_func = RedisActPayload.redis_flush_data_payload.__name__
                    acts_list.append(
                        {
                            "act_name": _("old master:{} ports:{} 清档").format(master_ip, master_ports),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(act_kwargs),
                        }
                    )
            if len(acts_list) > 0:
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # old_master 做 new_slave
            child_pipelines = []
            act_kwargs.cluster = {}
            for cluster in master_meta["clusters"]:
                tmp_cluster_meta = get_cluster_info_by_cluster_id(cluster["cluster_id"])
                act_kwargs.cluster["bk_biz_id"] = tmp_cluster_meta["bk_biz_id"]
                act_kwargs.cluster["bk_cloud_id"] = tmp_cluster_meta["bk_cloud_id"]
                act_kwargs.cluster["immute_domain"] = tmp_cluster_meta["immute_domain"]
                act_kwargs.cluster["cluster_name"] = tmp_cluster_meta["cluster_name"]
                act_kwargs.cluster["cluster_type"] = tmp_cluster_meta["cluster_type"]
                for master_ip, master_ports in tmp_cluster_meta["master_ports"].items():
                    slave_ip = tmp_cluster_meta["master_ip_to_slave_ip"][master_ip]
                    slave_ports = tmp_cluster_meta["slave_ports"][slave_ip]
                    sync_param = {
                        "sync_type": SyncType.SYNC_MS,
                        "origin_1": slave_ip,
                        "sync_dst1": master_ip,
                        "ins_link": [],
                        "server_shards": {},
                        "cache_backup_mode": get_cache_backup_mode(
                            tmp_cluster_meta["bk_biz_id"], tmp_cluster_meta["cluster_id"]
                        ),
                    }
                    for idx, port in enumerate(master_ports):
                        sync_param["ins_link"].append(
                            {
                                "origin_1": str(slave_ports[idx]),
                                "sync_dst1": str(port),
                            }
                        )
                    sync_builder = RedisMakeSyncAtomJob(
                        root_id=self.root_id, ticket_data=self.data, sub_kwargs=act_kwargs, params=sync_param
                    )
                    child_pipelines.append(sync_builder)
            if len(child_pipelines) > 0:
                sub_pipeline.add_parallel_sub_pipeline(child_pipelines)

            # 更新元数据中集群版本
            newest_version = (
                target_major_version
                if version_ge(target_major_version, cluster_meta_data["major_version"])
                else cluster_meta_data["major_version"]
            )
            act_kwargs.cluster["bk_biz_id"] = cluster_meta_data["bk_biz_id"]
            act_kwargs.cluster["bk_cloud_id"] = cluster_meta_data["bk_cloud_id"]
            act_kwargs.cluster["cluster_ids"] = cluster_ids
            act_kwargs.cluster["db_version"] = newest_version
            act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_cluster_version_update.__name__
            sub_pipeline.add_act(
                act_name=_("Redis-元数据更新集群版本"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 更新 dbconfig 中版本信息
            acts_list = []
            for item in master_meta["clusters"]:
                cluster = Cluster.objects.get(id=item["cluster_id"])
                act_kwargs.cluster = {
                    "bk_biz_id": cluster.bk_biz_id,
                    "cluster_domain": cluster.immute_domain,
                    "current_version": cluster.major_version,
                    "target_version": newest_version,
                    "cluster_type": cluster.cluster_type,
                }
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_dbconfig.__name__
                acts_list.append(
                    {
                        "act_name": _("{}-dbconfig更新版本").format(cluster.immute_domain),
                        "act_component_code": RedisConfigComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 更新集群 集群 版本
            act_kwargs.cluster["update_storage"] = True
            act_kwargs.cluster["update_proxy"] = False
            act_kwargs.cluster["cluster_id"] = cluster_meta_data["cluster_id"]
            act_kwargs.cluster["bk_biz_id"] = cluster.bk_biz_id
            sub_pipeline.add_act(
                act_name=_("{}-更新版本").format(cluster_meta_data["immute_domain"]),
                act_component_code=RedisUpdateVersionComponent.code,
                kwargs=asdict(act_kwargs),
            )

        # 重装 dbmon
        acts_list = []
        for ip in all_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {"ip": ip, "is_stop": False}
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
            acts_list.append(
                {
                    "act_name": _("{}-重装bkdbmon").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)
        return sub_pipeline.build_sub_process(sub_name=_("主从集群 {} 版本升级").format(cluster_meta_data["cluster_name"]))
