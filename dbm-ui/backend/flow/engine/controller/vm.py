# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights rvmerved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licensvm/MIT
Unlvms required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either exprvms or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging

from backend.flow.engine.bamboo.scene.vm.vm_apply_flow import VmApplyFlow
from backend.flow.engine.bamboo.scene.vm.vm_destroy_flow import VmDestroyFlow
from backend.flow.engine.bamboo.scene.vm.vm_disable_flow import VmDisableFlow
from backend.flow.engine.bamboo.scene.vm.vm_enable_flow import VmEnableFlow
from backend.flow.engine.bamboo.scene.vm.vm_machine_clear_flow import ClearVmMachineFlow
from backend.flow.engine.bamboo.scene.vm.vm_reboot_flow import VmRebootFlow
from backend.flow.engine.bamboo.scene.vm.vm_replace_flow import VmReplaceFlow
from backend.flow.engine.bamboo.scene.vm.vm_scale_up_flow import VmScaleUpFlow
from backend.flow.engine.bamboo.scene.vm.vm_shrink_flow import VmShrinkFlow
from backend.flow.engine.controller.base import BaseController

logger = logging.getLogger("Controller")


class VmController(BaseController):
    """
    vm实例相关调用
    """

    def vm_apply_scene(self):
        """
        vm部署流程
        """
        flow = VmApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_vm_flow()

    def vm_scale_up_scene(self):
        """
        vm扩容
        """
        flow = VmScaleUpFlow(root_id=self.root_id, data=self.ticket_data)
        flow.scale_up_vm_flow()

    def vm_enable_scene(self):
        """
        vm启用
        """
        flow = VmEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_vm_flow()

    def vm_disable_scene(self):
        """
        vm禁用
        """
        flow = VmDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_vm_flow()

    def vm_destroy_scene(self):
        """
        vm下架
        """
        flow = VmDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_vm_flow()

    def vm_shrink_scene(self):
        """
        vm缩容
        """
        flow = VmShrinkFlow(root_id=self.root_id, data=self.ticket_data)
        flow.shrink_vm_flow()

    def vm_replace_scene(self):
        """
        vm替换
        """
        flow = VmReplaceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.replace_vm_flow()

    def vm_reboot_scene(self):
        """
        vm重启节点
        """
        flow = VmRebootFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reboot_vm_flow()

    def vm_machine_clear_scene(self):
        """
        vm清理机器
        """
        flow = ClearVmMachineFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()
