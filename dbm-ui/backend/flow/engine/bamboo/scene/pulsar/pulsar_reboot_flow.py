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
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.pulsar.pulsar_base_flow import PulsarBaseFlow
from backend.flow.plugins.components.collections.pulsar.exec_actuator_script import (
    ExecutePulsarActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.pulsar.get_pulsar_payload import GetPulsarActPayloadComponent
from backend.flow.plugins.components.collections.pulsar.trans_files import TransFileComponent
from backend.flow.utils.pulsar.consts import PULSAR_ROLE_ALL
from backend.flow.utils.pulsar.pulsar_act_payload import PulsarActPayload
from backend.flow.utils.pulsar.pulsar_context_dataclass import PulsarActKwargs, PulsarApplyContext

logger = logging.getLogger("flow")


class PulsarRebootFlow(PulsarBaseFlow):
    """
    构建Pulsar集群实例重启流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.data = data

    def reboot_pulsar_flow(self):
        """
        重启Pulsar集群实例
        """
        # Builder 传参 为封装好角色IP的数据结构
        pulsar_pipeline = Builder(root_id=self.root_id, data=self.base_flow_data)
        trans_files = GetFileList(db_type=DBType.Pulsar)

        # 拼接活动节点需要的私有参数
        act_kwargs = PulsarActKwargs(bk_cloud_id=self.base_flow_data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = PulsarApplyContext.__name__
        act_kwargs.file_list = trans_files.pulsar_actuator()

        pulsar_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetPulsarActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = self.__get_all_reboot_ips()
        pulsar_pipeline.add_act(
            act_name=_("下发pulsar actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        reboot_acts = []
        # 是否判断实例是否存在
        for instance in self.data["instance_list"]:
            # 启动进程
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_reboot_process_payload.__name__
            act_kwargs.exec_ip = instance["ip"]
            act_kwargs.role = PULSAR_ROLE_ALL
            reboot_act = {
                "act_name": _("重启实例-{}-{}").format(act_kwargs.exec_ip, act_kwargs.role),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            reboot_acts.append(reboot_act)
        # 并发执行所有重启实例
        pulsar_pipeline.add_parallel_acts(acts_list=reboot_acts)

        pulsar_pipeline.run_pipeline()

    def __get_all_reboot_ips(self) -> list:
        return list(set([instance["ip"] for instance in self.data["instance_list"]]))
