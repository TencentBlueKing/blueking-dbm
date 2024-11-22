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
import logging

from backend.flow.engine.bamboo.scene.doris.doris_apply_flow import DorisApplyFlow
from backend.flow.engine.bamboo.scene.doris.doris_destroy_flow import DorisDestroyFlow
from backend.flow.engine.bamboo.scene.doris.doris_disable_flow import DorisDisableFlow
from backend.flow.engine.bamboo.scene.doris.doris_enable_flow import DorisEnableFlow
from backend.flow.engine.bamboo.scene.doris.doris_machine_clear_flow import ClearDorisMachineFlow
from backend.flow.engine.bamboo.scene.doris.doris_reboot_flow import DorisRebootFlow
from backend.flow.engine.bamboo.scene.doris.doris_replace_flow import DorisReplaceFlow
from backend.flow.engine.bamboo.scene.doris.doris_scale_up_flow import DorisScaleUpFlow
from backend.flow.engine.bamboo.scene.doris.doris_shrink_flow import DorisShrinkFlow
from backend.flow.engine.controller.base import BaseController

logger = logging.getLogger("Controller")


class DorisController(BaseController):
    """
    doris实例相关调用
    """

    def doris_apply_scene(self):
        """
        doris部署流程
        """
        flow = DorisApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_doris_flow()

    def doris_scale_up_scene(self):
        """
        doris扩容
        """
        flow = DorisScaleUpFlow(root_id=self.root_id, data=self.ticket_data)
        flow.scale_up_doris_flow()

    def doris_enable_scene(self):
        """
        doris启用
        """
        flow = DorisEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_doris_flow()

    def doris_disable_scene(self):
        """
        doris禁用
        """
        flow = DorisDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_doris_flow()

    def doris_destroy_scene(self):
        """
        doris下架
        """
        flow = DorisDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_doris_flow()

    def doris_shrink_scene(self):
        """
        doris缩容
        """
        flow = DorisShrinkFlow(root_id=self.root_id, data=self.ticket_data)
        flow.shrink_doris_flow()

    def doris_replace_scene(self):
        """
        doris替换
        """
        flow = DorisReplaceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.replace_doris_flow()

    def doris_reboot_scene(self):
        """
        doris重启节点
        """
        flow = DorisRebootFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reboot_doris_flow()

    def doris_machine_clear_scene(self):
        """
        doris清理机器
        """
        flow = ClearDorisMachineFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()
