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
from backend.flow.engine.bamboo.scene.es.es_flow import EsFlow
from backend.flow.plugins.components.collections.es.exec_es_actuator_script import ExecuteEsActuatorScriptComponent
from backend.flow.plugins.components.collections.es.get_es_payload import GetEsActPayloadComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.utils.es.es_act_payload import EsActPayload
from backend.flow.utils.es.es_context_dataclass import EsActKwargs, EsApplyContext

logger = logging.getLogger("flow")


class EsRebootFlow(EsFlow):
    """
    构建ES重启实例流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.instance_list = data["instance_list"]

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["instance_list"] = self.instance_list
        return flow_data

    def __get_all_reboot_ips(self) -> list:
        return list(set([instance["ip"] for instance in self.instance_list]))

    def __get_all_reboot_instances(self) -> list:
        return self.instance_list

    def reboot_es_flow(self):
        """
        定义重启ES集群
        :return:
        """
        es_pipeline = Builder(root_id=self.root_id, data=self.__get_flow_data())
        trans_files = GetFileList(db_type=DBType.Es)
        act_kwargs = EsActKwargs(self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = EsApplyContext.__name__
        act_kwargs.file_list = trans_files.es_reboot()

        es_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetEsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = self.__get_all_reboot_ips()
        es_pipeline.add_act(
            act_name=_("下发actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        reboot_acts = []
        for instance in self.__get_all_reboot_instances():
            # 启动进程
            act_kwargs.get_es_payload_func = EsActPayload.get_reboot_process_payload.__name__
            act_kwargs.exec_ip = instance["ip"]
            act_kwargs.instance_name = instance["instance_name"]
            reboot_act = {
                "act_name": _("重启实例-{}").format(instance["ip"]),
                "act_component_code": ExecuteEsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            reboot_acts.append(reboot_act)
        # 并发执行所有重启实例
        es_pipeline.add_parallel_acts(acts_list=reboot_acts)

        es_pipeline.run_pipeline()
