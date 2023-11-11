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
import re
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.configuration.constants import DBType
from backend.db_meta.api.cluster import nosqlcomm
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import AppCache, Cluster
from backend.db_services.redis.redis_dts.constants import REDIS_CONF_DEL_SLAVEOF
from backend.db_services.redis.redis_dts.util import common_cluster_precheck, get_cluster_info_by_id
from backend.db_services.redis.util import is_redis_cluster_protocal, is_twemproxy_proxy_type
from backend.flow.consts import DEFAULT_LAST_IO_SECOND_AGO, DEFAULT_MASTER_DIFF_TIME, SyncType, WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_makesync import RedisMakeSyncAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import (
    get_cache_backup_mode,
    get_db_versions_by_cluster_type,
    get_twemproxy_cluster_server_shards,
)
from backend.flow.utils.redis.redis_util import get_latest_redis_package_by_version, version_equal

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
        """
        bk_biz_id = self.data["bk_biz_id"]
        for input_item in self.data["infos"]:
            if not input_item["target_version"]:
                raise Exception(_("redis集群 {} 目标版本为空?").format(input_item["cluster_id"]))
            common_cluster_precheck(bk_biz_id, input_item["cluster_id"])
            cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=input_item["cluster_id"])

            # 检查版本是否合法
            valid_versions = get_db_versions_by_cluster_type(cluster.cluster_type)
            if input_item["target_version"] not in valid_versions:
                raise Exception(
                    _("redis集群 {}目标版本 {} 不合法,合法的版本:{}").format(
                        cluster.immute_domain,
                        input_item["target_version"],
                        valid_versions,
                    )
                )

            if cluster.major_version == input_item["target_version"]:
                cluster_info = get_cluster_info_by_id(bk_biz_id=bk_biz_id, cluster_id=cluster.id)
                self.is_minor_version_update(cluster, cluster_info["redis_password"], input_item["target_version"])

    # 是否大版本相同情况下,小版本升级
    # 1. 获取一个running_master, 进而获取到 master_addr;
    # 2. 通过 redis_rpc 函数执行 info server, 进而获取到当前 current_redis_version;
    # 3. 通过 Package包获取当前 target_version 最新包的最新版本 package_latest_version;
    # 4. 对比  current_redis_version 和 package_latest_version, 相同则 raise Exception;
    def is_minor_version_update(self, cluster: Cluster, redis_password: str, target_version: str):
        one_running_master = cluster.storageinstance_set.filter(
            instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
        ).first()
        if not one_running_master:
            raise Exception(_("redis集群 {} 没有running_master??").format(cluster.immute_domain))
        master_addr = one_running_master.ip_port
        resp = DRSApi.redis_rpc(
            {
                "addresses": [master_addr],
                "db_num": 0,
                "password": redis_password,
                "command": "ping",
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        current_redis_version = re.search(r"redis_version:(.*)\r\n", resp[0]["result"]).group(1)
        redis_pkg = get_latest_redis_package_by_version(target_version)
        if not redis_pkg:
            raise Exception(_("目标版本:{} 没有找到其最新的Package信息?").format(target_version))
        package_redis_version = redis_pkg.name
        is_equal, err = version_equal(current_redis_version, package_redis_version)
        if err:
            raise Exception(
                _("redis当前版本:{} 与 package版本:{} 比较失败: {}").format(
                    current_redis_version, package_redis_version, cluster.immute_domain, err
                )
            )
        if is_equal:
            raise Exception(
                _("redis集群: redis当前版本:{} 与 package版本:{} 相同,无需升级").format(
                    cluster.immute_domain, current_redis_version, package_redis_version
                )
            )

    def get_cluster_meta_data(self, bk_biz_id: int, cluster_id: int):
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        master_ports, slave_ports = defaultdict(list), defaultdict(list)
        master_slave_pairs = []
        masterip_to_slaveip = {}

        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            master_ports[master_obj.machine.ip].append(master_obj.port)
            if master_obj.as_ejector and master_obj.as_ejector.first():
                my_slave_obj = master_obj.as_ejector.get().receiver
                slave_ports[my_slave_obj.machine.ip].append(my_slave_obj.port)
                masterip_to_slaveip[master_obj.machine.ip] = my_slave_obj.machine.ip
                master_slave_pairs.append(
                    {
                        "master": {"ip": master_obj.machine.ip, "port": master_obj.port},
                        "slave": {"ip": my_slave_obj.machine.ip, "port": my_slave_obj.port},
                    }
                )
        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": str(cluster.bk_biz_id),
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "cluster_name": cluster.name,
            "cluster_version": cluster.major_version,
            "slave_ports": dict(slave_ports),
            "master_ports": dict(master_ports),
            "masterip_to_slaveip": masterip_to_slaveip,
            "master_slave_pairs": master_slave_pairs,
        }

    def version_update_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        sub_pipelines = []
        bk_biz_id = self.data["bk_biz_id"]

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for input_item in self.data["infos"]:
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            cluster_meta_data = self.get_cluster_meta_data(bk_biz_id, int(input_item["cluster_id"]))
            cluster_info = get_cluster_info_by_id(bk_biz_id=bk_biz_id, cluster_id=input_item["cluster_id"])
            act_kwargs.bk_cloud_id = cluster_meta_data["bk_cloud_id"]
            act_kwargs.cluster.update(cluster_info)

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )
            all_ips = []
            all_ips.extend(list(cluster_meta_data["master_ports"].keys()))
            all_ips.extend(list(cluster_meta_data["slave_ports"].keys()))
            all_ips = list(set(all_ips))

            act_kwargs.exec_ip = all_ips
            act_kwargs.file_list = trans_files.redis_cluster_version_update(input_item["target_version"])
            sub_pipeline.add_act(
                act_name=_("主从所有IP 下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
            )

            act_kwargs.cluster = {}
            acts_list = []
            for ip, ports in cluster_meta_data["slave_ports"].items():
                act_kwargs.exec_ip = ip
                act_kwargs.cluster["ip"] = ip
                act_kwargs.cluster["ports"] = ports
                act_kwargs.cluster["password"] = cluster_info["redis_password"]
                act_kwargs.cluster["target_version"] = input_item["target_version"]
                act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
                act_kwargs.get_redis_payload_func = (
                    RedisActPayload.redis_cluster_version_update_online_payload.__name__
                )
                acts_list.append(
                    {
                        "act_name": _("old_slave:{} 版本升级").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)
            twemproxy_server_shards = get_twemproxy_cluster_server_shards(bk_biz_id, int(input_item["cluster_id"]), {})

            if is_redis_cluster_protocal(cluster_meta_data["cluster_type"]):
                first_master_ip = list(cluster_meta_data["master_ports"].keys())[0]
                act_kwargs.exec_ip = first_master_ip
                act_kwargs.cluster = {
                    "redis_password": cluster_info["redis_password"],
                    "redis_master_slave_pairs": cluster_meta_data["master_slave_pairs"],
                    "force": False,
                }
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_failover.__name__
                sub_pipeline.add_act(
                    act_name=_("{} 集群:{}执行 cluster failover").format(
                        first_master_ip, cluster_meta_data["cluster_name"]
                    ),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # old_master 升级
                act_kwargs.cluster = {}
                acts_list = []
                for ip, ports in cluster_meta_data["master_ports"].items():
                    act_kwargs.exec_ip = ip
                    act_kwargs.cluster["ip"] = ip
                    act_kwargs.cluster["ports"] = ports
                    act_kwargs.cluster["password"] = cluster_info["redis_password"]
                    act_kwargs.cluster["target_version"] = input_item["target_version"]
                    act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
                    act_kwargs.get_redis_payload_func = (
                        RedisActPayload.redis_cluster_version_update_online_payload.__name__
                    )
                    acts_list.append(
                        {
                            "act_name": _("new slave:{} 版本升级").format(ip),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(act_kwargs),
                        }
                    )
                sub_pipeline.add_parallel_acts(acts_list=acts_list)
            elif is_twemproxy_proxy_type(cluster_meta_data["cluster_type"]):
                first_master_ip = list(cluster_meta_data["master_ports"].keys())[0]
                act_kwargs.exec_ip = first_master_ip
                act_kwargs.cluster = {}
                act_kwargs.cluster["cluster_id"] = int(input_item["cluster_id"])
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
                act_kwargs.cluster["switch_info"] = cluster_meta_data["master_slave_pairs"]
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_twemproxy_arch_switch_4_scene.__name__
                sub_pipeline.add_act(
                    act_name=_("集群:{} 主从切换").format(cluster_meta_data["cluster_name"]),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                act_kwargs.cluster["instances"] = nosqlcomm.other.get_cluster_proxies(
                    cluster_id=act_kwargs.cluster["cluster_id"]
                )
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_twemproxy_backends_4_scene.__name__
                sub_pipeline.add_act(
                    act_name=_("Redis-{}-检查切换状态").format(first_master_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 将 master & slave 配置中 slaveof 配置清理
                acts_list = []
                act_kwargs.cluster = {}
                for master_ip, master_ports in cluster_meta_data["master_ports"].items():
                    slave_ip = cluster_meta_data["masterip_to_slaveip"][master_ip]
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
                            "act_name": _("old_slave:{} 删除slaveof配置").format(master_ip),
                            "act_component_code": ExecuteShellScriptComponent.code,
                            "kwargs": asdict(act_kwargs),
                        }
                    )
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

                # old_master 升级
                act_kwargs.cluster = {}
                act_kwargs.write_op = None
                acts_list = []
                for ip, ports in cluster_meta_data["master_ports"].items():
                    act_kwargs.exec_ip = ip
                    act_kwargs.cluster["ip"] = ip
                    act_kwargs.cluster["ports"] = ports
                    act_kwargs.cluster["password"] = cluster_info["redis_password"]
                    act_kwargs.cluster["target_version"] = input_item["target_version"]
                    act_kwargs.cluster["role"] = InstanceRole.REDIS_MASTER.value
                    act_kwargs.get_redis_payload_func = (
                        RedisActPayload.redis_cluster_version_update_online_payload.__name__
                    )
                    acts_list.append(
                        {
                            "act_name": _("new slave:{} 版本升级").format(ip),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(act_kwargs),
                        }
                    )
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

                # 清档old_master
                acts_list = []
                for ip, ports in cluster_meta_data["master_ports"].items():
                    act_kwargs.exec_ip = ip
                    act_kwargs.cluster = {}
                    act_kwargs.cluster["domain_name"] = cluster_meta_data["immute_domain"]
                    act_kwargs.cluster["db_version"] = cluster_meta_data["cluster_version"]
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
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

                # old_master 做 new_slave
                child_pipelines = []
                act_kwargs.cluster = {}
                act_kwargs.cluster["bk_biz_id"] = bk_biz_id
                act_kwargs.cluster["bk_cloud_id"] = cluster_meta_data["bk_cloud_id"]
                act_kwargs.cluster["immute_domain"] = cluster_meta_data["immute_domain"]
                act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
                act_kwargs.cluster["cluster_name"] = cluster_meta_data["cluster_name"]
                masterip_to_slaveip = cluster_meta_data["masterip_to_slaveip"]
                for master_ip, ports in cluster_meta_data["master_ports"].items():
                    master_ports = cluster_meta_data["master_ports"][master_ip]
                    slave_ip = masterip_to_slaveip[master_ip]
                    slave_ports = cluster_meta_data["slave_ports"][slave_ip]
                    sync_param = {
                        "sync_type": SyncType.SYNC_MS,
                        "origin_1": slave_ip,
                        "sync_dst1": master_ip,
                        "ins_link": [],
                        "server_shards": twemproxy_server_shards.get(slave_ip, {}),
                        "cache_backup_mode": get_cache_backup_mode(bk_biz_id, input_item["cluster_id"]),
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
                sub_pipeline.add_parallel_sub_pipeline(child_pipelines)

            # 修改元数据指向，并娜动CC模块
            act_kwargs.cluster = {}
            act_kwargs.cluster["bk_biz_id"] = bk_biz_id
            act_kwargs.cluster["bk_cloud_id"] = cluster_meta_data["bk_cloud_id"]
            act_kwargs.cluster["immute_domain"] = cluster_meta_data["immute_domain"]
            act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
            act_kwargs.cluster["cluster_name"] = cluster_meta_data["cluster_name"]
            act_kwargs.cluster["switch_condition"] = {
                "is_check_sync": True,  # 不强制切换
                "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
                "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
                "can_write_before_switch": True,
                "sync_type": SyncType.SYNC_MS.value,
            }
            act_kwargs.cluster["sync_relation"] = []
            masterip_to_slaveip = cluster_meta_data["masterip_to_slaveip"]
            for master_ip, ports in cluster_meta_data["master_ports"].items():
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
            sub_pipeline.add_act(
                act_name=_("Redis-元数据切换"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )

            acts_list = []
            for master_ip, master_ports in cluster_meta_data["master_ports"].items():
                act_kwargs.cluster["meta_update_ip"] = master_ip
                slave_ip = masterip_to_slaveip[master_ip]
                act_kwargs.cluster["meta_update_ports"] = master_ports
                act_kwargs.cluster["meta_update_status"] = InstanceStatus.RUNNING.value
                act_kwargs.cluster["meta_func_name"] = RedisDBMeta.instances_failover_4_scene.__name__
                acts_list.append(
                    {
                        "act_name": _("master:{}-slave:{}-元数据交换".format(master_ip, slave_ip)),
                        "act_component_code": RedisDBMetaComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 更新元数据中集群版本
            act_kwargs.cluster["bk_biz_id"] = bk_biz_id
            act_kwargs.cluster["bk_cloud_id"] = cluster_meta_data["bk_cloud_id"]
            act_kwargs.cluster["immute_domain"] = cluster_meta_data["immute_domain"]
            act_kwargs.cluster["target_version"] = input_item["target_version"]
            act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_cluster_version_update.__name__
            sub_pipeline.add_act(
                act_name=_("Redis-元数据更新集群版本"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )

            # 更新 dbconfig 中版本信息
            act_kwargs.cluster = {
                "bk_biz_id": bk_biz_id,
                "cluster_domain": cluster_meta_data["immute_domain"],
                "current_version": cluster_meta_data["cluster_version"],
                "target_version": input_item["target_version"],
                "cluster_type": cluster_meta_data["cluster_type"],
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_dbconfig.__name__
            sub_pipeline.add_act(
                act_name=_("Redis-更新dbconfig中集群版本"),
                act_component_code=RedisConfigComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 重装 dbmon
            acts_list = []
            act_kwargs.cluster = {}
            act_kwargs.cluster["servers"] = [
                {
                    "app": AppCache.get_app_attr(bk_biz_id, "db_app_abbr"),
                    "app_name": AppCache.get_app_attr(bk_biz_id, "bk_biz_name"),
                    "bk_biz_id": str(bk_biz_id),
                    "bk_cloud_id": int(cluster_meta_data["bk_cloud_id"]),
                    "cluster_name": cluster_meta_data["cluster_name"],
                    "cluster_type": cluster_meta_data["cluster_type"],
                    "cluster_domain": cluster_info["cluster_domain"],
                }
            ]
            for ip, ports in cluster_meta_data["slave_ports"].items():
                act_kwargs.cluster["servers"][0]["server_ip"] = ip
                act_kwargs.cluster["servers"][0]["server_ports"] = ports
                act_kwargs.cluster["servers"][0]["meta_role"] = InstanceRole.REDIS_MASTER.value
                act_kwargs.cluster["servers"][0]["server_shards"] = twemproxy_server_shards.get(ip, {})
                act_kwargs.cluster["servers"][0]["cache_backup_mode"] = get_cache_backup_mode(
                    bk_biz_id, int(input_item["cluster_id"])
                )
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                acts_list.append(
                    {
                        "act_name": _("new_master {} 重装 dbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            for ip, ports in cluster_meta_data["master_ports"].items():
                act_kwargs.cluster["servers"][0]["server_ip"] = ip
                act_kwargs.cluster["servers"][0]["server_ports"] = ports
                act_kwargs.cluster["servers"][0]["meta_role"] = InstanceRole.REDIS_SLAVE.value
                act_kwargs.cluster["servers"][0]["server_shards"] = twemproxy_server_shards.get(ip, {})
                act_kwargs.cluster["servers"][0]["cache_backup_mode"] = get_cache_backup_mode(
                    bk_biz_id, int(input_item["cluster_id"])
                )
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                acts_list.append(
                    {
                        "act_name": _("new_slave {} 重装 dbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("集群{}版本在线升级".format(cluster_meta_data["cluster_name"])))
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
