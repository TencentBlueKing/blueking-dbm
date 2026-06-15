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

from backend.flow.engine.bamboo.scene.qdrant.qdrant_apply_flow import K8sQdrantApplyFlow
from backend.flow.engine.bamboo.scene.qdrant.qdrant_delete_flow import K8sQdrantDeleteFlow
from backend.flow.engine.bamboo.scene.qdrant.qdrant_disable_flow import K8sQdrantDisableFlow
from backend.flow.engine.bamboo.scene.qdrant.qdrant_enable_flow import K8sQdrantEnableFlow
from backend.flow.engine.bamboo.scene.qdrant.qdrant_restart_flow import K8sQdrantRestartFlow
from backend.flow.engine.controller.base import BaseController


class QdrantController(BaseController):
    """
    Qdrant实例相关调用
    """

    def qdrant_apply_scene(self):
        """
        Qdrant部署流程
        """
        flow = K8sQdrantApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_qdrant_flow()

    def qdrant_enable_scene(self):
        """
        Qdrant启用流程
        """
        flow = K8sQdrantEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_qdrant_flow()

    def qdrant_disable_scene(self):
        """
        Qdrant禁用流程
        """
        flow = K8sQdrantDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_qdrant_flow()

    def qdrant_delete_scene(self):
        """
        Qdrant删除流程
        """
        flow = K8sQdrantDeleteFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_qdrant_flow()

    def qdrant_restart_scene(self):
        """
        Qdrant重启流程
        """
        flow = K8sQdrantRestartFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_qdrant_flow()
