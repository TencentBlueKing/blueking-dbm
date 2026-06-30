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

from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_single.surrealdb_single_apply_flow import (
    K8sSurrealDBSingleApplyFlow,
)
from backend.flow.engine.controller.base import BaseController


class SurrealDBSingleController(BaseController):
    """
    SurrealDB 单机版实例相关调用
    """

    def surrealdb_apply_scene(self):
        """
        SurrealDB 单机版实例部署流程
        """
        flow = K8sSurrealDBSingleApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_surrealdb_flow()

    def surrealdb_enable_scene(self):
        """
        SurrealDB 单机版实例启用流程
        """
        pass

    def surrealdb_disable_scene(self):
        """
        SurrealDB 单机版实例禁用流程
        """
        pass

    def surrealdb_restart_scene(self):
        """
        SurrealDB 单机版实例重启流程
        """
        pass
