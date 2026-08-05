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

from backend.flow.engine.bamboo.scene.k8s_vm.k8s_vm_apply_flow import K8sVmApplyFlow
from backend.flow.engine.bamboo.scene.k8s_vm.k8s_vm_delete_flow import K8sVmDeleteFlow
from backend.flow.engine.bamboo.scene.k8s_vm.k8s_vm_disable_flow import K8sVmDisableFlow
from backend.flow.engine.bamboo.scene.k8s_vm.k8s_vm_enable_flow import K8sVmEnableFlow
from backend.flow.engine.bamboo.scene.k8s_vm.k8s_vm_restart_flow import K8sVmRestartFlow
from backend.flow.engine.controller.base import BaseController


class K8sVmController(BaseController):
    """
    K8s VM实例相关调用
    """

    def vm_apply_scene(self):
        """
        K8s VM部署流程
        """
        flow = K8sVmApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_vm_flow()

    def vm_enable_scene(self):
        """
        K8s VM启用流程
        """
        flow = K8sVmEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_vm_flow()

    def vm_disable_scene(self):
        """
        K8s VM禁用流程
        """
        flow = K8sVmDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_vm_flow()

    def vm_delete_scene(self):
        """
        K8s VM删除流程
        """
        flow = K8sVmDeleteFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_vm_flow()

    def vm_restart_scene(self):
        """
        K8s VM重启流程
        """
        flow = K8sVmRestartFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_vm_flow()
