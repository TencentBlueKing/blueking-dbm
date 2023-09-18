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
from backend.db_meta.models import StorageInstance
from backend.flow.consts import (
    DEFAULT_MONITOR_TIME,
    DEFAULT_REDIS_SYSTEM_CMDS,
    DBActuatorTypeEnum,
    DnsOpType,
    RedisActuatorActionEnum,
    RedisBackupEnum,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.cc_service import TransferHostDestroyClusterComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class SingleRedisShutdownFlow(object):
    """
    孤立redis节点下架流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_ins_by_id(bk_biz_id: int, ins_ids: list) -> dict:
        ins_info_dict = {}
        for ins_id in ins_ids:
            ins_info = StorageInstance.objects.get(id=ins_id, bk_biz_id=bk_biz_id)
            if ins_info.machine.ip not in ins_info_dict:
                ins_info_dict[ins_info.machine.ip] = {
                    "ports": [],
                    "cluster_type": "",
                }
            ins_info_dict[ins_info.machine.ip]["ports"].append(ins_info.port)
            ins_info_dict[ins_info.machine.ip]["cluster_type"] = ins_info.cluster_type

        return ins_info_dict

    def single_redis_shutdown_flow(self):
        """
        主要逻辑：
            1、根据instance_list获取对应的实例信息
            2、下发介质
            3、监听请求
            3、执行下架逻辑
            4、清理配置
            5、挪动CC
            6、删除元数据
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        ins_info = self.__get_ins_by_id(self.data["bk_fiz_id"], self.data["instance_list"])
        ins_ips = list(ins_info.keys())

        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **ins_info,
            "backup_type": RedisBackupEnum.NORMAL_BACKUP.value,
        }

        act_kwargs.exec_ip = ins_ips
        # 下发介质，可能是故障机器，忽略错误
        redis_pipeline.add_act(
            act_name=_("下发介质包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(act_kwargs),
            error_ignorable=True,
        )
        #  监听请求。独立节点，理论上是没有请求的
        if self.data["force"]:
            acts_list = []
            for ip in ins_ips:
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

        acts_list = []
        for ip in ins_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_shutdown_payload.__name__
            acts_list.append(
                {
                    "act_name": _("{}下架redis实例").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                    "error_ignorable": True,
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 挪CC到回收模块
        act_kwargs.cluster = {"ips": ins_ips}
        redis_pipeline.add_act(
            act_name=_("主机转移到空闲机"),
            act_component_code=TransferHostDestroyClusterComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # TODO 孤立redis实例下架
        # act_kwargs.cluster = {
        #     "meta_func_name": RedisDBMeta.cluster_shutdown.__name__,
        #     "cluster_type": cluster_info["cluster_type"],
        # }
        # redis_pipeline.add_act(
        #     act_name="删除集群元数据", act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        # )
