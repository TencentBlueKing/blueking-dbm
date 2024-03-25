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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import AffinityEnum, DBType
from backend.db_meta.api import common
from backend.db_meta.api.cluster.apis import query_cluster_by_hosts
from backend.db_meta.enums import InstanceInnerRole, InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache, StorageInstance
from backend.db_services.version.constants import RedisVersion
from backend.flow.consts import DEPENDENCIES_PLUGINS, ClusterStatus, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs, InstallNodemanPluginKwargs
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode

logger = logging.getLogger("flow")


class RedisInstanceApplyFlow(object):
    """
            redis 单实例部署流程。
            这个单据因为密码、maxmemory、db_num这些东西可能不同。
            另外，为了减少介质下发、安装dbmon这些节点的重复执行，最好不要用子流程批量安装。

            {
        "uid":"2022051612120001",
        "created_by":"admin",
        "bk_biz_id":10,
        "bk_cloud_id":0,
        "ticket_type":"REDIS_CLUSTER_APPLY",
        "cluster_type":"TendisRedisInstance",
        "infos":[
            {
                "port":30000,
                "domain_name":"redis14.cloud.zbin.db",
                "cluster_name":"pwdtest",
                "cluster_alias":"集群测试",
                "city":"上海",
                "city_code":"上海",
                "maxmemory":2147483648,
                "db_version":"Redis-6",
                "databases":2,
                "redis_pwd":"redisrandompwd",
                "backend_group":{
                    "master":{
                        "ip":"1.1.1.1",
                        "bk_cloud_id":0
                    },
                    "slave":{
                        "ip":"2.2.2.2",
                        "bk_cloud_id":0
                    }
                },
                "resource_spec":{
                    "id":0,
                    "cpu":{
                        "max":10000,
                        "min":1
                    },
                    "mem":{
                        "max":10000,
                        "min":1
                    },
                    "name":"mysql",
                    "count":1,
                    "device_class":[

                    ],
                    "storage_spec":[
                        {
                            "type":"",
                            "max_size":100000000,
                            "min_size":1,
                            "mount_point":""
                        }
                    ]
                }
            }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __get_old_ins_info(self, ip: str) -> dict:
        """
        获取ip相关的老实例信息
        ports/slave_ip/db_version
        """
        ports = []
        slave_ip = ""
        db_version = ""
        clusters = query_cluster_by_hosts([ip])
        if len(clusters) != 0:
            ports = clusters[0]["ports"]
            db_version = clusters[0]["major_version"]

            storages = [{"ip": ip, "port": ports[0]}]
            storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
            slave_objs = storage_objs.get(instance_inner_role=InstanceInnerRole.MASTER).as_ejector.get().receiver
            slave_ip = slave_objs.machine.ip
        return {
            "ports": ports,
            "slave_ip": slave_ip,
            "db_version": db_version,
        }

    def __pre_check(self, data: dict) -> dict:
        """
        前置检查+数据处理
        将rule转换成以ip为维度

        检查：
            - 1. ip:port 是否已被使用、冲突
            - 2. 同一ip的版本是否一致（如果已经安装过实例，还需要跟已安装实例的版本做对比）
            # - 3. (非强制，优化)同一ip新安装的实例，密码是否一样？如果一样，安装任务可以合并
            - 4. 一个master是否有多个slave ip的情况

        数据处理：
            - 1. db_version -> ips 介质下发
            - 2. ip -> new_ports/ ip -> old_ports 新安装的端口，已经安装的端口。 用于dbmon安装
            - 3. master:port -> slave:port 主从复制
            - 4. all_ip: 插件安装
            # - 5. 密码、database 如果同一ip的这两个一样，则可以合并安装

        """
        master_ip_list = []
        old_ports_dict = defaultdict(list)  # ip对应历史已安装端口
        new_ports_dict = defaultdict(list)  # ip对应需要新安装端口
        db_version_dict = {}  # ip对应的版本
        repl_dict = {}  # ip主从复制关系
        ip_install_dict = defaultdict(list)

        for rule in data["infos"]:
            master_ip = rule["backend_group"]["master"]["ip"]
            slave_ip = rule["backend_group"]["slave"]["ip"]
            port = rule["port"]
            db_version = rule["db_version"]

            if master_ip not in master_ip_list:
                master_ip_list.append(master_ip)
                db_version_dict[master_ip] = db_version
                repl_dict[master_ip] = slave_ip

                machine_old_info = self.__get_old_ins_info(master_ip)
                if len(machine_old_info["ports"]):
                    old_ports_dict[master_ip] = machine_old_info["ports"]
                    if machine_old_info["slave_ip"] != slave_ip:
                        raise Exception(master_ip + " old slave is: " + machine_old_info["slave_ip"])
                    if machine_old_info["db_version"] != db_version:
                        raise Exception(master_ip + " old db_version is: " + machine_old_info["db_version"])

            if db_version != db_version_dict[master_ip]:
                raise Exception(master_ip + " have more db_version")
            if slave_ip != repl_dict[master_ip]:
                raise Exception("master have more slave")
            if port in new_ports_dict[master_ip]:
                raise Exception(master_ip + " port have conflict: " + str(port))
            if port in old_ports_dict[master_ip]:
                raise Exception(master_ip + " port is exists: " + str(port))
            new_ports_dict[master_ip].append(port)
            ip_install_dict[master_ip].append(rule)

        return {
            "master_ip_list": master_ip_list,
            "new_ports_dict": dict(new_ports_dict),
            "old_ports_dict": dict(old_ports_dict),
            "db_version_dict": db_version_dict,
            "repl_dict": repl_dict,
            "ip_install_dict": dict(ip_install_dict),
        }

    def deploy_redis_instance_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        info = self.__pre_check(self.data)
        app = AppCache.get_app_attr(self.data["bk_biz_id"], "db_app_abbr")
        app_name = AppCache.get_app_attr(self.data["bk_biz_id"], "bk_biz_name")
        cache_backup_mode = get_cache_backup_mode(self.data["bk_biz_id"], 0)

        sub_pipelines = []
        for master_ip in info["ip_install_dict"]:
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

            old_ports = info["old_ports_dict"][master_ip]
            db_version = info["db_version_dict"][master_ip]
            slave_ip = info["repl_dict"][master_ip]
            all_ip = [master_ip, slave_ip]

            spec_id = info["ip_install_dict"][master_ip][0]["resource_spec"]["id"]
            spec_config = info["ip_install_dict"][master_ip][0]["resource_spec"]

            # 初始化配置
            act_kwargs.cluster["db_version"] = db_version
            act_kwargs.cluster["cluster_type"] = self.data["cluster_type"]
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            # 下发介质包
            trans_files = GetFileList(db_type=DBType.Redis)
            act_kwargs.file_list = trans_files.redis_cluster_apply_backend(db_version)
            act_kwargs.exec_ip = all_ip
            sub_pipeline.add_act(
                act_name=_("Redis-{}-下发介质包").format(all_ip),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            if len(old_ports) == 0:
                "如果之前没有安装过实例，则需要做初始化和安装工具操作"
                act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("Redis-{}-初始化机器").format(all_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                acts_list = []
                acts_list.append(
                    {
                        "act_name": _("Redis-{}-安装backup-client工具").format(all_ip),
                        "act_component_code": DownloadBackupClientComponent.code,
                        "kwargs": asdict(
                            DownloadBackupClientKwargs(
                                bk_cloud_id=self.data["bk_cloud_id"],
                                bk_biz_id=int(self.data["bk_biz_id"]),
                                download_host_list=all_ip,
                            ),
                        ),
                    }
                )
                for plugin_name in DEPENDENCIES_PLUGINS:
                    acts_list.append(
                        {
                            "act_name": _("安装[{}]插件".format(plugin_name)),
                            "act_component_code": InstallNodemanPluginServiceComponent.code,
                            "kwargs": asdict(
                                InstallNodemanPluginKwargs(
                                    bk_cloud_id=int(self.data["bk_cloud_id"]), ips=all_ip, plugin_name=plugin_name
                                )
                            ),
                        }
                    )
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 按照端口安装Redis实例
            acts_list = []
            replica_pairs = []
            master_servers = []
            slave_servers = []
            for rule in info["ip_install_dict"][master_ip]:
                act_kwargs.cluster["exec_ip"] = master_ip
                #  集群申请单据时，下面参数需要从param中获取，不能从已有配置中获取
                act_kwargs.cluster["requirepass"] = rule["redis_pwd"]
                act_kwargs.cluster["databases"] = rule["databases"]
                act_kwargs.cluster["maxmemory"] = rule["maxmemory"]
                act_kwargs.cluster["cluster_type"] = self.data["cluster_type"]
                act_kwargs.cluster["db_version"] = db_version
                act_kwargs.cluster["ports"] = [rule["port"]]
                act_kwargs.get_redis_payload_func = RedisActPayload.get_install_redis_apply_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("Redis-{}:{}-安装实例").format(master_ip, rule["port"]),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )

                act_kwargs.cluster["exec_ip"] = info["repl_dict"][master_ip]
                acts_list.append(
                    {
                        "act_name": _("Redis-{}:{}-安装实例").format(info["repl_dict"][master_ip], rule["port"]),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )

                replica_pairs.append(
                    {
                        "master_ip": master_ip,
                        "master_port": rule["port"],
                        "master_auth": rule["redis_pwd"],
                        "slave_ip": info["repl_dict"][master_ip],
                        "slave_port": rule["port"],
                        "slave_password": rule["redis_pwd"],
                    }
                )
                master_servers.append(
                    {
                        "app": app,
                        "app_name": app_name,
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": int(self.data["bk_cloud_id"]),
                        "server_ip": master_ip,
                        "server_ports": [rule["port"]],
                        "meta_role": InstanceRole.REDIS_MASTER.value,
                        "cluster_name": rule["cluster_name"],
                        "cluster_type": self.data["cluster_type"],
                        "cluster_domain": rule["domain_name"],
                        "server_shards": {},
                        "cache_backup_mode": cache_backup_mode,
                    }
                )
                slave_servers.append(
                    {
                        "app": app,
                        "app_name": app_name,
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": int(self.data["bk_cloud_id"]),
                        "server_ip": info["repl_dict"][master_ip],
                        "server_ports": [rule["port"]],
                        "meta_role": InstanceRole.REDIS_SLAVE.value,
                        "cluster_name": rule["cluster_name"],
                        "cluster_type": self.data["cluster_type"],
                        "cluster_domain": rule["domain_name"],
                        "server_shards": {},
                        "cache_backup_mode": cache_backup_mode,
                    }
                )

            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 写入元数据
            act_kwargs.cluster["spec_id"] = spec_id
            act_kwargs.cluster["spec_config"] = spec_config
            act_kwargs.cluster["ports"] = info["new_ports_dict"][master_ip]
            act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_install_append.__name__
            act_kwargs.cluster["master_ip"] = master_ip
            act_kwargs.cluster["slave_ip"] = slave_ip
            sub_pipeline.add_act(
                act_name=_("Redis-{}-写入元数据").format(master_ip),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 建立主从关系
            act_kwargs.cluster["replica_pairs"] = replica_pairs
            act_kwargs.exec_ip = master_ip
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_init_batch_replicate.__name__
            sub_pipeline.add_act(
                act_name=_("建立主从关系-{}-{}".format(master_ip, slave_ip)),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 建立主从元数据
            act_kwargs.cluster = {
                "bacth_pairs": replica_pairs,
                "created_by": self.data["created_by"],
                "meta_func_name": RedisDBMeta.replicaof_ins.__name__,
            }
            sub_pipeline.add_act(
                act_name=_("redis建立主从 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )
            acts_list = []
            for rule in info["ip_install_dict"][master_ip]:
                act_kwargs.cluster = {
                    "bk_biz_id": self.data["bk_biz_id"],
                    "bk_cloud_id": self.data["bk_cloud_id"],
                    "cluster_name": rule["cluster_name"],
                    "cluster_alias": rule["cluster_alias"],
                    "db_version": rule["db_version"],
                    "immute_domain": rule["domain_name"],
                    "master_ip": master_ip,
                    "slave_ip": slave_ip,
                    "port": rule["port"],
                    "created_by": self.data["created_by"],
                    "region": rule.get("city_code", ""),
                    "meta_func_name": RedisDBMeta.redis_instance.__name__,
                    "disaster_tolerance_level": rule.get("disaster_tolerance_level", AffinityEnum.CROS_SUBZONE),
                }
                acts_list.append(
                    {
                        "act_name": _("{}-主从实例集群元数据").format(rule["domain_name"]),
                        "act_component_code": RedisDBMetaComponent.code,
                        "kwargs": asdict(act_kwargs),
                    },
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 写config，需要在写集群元数据后面
            acts_list = []
            for rule in info["ip_install_dict"][master_ip]:
                act_kwargs.cluster = {
                    "conf": {
                        "maxmemory": str(rule["maxmemory"]),
                        "databases": str(rule["databases"]),
                    },
                    "pwd_conf": {
                        "redis_pwd": str(rule["redis_pwd"]),
                    },
                    "db_version": rule["db_version"],
                    "domain_name": rule["domain_name"],
                }
                if (
                    self.data["cluster_type"] == ClusterType.TendisRedisInstance.value
                    and rule["db_version"] != RedisVersion.Redis20.value
                ):
                    act_kwargs.cluster["conf"]["cluster-enabled"] = ClusterStatus.REDIS_CLUSTER_NO

                act_kwargs.get_redis_payload_func = RedisActPayload.set_redis_config.__name__
                acts_list.append(
                    {
                        "act_name": _("{}-回写集群配置[Redis]").format(rule["domain_name"]),
                        "act_component_code": RedisConfigComponent.code,
                        "kwargs": asdict(act_kwargs),
                    },
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 添加域名
            acts_list = []
            for rule in info["ip_install_dict"][master_ip]:
                dns_kwargs = DnsKwargs(
                    dns_op_type=DnsOpType.CREATE,
                    add_domain_name=rule["domain_name"],
                    dns_op_exec_port=rule["port"],
                )
                act_kwargs.exec_ip = master_ip
                acts_list.append(
                    {
                        "act_name": _("主注册域名"),
                        "act_component_code": RedisDnsManageComponent.code,
                        "kwargs": {**asdict(act_kwargs), **asdict(dns_kwargs)},
                    }
                )

                domain_split = str.split(rule["domain_name"], ".")
                domain_split[0] = domain_split[0] + "-slave"
                slave_domain = ".".join(domain_split)
                dns_kwargs = DnsKwargs(
                    dns_op_type=DnsOpType.CREATE,
                    add_domain_name=slave_domain,
                    dns_op_exec_port=rule["port"],
                )
                act_kwargs.exec_ip = info["repl_dict"][master_ip]
                acts_list.append(
                    {
                        "act_name": _("从注册域名"),
                        "act_component_code": RedisDnsManageComponent.code,
                        "kwargs": {**asdict(act_kwargs), **asdict(dns_kwargs)},
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 部署bkdbmon
            acts_list = []
            for ip in [master_ip, slave_ip]:
                act_kwargs.exec_ip = ip
                act_kwargs.cluster = {"ip": ip}
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
                acts_list.append(
                    {
                        "act_name": _("{}-安装bkdbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("Redis主从安装-{}").format(master_ip)))
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
