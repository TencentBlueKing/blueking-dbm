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
from backend.db_meta import api
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.machine_type import MachineType
from backend.flow.consts import DBActuatorTypeEnum, DnsOpType, RedisActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.cc_service import (
    TransferHostDestroyClusterComponent,
    TransferHostScaleComponent,
)
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisProxyScaleFlow(object):
    """
    proxy扩缩容流程
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
        cluster_info = api.cluster.nosqlcomm.get_cluster_detail(cluster_id)[0]
        cluster_name = cluster_info["name"]
        cluster_type = cluster_info["cluster_type"]
        redis_master_set = cluster_info["redis_master_set"]
        redis_slave_set = cluster_info["redis_slave_set"]
        servers = []
        if cluster_type in [ClusterType.TendisTwemproxyRedisInstance, ClusterType.TwemproxyTendisSSDInstance]:
            for set in redis_master_set:
                ip_port, seg_range = str.split(set)
                servers.append("{} {} {} {}".format(ip_port, cluster_name, seg_range, 1))
        elif cluster_type == ClusterType.TendisPredixyTendisplusCluster:
            servers = redis_master_set + redis_slave_set

        return {
            "proxy_port": cluster_info["twemproxy_ports"][0],
            "cluster_type": cluster_type,
            "cluster_name": cluster_name,
            "bk_cloud_id": cluster_info["bk_cloud_id"],
            "servers": servers,
            "domain_name": cluster_info["clusterentry_set"]["dns"][0]["domain"],
        }

    def redis_proxy_scale_flow(self):
        """
        主要逻辑：
            0、获取信息(proxy配置、密码、端口、分片信息)(twemproxy和predixy是两套不同逻辑)
            1、初始化信息
            2、下发介质包
            3、新增proxy
                3.1 部署实例
                3.2 元数据
                3.3 域名
                3.4 cc模块
            4、下架proxy
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], self.data["cluster_id"])
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {**cluster_info}
        act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
        #  TODO  if self.data["ip_source"] == IpSource.RESOURCE_POOL 从资源池获取资源 待删除
        if self.data["del_proxy_list"]:
            ips = [info["ip"] for info in self.data["del_proxy_list"]]
            old_proxy_list = defaultdict(list)
            for proxy_ip in ips:
                old_proxy_list[proxy_ip] = cluster_info["proxy_port"]
            act_kwargs.cluster = {
                **cluster_info,
                #  twemproxy下架的时候需要
                "operate": DBActuatorTypeEnum.Proxy.value + "_" + RedisActuatorActionEnum.Shutdown.value,
                **dict(old_proxy_list),
            }
        proxy_payload = ""
        machine_type = ""
        if cluster_info["cluster_type"] in [
            ClusterType.TendisTwemproxyRedisInstance.value,
            ClusterType.TwemproxyTendisSSDInstance.value,
        ]:
            act_kwargs.file_list = trans_files.redis_cluster_apply_proxy()
            proxy_payload = RedisActPayload.add_twemproxy_payload.__name__
            machine_type = MachineType.TWEMPROXY.value
        elif cluster_info["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
            act_kwargs.file_list = trans_files.tendisplus_apply_proxy()
            proxy_payload = RedisActPayload.add_predixy_payload.__name__
            machine_type = MachineType.PREDIXY.value
        else:
            pass

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 增加proxy
        if self.data["add_proxy_list"]:
            ips = [info["ip"] for info in self.data["add_proxy_list"]]
            act_kwargs.exec_ip = ips
            redis_pipeline.add_act(
                act_name=_("proxy下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
            )
            act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
            redis_pipeline.add_act(
                act_name=_("初始化机器"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            #  并发安装proxy
            sub_pipelines = []
            for proxy_ip in ips:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
                act_kwargs.exec_ip = proxy_ip
                act_kwargs.get_redis_payload_func = proxy_payload
                sub_pipeline.add_act(
                    act_name=_("{}安装proxy实例").format(proxy_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                sub_pipeline.add_act(
                    act_name=_("{}部署bkdbmon").format(proxy_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                act_kwargs.cluster = {
                    "proxy_ips": [proxy_ip],
                    "proxy_port": cluster_info["proxy_port"],
                    "meta_func_name": RedisDBMeta.proxy_add_cluster.__name__,
                    "domain_name": cluster_info["domain_name"],
                    "machine_type": machine_type,
                }
                sub_pipeline.add_act(
                    act_name=_("{}proxy扩容 元数据").format(proxy_ip),
                    act_component_code=RedisDBMetaComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 添加域名
                dns_kwargs = DnsKwargs(
                    dns_op_type=DnsOpType.CREATE,
                    add_domain_name=cluster_info["domain_name"],
                    dns_op_exec_port=cluster_info["proxy_port"],
                )
                act_kwargs.exec_ip = proxy_ip
                sub_pipeline.add_act(
                    act_name=_("{}添加域名").format(proxy_ip),
                    act_component_code=RedisDnsManageComponent.code,
                    kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
                )

                act_kwargs.cluster = {
                    "cluster_name": cluster_info["cluster_name"],
                    "cluster_type": cluster_info["cluster_type"],
                    "machine_list": [
                        {
                            "machine_type": machine_type,
                            "ips": [proxy_ip],
                        }
                    ],
                }
                sub_pipeline.add_act(
                    act_name=_("主机转移"), act_component_code=TransferHostScaleComponent.code, kwargs=asdict(act_kwargs)
                )

                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("新增proxy实例")))
            redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)

        # 下架proxy
        if self.data["del_proxy_list"]:
            ips = [info["ip"] for info in self.data["del_proxy_list"]]
            act_kwargs.exec_ip = ips
            redis_pipeline.add_act(
                act_name=_("proxy下发介质包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
                error_ignorable=True,
            )
            sub_pipelines = []
            for proxy_ip in ips:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
                # 清理域名
                dns_kwargs = DnsKwargs(
                    dns_op_type=DnsOpType.RECYCLE_RECORD,
                    dns_op_exec_port=cluster_info["proxy_port"],
                )
                act_kwargs.exec_ip = proxy_ip
                sub_pipeline.add_act(
                    act_name=_("{}删除域名").format(proxy_ip),
                    act_component_code=RedisDnsManageComponent.code,
                    kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
                )

                act_kwargs.exec_ip = proxy_ip
                act_kwargs.get_redis_payload_func = RedisActPayload.proxy_operate_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("{}下架proxy实例").format(proxy_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                    error_ignorable=True,
                )

                #  TODO 这个地方模块转移后面可能需要修改成待回收模块
                #  这个节点得放在删除元数据之前，否则会找不到bk_host_id
                act_kwargs.cluster = {"ips": [proxy_ip]}
                sub_pipeline.add_act(
                    act_name=_("主机转移到空闲机"),
                    act_component_code=TransferHostDestroyClusterComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("下架proxy实例")))
            redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)
            #  删除元数据这里，放在子流程里可能会发生死锁。所以给放在外面统一清理
            act_kwargs.cluster = {
                "proxy_ips": ips,
                "proxy_port": cluster_info["proxy_port"],
                "meta_func_name": RedisDBMeta.proxy_uninstall.__name__,
                "domain_name": cluster_info["domain_name"],
            }
            redis_pipeline.add_act(
                act_name=_("proxy下架元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )
        redis_pipeline.run_pipeline()
