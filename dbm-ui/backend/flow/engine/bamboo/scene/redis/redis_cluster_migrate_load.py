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

from backend.configuration.constants import AffinityEnum, DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.machine_type import MachineType
from backend.db_meta.models import AppCache, Spec
from backend.flow.consts import ClusterStatus, InstanceStatus
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs.reupload_old_backup_records import (
    RedisReuploadOldBackupRecordsAtomJob,
)
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
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
        """
        处理集群参数
        返回需要的处理后的数据格式
        """
        master_ips = []
        slave_ips = []
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
            master_ips.append(mip)
            slave_ips.append(sip)
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
            "ip_port_dict": dict(ip_port_dict),
            "proxy_ips": proxy_ips,
            "proxy_port": proxy_port,
            "proxy_spec_id": proxy_spec_id,
            "proxy_spec_config": Spec.objects.get(spec_id=proxy_spec_id).get_spec_info(),
            "master_ips": list(set(master_ips)),
            "slave_ips": list(set(slave_ips)),
            "server_shards": dict(server_shards),
        }

    def redis_cluster_migrate_load_flow(self):
        """
        if dbha:
            只更新元数据
        1、写元数据（这里地方挪了cc）
            1.1 proxy元数据
            1.2 redis元数据
            1.3 集群元数据
        2、写配置文件
        3、if 安装dbmon
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

            if ins_status == InstanceStatus.RUNNING:
                acts_list = []
                for redis_ip in cluster["master_ips"] + cluster["slave_ips"]:
                    act_kwargs.cluster["meta_update_ip"] = redis_ip
                    act_kwargs.cluster["meta_update_ports"] = cluster["ip_port_dict"][redis_ip]
                    act_kwargs.cluster["meta_update_status"] = InstanceStatus.RUNNING
                    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.instances_status_update.__name__
                    acts_list.append(
                        {
                            "act_name": _("{}-更新redis状态".format(redis_ip)),
                            "act_component_code": RedisDBMetaComponent.code,
                            "kwargs": asdict(act_kwargs),
                        },
                    )
                for proxy_ip in cluster["proxy_ips"]:
                    act_kwargs.cluster["meta_update_ip"] = proxy_ip
                    act_kwargs.cluster["meta_update_ports"] = [cluster["proxy_port"]]
                    act_kwargs.cluster["meta_update_status"] = InstanceStatus.RUNNING
                    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.instances_status_update.__name__
                    acts_list.append(
                        {
                            "act_name": _("{}-更新proxy状态".format(proxy_ip)),
                            "act_component_code": RedisDBMetaComponent.code,
                            "kwargs": asdict(act_kwargs),
                        },
                    )
                sub_pipeline.add_parallel_acts(acts_list)
                sub_pipelines.append(
                    sub_pipeline.build_sub_process(
                        sub_name=_("{}更新状态子任务").format(params["clusterinfo"]["immute_domain"])
                    )
                )
                continue

            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            # 下发介质包
            all_ips = cluster["proxy_ips"] + cluster["master_ips"] + cluster["slave_ips"]
            trans_files = GetFileList(db_type=DBType.Redis)
            act_kwargs.file_list = trans_files.redis_dbmon()
            act_kwargs.exec_ip = all_ips
            sub_pipeline.add_act(
                act_name=_("下发介质包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            sub_pipeline.add_act(
                act_name=_("安装backup-client工具").format(all_ips),
                act_component_code=DownloadBackupClientComponent.code,
                kwargs=asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=self.data["bk_cloud_id"],
                        bk_biz_id=int(self.data["bk_biz_id"]),
                        download_host_list=all_ips,
                    ),
                ),
            )

            # ./dbactuator_redis --atom-job-list="sys_init"
            act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
            sub_pipeline.add_act(
                act_name=_("初始化机器"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # proxy 相关操作
            act_kwargs.cluster = copy.deepcopy(cluster_tpl)
            act_kwargs.cluster["machine_type"] = proxy_type
            act_kwargs.cluster["cluster_type"] = params["clusterinfo"]["cluster_type"]
            # proxy元数据 - 批量写入
            act_kwargs.cluster["ins_status"] = ins_status
            act_kwargs.cluster["new_proxy_ips"] = cluster["proxy_ips"]
            act_kwargs.cluster["port"] = cluster["proxy_port"]
            act_kwargs.cluster["spec_id"] = cluster["proxy_spec_id"]
            act_kwargs.cluster["spec_config"] = cluster["proxy_spec_config"]
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

            # redis 相关操作
            # 写入元数据,后面实例的规格可能不一样，所以不能批量写入
            acts_list = []
            for redis_ip in cluster["master_ips"] + cluster["slave_ips"]:
                act_kwargs.cluster = copy.deepcopy(cluster_tpl)
                act_kwargs.cluster["cluster_type"] = params["clusterinfo"]["cluster_type"]
                act_kwargs.cluster["ins_status"] = ins_status

                act_kwargs.cluster[cluster["role_dict"][redis_ip]] = [redis_ip]
                act_kwargs.cluster["ports"] = cluster["ip_port_dict"][redis_ip]
                act_kwargs.cluster["spec_id"] = cluster["spec_id_dict"][redis_ip]
                act_kwargs.cluster["spec_config"] = Spec.objects.get(
                    spec_id=cluster["spec_id_dict"][redis_ip]
                ).get_spec_info()
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
            for redis_ip in cluster["master_ips"]:
                act_kwargs.cluster["servers"] = [
                    {
                        "app": app,
                        "app_name": app_name,
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": int(self.data["bk_cloud_id"]),
                        "server_ip": redis_ip,
                        "server_ports": cluster["ip_port_dict"][redis_ip],
                        "meta_role": InstanceRole.REDIS_MASTER.value,
                        "cluster_domain": params["clusterinfo"]["immute_domain"],
                        "cluster_name": params["clusterinfo"]["name"],
                        "cluster_type": params["clusterinfo"]["cluster_type"],
                        "server_shards": cluster["server_shards"][redis_ip],
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
            for redis_ip in cluster["slave_ips"]:
                act_kwargs.cluster["servers"] = [
                    {
                        "app": app,
                        "app_name": app_name,
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": int(self.data["bk_cloud_id"]),
                        "server_ip": redis_ip,
                        "server_ports": cluster["ip_port_dict"][redis_ip],
                        "meta_role": InstanceRole.REDIS_SLAVE.value,
                        "cluster_domain": params["clusterinfo"]["immute_domain"],
                        "cluster_name": params["clusterinfo"]["name"],
                        "cluster_type": params["clusterinfo"]["cluster_type"],
                        "server_shards": cluster["server_shards"][redis_ip],
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
            # 历史备份记录上报
            upload_backup_sub_pipelines = []
            for redis_ip in cluster["slave_ips"]:
                upload_backup_sub_pipelines.append(
                    RedisReuploadOldBackupRecordsAtomJob(
                        self.root_id,
                        self.data,
                        act_kwargs,
                        {
                            "bk_biz_id": self.data["bk_biz_id"],
                            "bk_cloud_id": self.data["bk_cloud_id"],
                            "server_ip": redis_ip,
                            "server_ports": cluster["ip_port_dict"][redis_ip],
                            "cluster_domain": params["clusterinfo"]["immute_domain"],
                            "cluster_type": params["clusterinfo"]["cluster_type"],
                            "meta_role": InstanceRole.REDIS_SLAVE.value,
                            "server_shards": cluster["server_shards"][redis_ip],
                        },
                    )
                )
            sub_pipeline.add_parallel_sub_pipeline(upload_backup_sub_pipelines)

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
                "disaster_tolerance_level": self.data.get("disaster_tolerance_level", AffinityEnum.CROS_SUBZONE),
            }
            sub_pipeline.add_act(
                act_name=_("建立集群 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )

            db_admin = {"db_type": DBType.Redis.value, "users": str.split(self.data["nosqldbas"], ",")}
            act_kwargs.cluster = {
                "db_admins": [db_admin],
                "meta_func_name": RedisDBMeta.update_nosql_dba.__name__,
            }
            sub_pipeline.add_act(
                act_name=_("更新业务NOSQL DBA"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )

            # clb、北极星需要写元数据
            if len(params["entry"]["clb"]) != 0:
                act_kwargs.cluster = params["entry"]["clb"]
                act_kwargs.cluster["bk_cloud_id"] = self.data["bk_cloud_id"]
                act_kwargs.cluster["immute_domain"] = params["clusterinfo"]["immute_domain"]
                act_kwargs.cluster["created_by"] = self.data["created_by"]
                act_kwargs.cluster["meta_func_name"] = RedisDBMeta.add_clb_domain.__name__
                sub_pipeline.add_act(
                    act_name=_("clb元数据写入"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
                )

            if len(params["entry"]["polairs"]) != 0:
                act_kwargs.cluster = params["entry"]["polairs"]
                act_kwargs.cluster["bk_cloud_id"] = self.data["bk_cloud_id"]
                act_kwargs.cluster["immute_domain"] = params["clusterinfo"]["immute_domain"]
                act_kwargs.cluster["created_by"] = self.data["created_by"]
                act_kwargs.cluster["meta_func_name"] = RedisDBMeta.add_polairs_domain.__name__
                sub_pipeline.add_act(
                    act_name=_("polairs元数据写入"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
                )

            # 为了把密码写进密码服务里去，写配置需要放在最后来做了
            # 写配置文件 begin
            acts_list = []
            proxy_pwd = ""
            redis_password = ""
            # 处理配置
            if "requirepass" in params["redis_config"]:
                del params["redis_config"]["requirepass"]
            if "redis_password" in params["proxy_config"]:
                redis_password = params["proxy_config"].pop("redis_password")
            if "password" in params["proxy_config"]:
                proxy_pwd = params["proxy_config"].pop("password")
            params["proxy_config"]["port"] = str(cluster["proxy_port"])

            act_kwargs.cluster = {
                "conf": params["redis_config"],
                "backup_config": params["backup_config"],
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
                "conf": params["proxy_config"],
                "pwd_conf": {
                    "proxy_pwd": proxy_pwd,
                    "proxy_admin_pwd": proxy_pwd,
                    "redis_pwd": redis_password,
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

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("{}迁移子任务").format(params["clusterinfo"]["immute_domain"]))
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
