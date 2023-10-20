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
from backend.flow.engine.bamboo.scene.pulsar.pulsar_apply_flow import PulsarApplyFlow
from backend.flow.engine.bamboo.scene.pulsar.pulsar_destroy_flow import PulsarDestroyFlow
from backend.flow.engine.bamboo.scene.pulsar.pulsar_disable_flow import PulsarDisableFlow
from backend.flow.engine.bamboo.scene.pulsar.pulsar_enable_flow import PulsarEnableFlow
from backend.flow.engine.bamboo.scene.pulsar.pulsar_fake_apply_flow import PulsarFakeApplyFlow
from backend.flow.engine.bamboo.scene.pulsar.pulsar_reboot_flow import PulsarRebootFlow
from backend.flow.engine.bamboo.scene.pulsar.pulsar_replace_flow import PulsarReplaceFlow
from backend.flow.engine.bamboo.scene.pulsar.pulsar_scale_up_flow import PulsarScaleUpFlow
from backend.flow.engine.bamboo.scene.pulsar.pulsar_shrink_flow import PulsarShrinkFlow
from backend.flow.engine.controller.base import BaseController


class PulsarController(BaseController):
    """
    pulsar实例相关调用
    """

    def pulsar_apply_scene(self):
        """
        pulsar部署流程
        """
        flow = PulsarApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_pulsar_flow()

    def pulsar_scale_up_scene(self):
        """
        pulsar扩容流程
        """
        flow = PulsarScaleUpFlow(root_id=self.root_id, data=self.ticket_data)
        flow.scale_up_pulsar_flow()

    def pulsar_enable_scene(self):
        """
        pulsar集群启用
        """
        flow = PulsarEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_pulsar_flow()

    def pulsar_disable_scene(self):
        """
        pulsar集群禁用
        """
        flow = PulsarDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_pulsar_flow()

    def pulsar_destroy_scene(self):
        """
        pulsar下架
        """
        flow = PulsarDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_pulsar_flow()

    def pulsar_shrink_scene(self):
        """
        pulsar缩容
        """
        flow = PulsarShrinkFlow(root_id=self.root_id, data=self.ticket_data)
        flow.shrink_pulsar_flow()

    def pulsar_replace_scene(self):
        """
        pulsar替换
        """
        flow = PulsarReplaceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.replace_pulsar_flow()

    def pulsar_reboot_scene(self):
        """
        pulsar重启
        """
        flow = PulsarRebootFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reboot_pulsar_flow()

    def pulsar_fake_apply_scene(self):
        """
        pulsar虚假上架
        """
        flow = PulsarFakeApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.fake_deploy_pulsar_flow()
