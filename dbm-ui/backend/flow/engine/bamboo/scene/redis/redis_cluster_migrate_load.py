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
import copy
import logging.config
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.machine_type import MachineType
from backend.db_meta.models import AppCache
from backend.flow.consts import (
    DEFAULT_REDIS_START_PORT,
    DEFAULT_TWEMPROXY_SEG_TOTOL_NUM,
    ClusterStatus,
    InstanceStatus,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode

logger = logging.getLogger("flow")


class RedisClusterMigrateLoadFlow(object):
    """
    redis清档
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __dispose_cluster_params(self, cluster_info: dict) -> dict:
        master_list = []
        slave_list = []
        spec_id_dict = {}
        seg_dict = {}
        role_dict = {}
        ip_port_dict = defaultdict(list)
        server_shards = defaultdict(dict)
        repl_list = []
        proxy_ips = [proxy["ip"] for proxy in cluster_info["proxies"]]
        proxy_spec_id = cluster_info["proxies"][0]["spec_id"]

        proxy_port = cluster_info["proxies"][0]["port"]
        for backend in cluster_info["backends"]:
            mip = backend["nodes"]["master"]["ip"]
            sip = backend["nodes"]["slave"]["ip"]
            mport = backend["nodes"]["master"]["port"]
            sport = backend["nodes"]["slave"]["port"]
            master_list.append(mip)
            slave_list.append(sip)
            ip_port_dict[mip].append(mport)
            ip_port_dict[sip].append(sport)
            spec_id_dict[mip] = backend["nodes"]["master"]["spec_id"]
            spec_id_dict[sip] = backend["nodes"]["slave"]["spec_id"]
            role_dict[mip] = "new_master_ips"
            role_dict[sip] = "new_slave_ips"
            seg_dict["{}:{}".format(mip, mport)] = backend["shard"]
            server_shards[mip]["{}:{}".format(mip, mport)] = backend["shard"]
            server_shards[sip]["{}:{}".format(sip, mport)] = backend["shard"]
            repl_list.append({"master_ip": mip, "master_port": int(mport), "slave_ip": sip, "slave_port": int(sport)})

        return {
            "spec_id_dict": spec_id_dict,
            "seg_dict": seg_dict,
            "repl_list": repl_list,
            "role_dict": role_dict,
            "ip_prot_dict": dict(ip_port_dict),
            "proxy_ips": proxy_ips,
            "proxy_port": proxy_port,
            "proxy_spec_id": proxy_spec_id,
            "master_list": master_list,
            "slave_list": slave_list,
            "server_shards": dict(server_shards),
        }

    def redis_cluster_migrate_load_flow(self):
        """
        1、写元数据（这里地方挪了cc）
            1.1 proxy元数据
            1.2 redis元数据
        2、写配置文件
        3、if 安装dbmon
        4、if 接入dbha
        """
        app = AppCache.get_app_attr(self.data["bk_biz_id"], "db_app_abbr")
        app_name = AppCache.get_app_attr(self.data["bk_biz_id"], "bk_biz_name")
        ins_status = InstanceStatus.UNAVAILABLE
        if self.data["migrate_ctl"]["dbha"]:
            ins_status = InstanceStatus.RUNNING
        # 暂时只支持twemproxy的迁移
        proxy_type = MachineType.TWEMPROXY.value
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.is_update_trans_data = True
        cluster_tpl = {
            "created_by": self.data["created_by"],
            "bk_biz_id": self.data["bk_biz_id"],
            "bk_cloud_id": self.data["bk_cloud_id"],
        }

        sub_pipelines = []
        for params in self.data["clusters"]:
            cluster = self.__dispose_cluster_params(params)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            act_kwargs.cluster = {
                "cluster_type": params["clusterinfo"]["cluster_type"],
                "db_version": params["clusterinfo"]["db_version"],
            }
            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            # 下发介质包
            trans_files = GetFileList(db_type=DBType.Redis)
            act_kwargs.file_list = trans_files.redis_dbmon()
            act_kwargs.exec_ip = cluster["proxy_ips"] + cluster["master_list"] + cluster["slave_list"]
            sub_pipeline.add_act(
                act_name=_("下发介质包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 写配置文件 begin
            acts_list = []
            act_kwargs.cluster = {
                "conf": {
                    "maxmemory": str(params["config"]["maxmemory"]),
                    "databases": str(params["config"]["databases"]),
                    "requirepass": params["config"]["requirepass"],
                },
                "db_version": params["clusterinfo"]["db_version"],
                "domain_name": params["clusterinfo"]["immute_domain"],
            }
            if params["clusterinfo"]["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
                act_kwargs.cluster["conf"]["cluster-enabled"] = ClusterStatus.REDIS_CLUSTER_NO

            act_kwargs.get_redis_payload_func = RedisActPayload.set_redis_config.__name__
            acts_list.append(
                {
                    "act_name": _("回写集群配置[Redis]"),
                    "act_component_code": RedisConfigComponent.code,
                    "kwargs": asdict(act_kwargs),
                },
            )

            act_kwargs.cluster = {
                "conf": {
                    "password": params["config"]["proxypass"],
                    "redis_password": params["config"]["requirepass"],
                    "port": str(cluster["proxy_port"]),
                },
                "domain_name": params["clusterinfo"]["immute_domain"],
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.set_proxy_config.__name__
            acts_list.append(
                {
                    "act_name": _("回写集群配置[Twemproxy]"),
                    "act_component_code": RedisConfigComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
            sub_pipeline.add_parallel_acts(acts_list)
            # 写配置文件 end

            # sub_ins_pipelines = []
            # proxy 相关操作
            # sub_proxy_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            act_kwargs.cluster = copy.deepcopy(cluster_tpl)
            act_kwargs.cluster["machine_type"] = proxy_type
            act_kwargs.cluster["cluster_type"] = params["clusterinfo"]["cluster_type"]
            # proxy元数据 - 批量写入
            act_kwargs.cluster["ins_status"] = ins_status
            act_kwargs.cluster["new_proxy_ips"] = cluster["proxy_ips"]
            act_kwargs.cluster["port"] = cluster["proxy_port"]
            act_kwargs.cluster["spec_id"] = cluster["proxy_spec_id"]
            act_kwargs.cluster["spec_config"] = {}
            act_kwargs.cluster["meta_func_name"] = RedisDBMeta.proxy_install.__name__
            sub_pipeline.add_act(
                act_name=_("Proxy写入元数据"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # proxy 安装dbmon
            acts_list = []
            for proxy_ip in cluster["proxy_ips"]:
                act_kwargs.cluster["servers"] = [
                    {
                        "app": app,
                        "app_name": app_name,
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": int(self.data["bk_cloud_id"]),
                        "server_ip": proxy_ip,
                        "server_ports": [cluster["proxy_port"]],
                        "meta_role": proxy_type,
                        "cluster_domain": params["clusterinfo"]["immute_domain"],
                        "cluster_name": params["clusterinfo"]["name"],
                        "cluster_type": params["clusterinfo"]["cluster_type"],
                    }
                ]
                act_kwargs.exec_ip = proxy_ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__

                acts_list.append(
                    {
                        "act_name": _("Proxy{}-安装监控").format(proxy_ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    },
                )
            sub_pipeline.add_parallel_acts(acts_list)
            # sub_ins_pipelines.append(sub_proxy_pipeline.build_sub_process(sub_name=_("proxy相关子任务")))

            # redis 相关操作
            # sub_redis_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            # 写入元数据,后面实例的规格可能不一样，所以不能批量写入
            # TODO 实例状态由参数传过来，需要修改
            acts_list = []
            for redis_ip in cluster["master_list"] + cluster["slave_list"]:
                act_kwargs.cluster = copy.deepcopy(cluster_tpl)
                act_kwargs.cluster["cluster_type"] = params["clusterinfo"]["cluster_type"]
                act_kwargs.cluster["ins_status"] = ins_status

                act_kwargs.cluster[cluster["role_dict"][redis_ip]] = [redis_ip]
                act_kwargs.cluster["ports"] = cluster["ip_prot_dict"][redis_ip]
                act_kwargs.cluster["spec_id"] = cluster["spec_id_dict"][redis_ip]
                act_kwargs.cluster["spec_config"] = {}
                act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_install.__name__
                acts_list.append(
                    {
                        "act_name": _("Redis-{}-写入元数据").format(redis_ip),
                        "act_component_code": RedisDBMetaComponent.code,
                        "kwargs": asdict(act_kwargs),
                    },
                )
            sub_pipeline.add_parallel_acts(acts_list)
            # 安装dbmon
            acts_list = []
            for redis_ip in cluster["master_list"]:
                act_kwargs.cluster["servers"] = [
                    {
                        "app": app,
                        "app_name": app_name,
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": int(self.data["bk_cloud_id"]),
                        "server_ip": redis_ip,
                        "server_ports": cluster["ip_prot_dict"][redis_ip],
                        "meta_role": InstanceRole.REDIS_MASTER.value,
                        "cluster_domain": params["clusterinfo"]["immute_domain"],
                        "cluster_name": params["clusterinfo"]["name"],
                        "cluster_type": params["clusterinfo"]["cluster_type"],
                        "server_shards": cluster["server_shards"],
                        "cache_backup_mode": get_cache_backup_mode(self.data["bk_biz_id"], 0),
                    }
                ]
                act_kwargs.exec_ip = redis_ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                acts_list.append(
                    {
                        "act_name": _("Redis{}-安装监控").format(redis_ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    },
                )
            for redis_ip in cluster["slave_list"]:
                act_kwargs.cluster["servers"] = [
                    {
                        "app": app,
                        "app_name": app_name,
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": int(self.data["bk_cloud_id"]),
                        "server_ip": redis_ip,
                        "server_ports": cluster["ip_prot_dict"][redis_ip],
                        "meta_role": InstanceRole.REDIS_SLAVE.value,
                        "cluster_domain": params["clusterinfo"]["immute_domain"],
                        "cluster_name": params["clusterinfo"]["name"],
                        "cluster_type": params["clusterinfo"]["cluster_type"],
                        "server_shards": cluster["server_shards"],
                        "cache_backup_mode": get_cache_backup_mode(self.data["bk_biz_id"], 0),
                    }
                ]
                act_kwargs.exec_ip = redis_ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                acts_list.append(
                    {
                        "act_name": _("Redis{}-安装监控").format(redis_ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    },
                )
            sub_pipeline.add_parallel_acts(acts_list)
            # 建立主从关系
            act_kwargs.cluster = {
                "repl": cluster["repl_list"],
                "created_by": self.data["created_by"],
                "meta_func_name": RedisDBMeta.replicaof_link.__name__,
            }
            sub_pipeline.add_act(
                act_name=_("redis建立主从 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )

            # 建立集群关系
            servers = []
            for ins, seg in cluster["seg_dict"].items():
                servers.append("{} {} {} {}".format(ins, params["clusterinfo"]["name"], seg, 1))
            act_kwargs.cluster = {
                "new_proxy_ips": cluster["proxy_ips"],
                "servers": servers,
                "proxy_port": cluster["proxy_port"],
                "cluster_type": params["clusterinfo"]["cluster_type"],
                "bk_biz_id": self.data["bk_biz_id"],
                "bk_cloud_id": self.data["bk_cloud_id"],
                "cluster_name": params["clusterinfo"]["name"],
                "cluster_alias": params["clusterinfo"]["alias"],
                "db_version": params["clusterinfo"]["db_version"],
                "immute_domain": params["clusterinfo"]["immute_domain"],
                "created_by": self.data["created_by"],
                "region": params["clusterinfo"]["region"],
                "meta_func_name": RedisDBMeta.redis_make_cluster.__name__,
            }
            sub_pipeline.add_act(
                act_name=_("建立集群 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )
            # sub_ins_pipelines.append(sub_redis_pipeline.build_sub_process(sub_name=_("redis相关子任务")))

            # clb、北极星需要写元数据
            # sub_access_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            if len(params["entry"]["clb"]) != 0:
                act_kwargs.cluster = params["entry"]["clb"]
                act_kwargs.cluster["bk_cloud_id"] = self.data["bk_cloud_id"]
                act_kwargs.cluster["immute_domain"] = params["clusterinfo"]["immute_domain"]
                act_kwargs.cluster["meta_func_name"] = RedisDBMeta.add_clb_domain.__name__
                sub_pipeline.add_act(
                    act_name=_("clb元数据写入"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
                )

            if len(params["entry"]["polairs"]) != 0:
                act_kwargs.cluster = params["entry"]["polairs"]
                act_kwargs.cluster["bk_cloud_id"] = self.data["bk_cloud_id"]
                act_kwargs.cluster["immute_domain"] = params["clusterinfo"]["immute_domain"]
                act_kwargs.cluster["meta_func_name"] = RedisDBMeta.add_polairs_domain.__name__
                sub_pipeline.add_act(
                    act_name=_("polairs元数据写入"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
                )
            # sub_ins_pipelines.append(sub_access_pipeline.build_sub_process(sub_name=_("接入层相关子任务")))
            # sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_ins_pipelines)
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("{}迁移子任务").format(params["clusterinfo"]["immute_domain"]))
            )
            print("0000" * 10, params["clusterinfo"]["immute_domain"])
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
