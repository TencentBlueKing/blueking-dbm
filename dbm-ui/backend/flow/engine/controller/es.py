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

from backend.flow.engine.bamboo.scene.es.es_apply_flow import EsApplyFlow
from backend.flow.engine.bamboo.scene.es.es_destroy_flow import EsDestroyFlow
from backend.flow.engine.bamboo.scene.es.es_disable_flow import EsDisableFlow
from backend.flow.engine.bamboo.scene.es.es_enable_flow import EsEnableFlow
from backend.flow.engine.bamboo.scene.es.es_reboot_flow import EsRebootFlow
from backend.flow.engine.bamboo.scene.es.es_replace_flow import EsReplaceFlow
from backend.flow.engine.bamboo.scene.es.es_scale_up_flow import EsScaleUpFlow
from backend.flow.engine.bamboo.scene.es.es_shrink_flow import EsShrinkFlow
from backend.flow.engine.controller.base import BaseController

logger = logging.getLogger("Controller")


class EsController(BaseController):
    """
    es实例相关调用
    """

    def es_apply_scene(self):
        """
        es部署流程
        """
        flow = EsApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_es_flow()

    def es_scale_up_scene(self):
        """
        es扩容
        """
        flow = EsScaleUpFlow(root_id=self.root_id, data=self.ticket_data)
        flow.scale_up_es_flow()

    def es_enable_scene(self):
        """
        es启用
        """
        flow = EsEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_es_flow()

    def es_disable_scene(self):
        """
        es禁用
        """
        flow = EsDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_es_flow()

    def es_destroy_scene(self):
        """
        es下架
        """
        flow = EsDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_es_flow()

    def es_shrink_scene(self):
        """
        es缩容
        """
        flow = EsShrinkFlow(root_id=self.root_id, data=self.ticket_data)
        flow.shrink_es_flow()

    def es_replace_scene(self):
        """
        es替换
        """
        flow = EsReplaceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.replace_es_flow()

    def es_reboot_scene(self):
        """
        es重启节点
        """
        flow = EsRebootFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reboot_es_flow()
