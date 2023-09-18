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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.name_service.name_service import (
    ExecNameServiceCreateComponent,
    ExecNameServiceDeleteComponent,
)

logger = logging.getLogger("flow")


class NameServiceFlow(object):
    """clb创建flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def name_service_clb_create_flow(self):
        """
        clb create流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 定义私有变量
        kwargs = self.data
        kwargs["name_service_type"] = "clb"

        # 添加活动节点
        pipeline.add_act(act_name=_("创建clb"), act_component_code=ExecNameServiceCreateComponent.code, kwargs=kwargs)

        # 运行流程
        pipeline.run_pipeline()

    def name_service_clb_delete_flow(self):
        """
        clb delete流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 定义私有变量
        kwargs = self.data
        kwargs["name_service_type"] = "clb"

        # 添加活动节点
        pipeline.add_act(act_name=_("删除clb"), act_component_code=ExecNameServiceDeleteComponent.code, kwargs=kwargs)

        # 运行流程
        pipeline.run_pipeline()

    def name_service_polaris_create_flow(self):
        """
        polaris create流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 定义私有变量
        kwargs = self.data
        kwargs["name_service_type"] = "polaris"

        # 添加活动节点
        pipeline.add_act(
            act_name=_("创建polaris"), act_component_code=ExecNameServiceCreateComponent.code, kwargs=kwargs
        )

        # 运行流程
        pipeline.run_pipeline()

    def name_service_polaris_delete_flow(self):
        """
        polaris delete流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 定义私有变量
        kwargs = self.data
        kwargs["name_service_type"] = "polaris"

        # 添加活动节点
        pipeline.add_act(
            act_name=_("删除polaris"), act_component_code=ExecNameServiceDeleteComponent.code, kwargs=kwargs
        )

        # 运行流程
        pipeline.run_pipeline()
