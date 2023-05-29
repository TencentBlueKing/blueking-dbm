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
from backend.flow.engine.bamboo.scene.vm.vm_base_flow import VmBaseFlow
from backend.flow.plugins.components.collections.vm.exec_vm_actuator_script import ExecuteVmActuatorScriptComponent
from backend.flow.plugins.components.collections.vm.get_vm_payload import GetVmActPayloadComponent
from backend.flow.plugins.components.collections.vm.trans_files import TransFileComponent
from backend.flow.plugins.components.collections.vm.vm_db_meta import VmMetaComponent
from backend.flow.utils.vm.vm_act_payload import VmActPayload
from backend.flow.utils.vm.vm_context_dataclass import VmActKwargs, VmApplyContext

logger = logging.getLogger("flow")


class VmEnableFlow(VmBaseFlow):
    """
    构建vm集群启用流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.root_id = root_id
        self.data = data

    def enable_vm_flow(self):
        """
        启用vm集群
        """
        # Builder 传参 为封装好角色IP的数据结构
        enable_data = self.get_flow_base_data()
        vm_pipeline = Builder(root_id=self.root_id, data=enable_data)
        trans_files = GetFileList(db_type=DBType.Vm)

        # 拼接活动节点需要的私有参数
        act_kwargs = VmActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = VmApplyContext.__name__
        act_kwargs.file_list = trans_files.vm_actuator()

        vm_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetVmActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        all_ips = self.get_all_node_ips_in_dbmeta()
        act_kwargs.exec_ip = all_ips
        vm_pipeline.add_act(
            act_name=_("下发actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        all_ip_acts = []
        for ip in all_ips:
            # 启动节点进程
            act_kwargs.get_vm_payload_func = VmActPayload.get_start_process_payload.__name__
            act_kwargs.exec_ip = ip
            act = {
                "act_name": _("启动vm集群进程-{}").format(ip),
                "act_component_code": ExecuteVmActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            all_ip_acts.append(act)

        vm_pipeline.add_parallel_acts(acts_list=all_ip_acts)

        # 修改DBMeta
        vm_pipeline.add_act(act_name=_("修改Meta"), act_component_code=VmMetaComponent.code, kwargs=asdict(act_kwargs))

        vm_pipeline.run_pipeline()
