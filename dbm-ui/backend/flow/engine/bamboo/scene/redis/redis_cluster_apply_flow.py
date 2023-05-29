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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.machine_type import MachineType
from backend.db_meta.models import AppCache
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import DEFAULT_REDIS_START_PORT, ClusterStatus, DBConstNumEnum, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.get_redis_resource import GetRedisResourceComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, DnsKwargs, RedisApplyContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisClusterApplyFlow(object):
    """
    构建redis集群申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def deploy_redis_cluster_flow(self):
        """
        部署Redis集群
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = RedisApplyContext.__name__
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {}
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        app = AppCache.get_app_attr(self.data["bk_biz_id"], "db_app_abbr")
        app_name = AppCache.get_app_attr(self.data["bk_biz_id"], "bk_biz_name")

        # 获取机器资源 done
        redis_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetRedisResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 合并请求、上下文配置，并初始化config配置 done
        act_kwargs.cluster = {"cluster_type": self.data["cluster_type"]}
        redis_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # TODO 增加一个机器检查的节点

        acts_list = []
        # proxy机器所需介质包
        act_kwargs.file_list = trans_files.redis_cluster_apply_proxy()
        act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_new_proxy_ips_var_name()
        acts_list.append(
            {
                "act_name": _("[proxy]下发介质包"),
                "act_component_code": TransFileComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )

        act_kwargs.file_list = trans_files.redis_cluster_apply_backend(db_version=self.data["db_version"])
        act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_new_redis_ips_var_name()
        acts_list.append(
            {
                "act_name": _("[redis]下发介质包"),
                "act_component_code": TransFileComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
        redis_pipeline.add_parallel_acts(acts_list)

        # ./dbactuator_redis --atom-job-list="sys_init"
        act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_new_all_ips_var_name()
        act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
        redis_pipeline.add_act(
            act_name=_("初始化机器"), act_component_code=ExecuteDBActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 并发安装redis
        acts_list = []
        for ip_index in range(0, self.data["group_num"] * DBConstNumEnum.REDIS_ROLE_NUM):
            act_kwargs.ip_index = ip_index
            act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_new_redis_ips_var_name()
            act_kwargs.get_redis_payload_func = RedisActPayload.get_install_redis_payload.__name__
            acts_list.append(
                {
                    "act_name": _("安装Redis实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        act_kwargs.ip_index = None
        redis_pipeline.add_parallel_acts(acts_list=acts_list)
        act_kwargs.cluster = {"meta_func_name": RedisDBMeta.redis_install.__name__}
        redis_pipeline.add_act(
            act_name=_("redis实例安装 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 建立主从关系
        act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_new_exec_ip_name()
        act_kwargs.get_redis_payload_func = RedisActPayload.get_slaveof_redis_payload.__name__
        redis_pipeline.add_act(
            act_name=_("建立主从关系"), act_component_code=ExecuteDBActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.cluster = {"meta_func_name": RedisDBMeta.replicaof.__name__}
        redis_pipeline.add_act(
            act_name=_("redis建立主从 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        ins_num = self.data["shard_num"] // self.data["group_num"]
        ports = list(map(lambda i: i + DEFAULT_REDIS_START_PORT, range(ins_num)))

        # 并发部署bkdbmon
        acts_list = []
        for ip_index in range(0, self.data["group_num"]):
            act_kwargs.ip_index = ip_index
            act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_redis_master_var_name()
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
            act_kwargs.cluster = {
                "servers": [
                    {
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": self.data["bk_cloud_id"],
                        "server_ports": ports,
                        "meta_role": InstanceRole.REDIS_MASTER.value,
                        "cluster_domain": self.data["domain_name"],
                        "app": app,
                        "app_name": app_name,
                        "cluster_name": self.data["cluster_name"],
                        "cluster_type": self.data["cluster_type"],
                    }
                ]
            }
            acts_list.append(
                {
                    "act_name": _("[redis master]部署bkdbmon"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

            act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_redis_slave_var_name()
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
            act_kwargs.cluster = {
                "servers": [
                    {
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": self.data["bk_cloud_id"],
                        "server_ports": ports,
                        "meta_role": InstanceRole.REDIS_SLAVE.value,
                        "cluster_domain": self.data["domain_name"],
                        "app": app,
                        "app_name": app_name,
                        "cluster_name": self.data["cluster_name"],
                        "cluster_type": self.data["cluster_type"],
                    }
                ]
            }
            acts_list.append(
                {
                    "act_name": _("[redis slave]部署bkdbmon"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
            act_kwargs.cluster = {}
        act_kwargs.ip_index = None
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        proxy_num = len(self.data["nodes"]["proxy"])

        acts_list = []
        for ip_index in range(0, proxy_num):
            act_kwargs.ip_index = ip_index
            act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_new_proxy_ips_var_name()
            act_kwargs.get_redis_payload_func = RedisActPayload.get_install_twemproxy_payload.__name__
            acts_list.append(
                {
                    "act_name": _("安装proxy实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

            act_kwargs.cluster = {
                "servers": [
                    {
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": self.data["bk_cloud_id"],
                        "server_ports": [self.data["proxy_port"]],
                        "meta_role": MachineType.TWEMPROXY.value,
                        "cluster_domain": self.data["domain_name"],
                        "app": app,
                        "app_name": app_name,
                        "cluster_name": self.data["cluster_name"],
                        "cluster_type": self.data["cluster_type"],
                    }
                ]
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
            acts_list.append(
                {
                    "act_name": _("[proxy]部署bkdbmon"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
            act_kwargs.cluster = {}
        redis_pipeline.add_parallel_acts(acts_list=acts_list)
        act_kwargs.ip_index = None
        act_kwargs.cluster = {
            "meta_func_name": RedisDBMeta.proxy_install.__name__,
            "machine_type": MachineType.TWEMPROXY.value,
        }
        redis_pipeline.add_act(
            act_name=_("proxy安装 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 建立集群关系
        act_kwargs.cluster = {"meta_func_name": RedisDBMeta.redis_make_cluster.__name__}
        redis_pipeline.add_act(
            act_name=_("建立集群 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        acts_list = []
        if self.data["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance.value:
            act_kwargs.cluster = {
                "conf": {
                    "maxmemory": str(self.data["maxmemory"]),
                    "databases": str(self.data["databases"]),
                    "requirepass": self.data["redis_pwd"],
                }
            }
        else:
            act_kwargs.cluster = {
                "conf": {
                    "maxmemory": str(self.data["maxmemory"]),
                    "databases": str(self.data["databases"]),
                    "requirepass": self.data["redis_pwd"],
                    "cluster-enabled": ClusterStatus.REDIS_CLUSTER_NO,
                }
            }
        act_kwargs.get_redis_payload_func = RedisActPayload.set_redis_config.__name__
        acts_list.append(
            {
                "act_name": _("回写集群配置[Redis]"),
                "act_component_code": RedisConfigComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )

        act_kwargs.cluster = {
            "conf": {
                "password": self.data["proxy_pwd"],
                "redis_password": self.data["redis_pwd"],
                "port": str(self.data["proxy_port"]),
            }
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.set_proxy_config.__name__
        acts_list.append(
            {
                "act_name": _("回写集群配置[Twemproxy]"),
                "act_component_code": RedisConfigComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )

        # 添加域名
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.CREATE,
            add_domain_name=self.data["domain_name"],
            dns_op_exec_port=self.data["proxy_port"],
        )
        act_kwargs.get_trans_data_ip_var = RedisApplyContext.get_new_proxy_ips_var_name()
        acts_list.append(
            {
                "act_name": _("注册域名"),
                "act_component_code": RedisDnsManageComponent.code,
                "kwargs": {**asdict(act_kwargs), **asdict(dns_kwargs)},
            }
        )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        redis_pipeline.run_pipeline()
