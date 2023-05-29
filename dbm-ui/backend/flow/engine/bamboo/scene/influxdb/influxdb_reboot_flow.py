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
from backend.flow.consts import InfluxdbActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.plugins.components.collections.influxdb.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.influxdb.influxdb_act_playload import get_base_payload
from backend.flow.utils.influxdb.influxdb_context_dataclass import ActKwargs, ApplyContext

logger = logging.getLogger("flow")


class InfluxdbRebootFlow(object):
    """
    构建Influxdb重用流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.data = data

    def __get_all_reboot_instances(self) -> list:
        return self.data["instance_list"]

    def reboot_influxdb_flow(self):
        """
        定义重启Influxdb实例
        :return:
        """
        influxdb_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.InfluxDB)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_kwargs.file_list = trans_files.reboot()
        act_kwargs.bk_cloud_id = self.data["instance_list"][0]["bk_cloud_id"]
        act_kwargs.exec_ip = self.__get_all_reboot_instances()
        influxdb_pipeline.add_act(
            act_name=_("下发actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        reboot_acts = []
        for instance in self.__get_all_reboot_instances():
            # 重启进程
            act_kwargs.template = get_base_payload(
                action=InfluxdbActuatorActionEnum.RestartProcess.value, host=instance["ip"]
            )
            act_kwargs.exec_ip = [{"ip": instance["ip"]}]
            reboot_act = {
                "act_name": _("重启实例-{}").format(instance["ip"]),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            reboot_acts.append(reboot_act)
        # 并发执行所有重启实例
        influxdb_pipeline.add_parallel_acts(acts_list=reboot_acts)

        influxdb_pipeline.run_pipeline()
