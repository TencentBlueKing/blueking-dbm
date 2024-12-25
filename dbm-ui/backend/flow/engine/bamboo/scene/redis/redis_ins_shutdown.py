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
from backend.db_meta.enums import ClusterEntryRole, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_MONITOR_TIME, DEFAULT_REDIS_SYSTEM_CMDS, DnsOpType, RedisBackupEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import AccessManagerAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisInsShutdownFlow(object):
    """
    主从实例下架
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_ins_info(bk_biz_id: int, cluster_ids: list) -> dict:
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
        ip_port_dict = defaultdict(list)
        cluster_type = ""
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
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
            if cluster_type == "":
                cluster_type = cluster.cluster_type
            elif cluster_type != cluster.cluster_type:
                raise Exception(_("存在不同的cluster_type。 {} and {}").format(cluster_type, cluster.cluster_type))

        return {
            "ins_info_list": ins_info_list,
            "master_ips": list(set(master_ips)),
            "slave_ips": list(set(slave_ips)),
            "ip_port_dict": dict(ip_port_dict),
            "cluster_type": cluster_type,
        }

    def redis_ins_shutdown_flow(self):
        """
        主要逻辑：
            1、根据cluster_id获取对应的实例信息
            2、下发介质
            3、监听请求
            3.1、执行下架逻辑
            3.2、删除域名
            4、清理配置
            5、挪动CC
            6、删除元数据
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        all_ins_info = self.__get_ins_info(self.data["bk_biz_id"], self.data["cluster_ids"])
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
            "backup_type": RedisBackupEnum.FOREVER_BACKUP.value,
            "monitor_time_ms": DEFAULT_MONITOR_TIME,
            "ignore_req": True,
            "ignore_keys": DEFAULT_REDIS_SYSTEM_CMDS,
        }

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = master_ips + slave_ips
        # 下发介质，可能是故障机器，忽略错误
        redis_pipeline.add_act(
            act_name=_("下发介质包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(act_kwargs),
            error_ignorable=True,
        )
        #  监听请求。独立节点，理论上是没有请求的
        acts_list = []
        for ip in master_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_capturer.__name__
            acts_list.append(
                {
                    "act_name": _("redis请求检查: {}").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                    "error_ignorable": True,
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 做一次永久备份
        acts_list = []
        for ins_info in all_ins_info["ins_info_list"]:
            act_kwargs.exec_ip = ins_info["master_ip"]
            act_kwargs.cluster["domain_name"] = ins_info["domain_name"]

            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_backup_payload.__name__
            acts_list.append(
                {
                    "act_name": _("redis备份: {}").format(ins_info["domain_name"]),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 删除接入层信息
        sub_pipeline_list = []
        for cluster_id in self.data["cluster_ids"]:
            params = {
                "cluster_id": cluster_id,
                "op_type": DnsOpType.CLUSTER_DELETE,
                "role": [
                    ClusterEntryRole.NODE_ENTRY.value,
                    ClusterEntryRole.PROXY_ENTRY.value,
                    ClusterEntryRole.MASTER_ENTRY.value,
                    ClusterEntryRole.SLAVE_ENTRY.value,
                ],
            }
            access_sub_builder = AccessManagerAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipeline_list.append(access_sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_pipeline_list)

        # 集群元数据删除
        acts_list = []
        for cluster_id in self.data["cluster_ids"]:
            act_kwargs.cluster = {
                "cluster_id": cluster_id,
                "meta_func_name": RedisDBMeta.cluster_shutdown.__name__,
                "cluster_type": cluster_type,
            }
            acts_list.append(
                {
                    "act_name": _("删除集群{}元数据").format(cluster_id),
                    "act_component_code": RedisDBMetaComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        acts_list = []
        for ip in master_ips + slave_ips:
            act_kwargs.cluster = {}
            act_kwargs.exec_ip = ip
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_shutdown_payload.__name__
            acts_list.append(
                {
                    "act_name": _("{}下架redis实例{}").format(ip, ip_ports[ip]),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                    "error_ignorable": True,
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 为了卸载dbmon方便，卸载dbmon和实例步骤放在后面来执行
        acts_list = []
        for ip in master_ips + slave_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {"ip": ip, "bk_biz_id": str(self.data["bk_biz_id"])}
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
            acts_list.append(
                {
                    "act_name": _("{}-卸载bkdbmon").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        redis_pipeline.run_pipeline()
