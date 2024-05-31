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
from backend.db_meta.enums import ClusterPhase, InstanceRole, MachineType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.flow.consts import (
    DEFAULT_MONITOR_TIME,
    DEFAULT_REDIS_SYSTEM_CMDS,
    DBActuatorTypeEnum,
    InstanceStatus,
    RedisActuatorActionEnum,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_change_password import RedisChangePwdAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class RedisClusterOpenCloseFlow(object):
    """
    redis启停流程
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
        proxy_map = {}
        for proxy in cluster.proxyinstance_set.filter():
            proxy_map[proxy.machine.ip] = proxy.port

        return {
            "domain_name": cluster.immute_domain,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_name": cluster.name,
            "cluster_type": cluster.cluster_type,
            "proxy_map": proxy_map,
        }

    def redis_cluster_open_close_flow(self):
        """
        主要逻辑：
            1、初始化信息
            2、下发介质包
            3.1、更新状态
            3.2、执行启停
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], self.data["cluster_id"])
        proxy_ips = list(cluster_info["proxy_map"].keys())
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        op = (
            RedisActuatorActionEnum.Open.value
            if self.data["ticket_type"] == TicketType.REDIS_PROXY_OPEN
            else RedisActuatorActionEnum.Close.value
        )
        act_kwargs.cluster = {
            **cluster_info,
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

        act_kwargs.exec_ip = proxy_ips
        redis_pipeline.add_act(
            act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )
        if self.data["ticket_type"] == TicketType.REDIS_PROXY_CLOSE and self.data["force"] is False:
            acts_list = []
            for ip in proxy_ips:
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_capturer.__name__
                acts_list.append(
                    {
                        "act_name": _("redis请求检查: {}").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list)

        sub_pipelines = []
        status = (
            InstanceStatus.UNAVAILABLE.value
            if self.data["ticket_type"] == TicketType.REDIS_PROXY_OPEN
            else InstanceStatus.RUNNING.value
        )
        for ip in proxy_ips:
            port = cluster_info["proxy_map"][ip]
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            # 更新状态
            act_kwargs.cluster = {
                "meta_func_name": RedisDBMeta.instances_status_update.__name__,
                "meta_update_ip": ip,
                "meta_update_ports": [port],
                "meta_update_status": status,
            }
            redis_pipeline.add_act(
                act_name=_("{}-更新proxy状态".format(ip)),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )
            meta_role = MachineType.TWEMPROXY.value
            if cluster_info["cluster_type"] in [
                ClusterType.TendisPredixyRedisCluster.value,
                ClusterType.TendisPredixyTendisplusCluster.value,
            ]:
                meta_role = MachineType.PREDIXY.value

            # 启停的时候也得操作dbmon
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {
                "servers": [
                    {
                        "bk_biz_id": str(self.data["bk_biz_id"]),
                        "bk_cloud_id": act_kwargs.bk_cloud_id,
                        "server_ip": ip,
                        "server_ports": []
                        if self.data["ticket_type"] == TicketType.REDIS_PROXY_CLOSE
                        else [cluster_info["proxy_map"][ip]],
                        "meta_role": meta_role,
                        "cluster_domain": cluster_info["domain_name"],
                        "app": app,
                        "app_name": app_name,
                        "cluster_name": cluster_info["cluster_name"],
                        "cluster_type": cluster_info["cluster_type"],
                    }
                ]
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
            sub_pipeline.add_act(
                act_name=_("[{}]卸载bkdbmon").format(ip)
                if self.data["ticket_type"] == TicketType.REDIS_PROXY_CLOSE
                else _("[{}]安装bkdbmon").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 执行启停
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {
                "operate": DBActuatorTypeEnum.Proxy.value + "_" + op,
                "ip": ip,
                "port": cluster_info["proxy_map"][ip],
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.proxy_operate_payload.__name__
            sub_pipeline.add_act(
                act_name="{}: {}".format(TicketType.get_choice_label(self.data["ticket_type"]), ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("集群[{}]启停").format(cluster_info["domain_name"]))
            )

        # 更新集群状态
        act_kwargs.cluster = {
            "meta_func_name": RedisDBMeta.cluster_status_update.__name__,
            "cluster_id": self.data["cluster_id"],
        }
        redis_pipeline.add_act(
            act_name=_("更新集群状态"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()


class RedisInsOpenCloseFlow(object):
    """
        redis启停流程
        {
        "bk_biz_id": 2005000194,
        "ticket_type": "REDIS_INSTANCE_OPEN/REDIS_INSTANCE_CLOSE",
        "cluster_ids": [
            111,
            222,
            333
        ],
        "force": true
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_ins_info(bk_biz_id: int, cluster_ids: list, status: str) -> dict:
        """
        根据cluster_id获取实例元数据相关的信息:
        - bk_cloud_id
        - immute_domain
        - cluster_type(应该都是一样的）
        - master_ip
        - slave_ip
        - port
        """
        ins_info_list = []
        master_ips = []
        slave_ips = []
        bk_cloud_id = 0
        ip_port_dict = defaultdict(list)
        cluster_type = ""
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
            if cluster.phase == status:
                raise Exception("cluster {}:{} phase status is {}".format(cluster_id, cluster.name, status))
            master_obj = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)[0]
            master_ip = master_obj.machine.ip
            port = master_obj.port
            slave_ip = master_obj.as_ejector.all()[0].receiver.machine.ip

            ins_info_list.append(
                {
                    "domain_name": cluster.immute_domain,
                    "bk_cloud_id": cluster.bk_cloud_id,
                    "cluster_name": cluster.name,
                    "master_ip": master_ip,
                    "slave_ip": slave_ip,
                    "port": port,
                    "cluster_id": cluster_id,
                }
            )
            master_ips.append(master_ip)
            slave_ips.append(slave_ip)
            ip_port_dict[master_ip].append(port)
            ip_port_dict[slave_ip].append(port)
            bk_cloud_id = cluster.bk_cloud_id

            if cluster_type == "":
                cluster_type = cluster.cluster_type
            elif cluster_type != cluster.cluster_type:
                raise Exception(_("存在不同的cluster_type。 {} and {}").format(cluster_type, cluster.cluster_type))

        return {
            "ins_info_list": ins_info_list,
            "master_ips": list(set(master_ips)),
            "slave_ips": list(set(slave_ips)),
            "ip_port_dict": dict(ip_port_dict),
            "bk_cloud_id": bk_cloud_id,
            "cluster_type": cluster_type,
        }

    def redis_ins_open_close_flow(self):
        """
        主要逻辑：
            1、预处理数据
            2、初始化信息
            3、机器维度下发介质包
            4、更新实例状态
            5、机器维度执行启停（修改密码，kill连接）
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        cluster_status = (
            ClusterPhase.OFFLINE.value
            if self.data["ticket_type"] == TicketType.REDIS_INSTANCE_CLOSE
            else ClusterPhase.ONLINE.value
        )
        all_ins_info = self.__get_ins_info(self.data["bk_biz_id"], self.data["cluster_ids"], cluster_status)
        master_ips = all_ins_info["master_ips"]
        slave_ips = all_ins_info["slave_ips"]
        ip_ports = all_ins_info["ip_port_dict"]
        cluster_type = all_ins_info["cluster_type"]

        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **all_ins_info,
            **ip_ports,
            "monitor_time_ms": DEFAULT_MONITOR_TIME,
            "ignore_req": False,
            "ignore_keys": DEFAULT_REDIS_SYSTEM_CMDS,
        }
        act_kwargs.bk_cloud_id = all_ins_info.get("bk_cloud_id", 0)

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = master_ips + slave_ips
        redis_pipeline.add_act(
            act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 如果非强制，检查请求
        if self.data["ticket_type"] == TicketType.REDIS_PROXY_CLOSE and self.data["force"] is False:
            acts_list = []
            for ip in master_ips:
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_capturer.__name__
                acts_list.append(
                    {
                        "act_name": _("redis请求检查: {}").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list)

        status = (
            InstanceStatus.UNAVAILABLE.value
            if self.data["ticket_type"] == TicketType.REDIS_INSTANCE_CLOSE
            else InstanceStatus.RUNNING.value
        )
        # 更新实例状态
        acts_list = []
        for redis_ip in master_ips + slave_ips:
            act_kwargs.cluster = {
                "meta_func_name": RedisDBMeta.instances_status_update.__name__,
                "meta_update_ip": redis_ip,
                "meta_update_ports": ip_ports[redis_ip],
                "meta_update_status": status,
            }
            acts_list.append(
                {
                    "act_name": _("{}-更新redis状态".format(redis_ip)),
                    "act_component_code": RedisDBMetaComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list)

        sub_pipeline_list = []
        suffix = "_shutdown"
        for ins_info in all_ins_info["ins_info_list"]:
            # 获取ip:port的密码
            old_pwd = PayloadHandler.redis_get_password_by_cluster_id(ins_info["cluster_id"]).get("redis_password")
            if self.data["ticket_type"] == TicketType.REDIS_INSTANCE_OPEN:
                # if old_pwd.endwith(suffix):
                new_pwd = old_pwd.removesuffix(suffix)
            else:
                new_pwd = old_pwd + suffix
            change_ins = [
                {"ip": ins_info["master_ip"], "role": "redis_master"},
                {"ip": ins_info["slave_ip"], "role": "redis_slave"},
            ]
            params = {
                "change_ins": change_ins,
                "port": ins_info["port"],
                "old_pwd": old_pwd,
                "new_pwd": new_pwd,
                "domain_name": ins_info["domain_name"],
            }
            sub_pipeline_list.append(RedisChangePwdAtomJob(self.root_id, self.data, act_kwargs, params))
        redis_pipeline.add_parallel_sub_pipeline(sub_pipeline_list)

        # master kill 连接
        acts_list = []
        for master_ip in master_ips:
            act_kwargs.exec_ip = master_ip
            act_kwargs.cluster["exec_ip"] = master_ip
            act_kwargs.cluster["cluster_type"] = cluster_type
            act_kwargs.cluster["instances"] = [{"ip": master_ip, "port": p} for p in ip_ports[master_ip]]
            act_kwargs.cluster["idle_time"] = 600
            act_kwargs.cluster["ignore_kill"] = False
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_killconn_4_scene.__name__
            acts_list.append(
                {
                    "act_name": _("干掉非活跃链接-{}").format(master_ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list)

        # 更新集群状态
        acts_list = []
        for ins_info in all_ins_info["ins_info_list"]:
            act_kwargs.cluster = {
                "meta_func_name": RedisDBMeta.cluster_status_update.__name__,
                "cluster_id": ins_info["cluster_id"],
            }
            acts_list.append(
                {
                    "act_name": _("更新集群状态-{}").format(ins_info["cluster_id"]),
                    "act_component_code": RedisDBMetaComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list)

        redis_pipeline.run_pipeline()
