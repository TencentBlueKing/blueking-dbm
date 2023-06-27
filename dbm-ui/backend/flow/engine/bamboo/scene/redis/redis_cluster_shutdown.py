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

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import AppCache, Cluster
from backend.flow.consts import (
    DEFAULT_MONITOR_TIME,
    DEFAULT_REDIS_SYSTEM_CMDS,
    DBActuatorTypeEnum,
    DnsOpType,
    RedisActuatorActionEnum,
    RedisBackupEnum,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisClusterShutdownFlow(object):
    """
    redis下架流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        proxy_map = {proxy.machine.ip: proxy.port for proxy in cluster.proxyinstance_set.all()}
        redis_map = defaultdict(list)
        redis_master_map = defaultdict(list)
        for ins in cluster.storageinstance_set.all():
            redis_map[ins.machine.ip].append(ins.port)

        for ins in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            redis_master_map[ins.machine.ip].append(ins.port)

        return {
            "domain_name": cluster.immute_domain,
            "cluster_name": cluster.name,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "proxy_map": proxy_map,
            "redis_map": dict(redis_map),
            "redis_master_map": dict(redis_master_map),
            "db_version": cluster.major_version,
        }

    def redis_cluster_shutdown_flow(self):
        """
        主要逻辑：
            1、初始化信息（需要获取:proxy_ip_list/redis_ip_list/all_ip_list)
            2、下发介质包
            6、删除域名
            3、下架proxy层
            4、下架redis层
            5、删除元数据
            7、挪CC
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], self.data["cluster_id"])
        proxy_ips = list(cluster_info["proxy_map"].keys())
        redis_ips = list(cluster_info["redis_map"].keys())
        redis_master_ips = list(cluster_info["redis_master_map"].keys())
        all_ips = proxy_ips + redis_ips
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **cluster_info,
            "backup_type": RedisBackupEnum.NORMAL_BACKUP.value,
            **cluster_info["redis_map"],
            **cluster_info["proxy_map"],
            "monitor_time_ms": DEFAULT_MONITOR_TIME,
            "ignore_req": False,
            "ignore_keys": DEFAULT_REDIS_SYSTEM_CMDS,
        }
        act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]

        app = AppCache.get_app_attr(self.data["bk_biz_id"], "db_app_abbr")
        app_name = AppCache.get_app_attr(self.data["bk_biz_id"], "bk_biz_name")

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = all_ips
        redis_pipeline.add_act(
            act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )
        #  监听请求。集群是先关闭再下架，所以理论上这里是没请求才对
        acts_list = []
        for ip in redis_master_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_capturer.__name__
            acts_list.append(
                {
                    "act_name": _("redis请求检查: {}").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 做一次永久备份
        acts_list = []
        for ip in redis_master_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_backup_payload.__name__
            acts_list.append(
                {
                    "act_name": _("redis备份: {}").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 删除域名
        dns_kwargs = DnsKwargs(dns_op_type=DnsOpType.CLUSTER_DELETE, delete_cluster_id=self.data["cluster_id"])
        redis_pipeline.add_act(
            act_name=_("删除域名"),
            act_component_code=RedisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        acts_list = []
        for ip in proxy_ips:
            # proxy执行下架
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {
                "ip": ip,
                "port": cluster_info["proxy_map"][ip],
                "operate": DBActuatorTypeEnum.Proxy.value + "_" + RedisActuatorActionEnum.Shutdown.value,
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.proxy_operate_payload.__name__
            acts_list.append(
                {
                    "act_name": _("{}下架proxy实例").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

        for ip in redis_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_shutdown_payload.__name__
            acts_list.append(
                {
                    "act_name": _("{}下架redis实例").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

            act_kwargs.cluster = {
                "servers": [
                    {
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": act_kwargs.bk_cloud_id,
                        # TODO 这里暂时不考虑机器复用的情况，直接传空列表。如果后面机器复用的话，这里需要查询出剩余的端口列表
                        "server_ports": [],
                        "meta_role": "",
                        "cluster_domain": cluster_info["domain_name"],
                        "app": app,
                        "app_name": app_name,
                        "cluster_name": cluster_info["cluster_name"],
                        "cluster_type": cluster_info["cluster_type"],
                    }
                ]
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
            acts_list.append(
                {
                    "act_name": _("[redis]卸载bkdbmon"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        acts_list = []
        # 清理config
        # TODO 这里等提供新接口后修改
        act_kwargs.cluster = {
            "conf": {
                "requirepass": "",
                "cluster-enabled": "",
            },
            "cluster_id": self.data["cluster_id"],
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.delete_redis_config.__name__
        acts_list.append(
            {
                "act_name": _("清理Redis配置"),
                "act_component_code": RedisConfigComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )

        act_kwargs.cluster = {
            "conf": {
                "password": "",
                "redis_password": "",
                "port": "",
            },
            "cluster_id": self.data["cluster_id"],
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.delete_proxy_config.__name__
        acts_list.append(
            {
                "act_name": _("清理Proxy配置"),
                "act_component_code": RedisConfigComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 集群元数据删除
        act_kwargs.cluster = {
            "meta_func_name": RedisDBMeta.cluster_shutdown.__name__,
            "cluster_type": cluster_info["cluster_type"],
        }
        redis_pipeline.add_act(
            act_name=_("删除集群元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        redis_pipeline.run_pipeline()
