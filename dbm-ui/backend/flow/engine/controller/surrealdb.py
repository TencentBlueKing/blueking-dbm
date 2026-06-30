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
from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_destroy_flow import K8sSurrealDBDestroyFlow
from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_disable_flow import K8sSurrealDBDisableFlow
from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_enable_flow import K8sSurrealDBEnableFlow
from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_restart_flow import K8sSurrealDBRestartFlow
from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_single.surrealdb_single_apply_flow import (
    K8sSurrealDBSingleApplyFlow,
)
from backend.flow.engine.controller.base import BaseController
from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_ha.surrealdb_ha_apply_flow import K8sSurrealdbApplyFlow



class SurrealDBController(BaseController):
    """
    SurrealDB 单机版实例相关调用
    """

    def surrealdb_single_apply_scene(self):
        """
        SurrealDB 单机版部署流程
        """
        flow = K8sSurrealDBSingleApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_surrealdb_flow()

    def surrealdb_enable_scene(self):
        """
        SurrealDB 启用流程
        """
        flow = K8sSurrealDBEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_surrealdb_flow()

    def surrealdb_disable_scene(self):
        """
        SurrealDB 禁用流程
        """
        flow = K8sSurrealDBDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_surrealdb_flow()

    def surrealdb_restart_scene(self):
        """
        SurrealDB 重启流程
        """
        flow = K8sSurrealDBRestartFlow(root_id=self.root_id, data=self.ticket_data)
        flow.restart_surrealdb_flow()

    def surrealdb_destroy_scene(self):
        """
        SurrealDB 下架流程
        """
        flow = K8sSurrealDBDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_surrealdb_flow()


class SurrealdbHaController(BaseController):
    """
    SurrealDB 组件版实例相关调用
    """

    def surrealdb_apply_scene(self):
        """
        SurrealDB 部署流程
        """
        flow = K8sSurrealdbApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_surrealdb_flow()
