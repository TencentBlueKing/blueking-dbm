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

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.name_service.name_service import ExecNameServiceOperationComponent
from backend.flow.utils.name_service.name_service_dataclass import ActKwargs, TransDataKwargs

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
        self.kwargs = ActKwargs()
        self.kwargs.set_trans_data_dataclass = TransDataKwargs.__name__
        self.kwargs.cluster_id = self.data["cluster_id"]
        self.kwargs.creator = self.data["created_by"]

    def clb_create_flow(self):
        """
        clb create流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 添加创建clb活动节点
        self.kwargs.name_service_operation_type = "create_clb"
        pipeline.add_act(
            act_name=_("创建clb"), act_component_code=ExecNameServiceOperationComponent.code, kwargs=asdict(self.kwargs)
        )
        self.kwargs.name_service_operation_type = "add_clb_info_to_meta"
        pipeline.add_act(
            act_name=_("clb信息写入meta"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )
        self.kwargs.name_service_operation_type = "add_clb_domain_to_dns"
        pipeline.add_act(
            act_name=_("clb域名添加到dns，clb域名信息写入meta"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )

        # 运行流程
        pipeline.run_pipeline()

    def clb_delete_flow(self):
        """
        clb delete流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 添加活动节点
        self.kwargs.name_service_operation_type = "domain_unbind_clb_ip"
        pipeline.add_act(
            act_name=_("主域名解绑clb ip"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )
        self.kwargs.name_service_operation_type = "delete_clb_domain_from_dns"
        pipeline.add_act(
            act_name=_("dns删除clb域名，从meta删除clb域名信息"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )
        self.kwargs.name_service_operation_type = "delete_clb"
        pipeline.add_act(
            act_name=_("删除clb"), act_component_code=ExecNameServiceOperationComponent.code, kwargs=asdict(self.kwargs)
        )
        self.kwargs.name_service_operation_type = "delete_clb_info_from_meta"
        pipeline.add_act(
            act_name=_("从meta删除clb信息"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )

        # 运行流程
        pipeline.run_pipeline()

    def polaris_create_flow(self):
        """
        polaris create流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 添加活动节点
        self.kwargs.name_service_operation_type = "create_polaris"
        pipeline.add_act(
            act_name=_("创建polaris"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )
        self.kwargs.name_service_operation_type = "add_polaris_info_to_meta"
        pipeline.add_act(
            act_name=_("polaris信息写入meta"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )

        # 运行流程
        pipeline.run_pipeline()

    def polaris_delete_flow(self):
        """
        polaris delete流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 添加活动节点
        self.kwargs.name_service_operation_type = "delete_polaris"
        pipeline.add_act(
            act_name=_("删除polaris"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )
        self.kwargs.name_service_operation_type = "delete_polaris_info_from_meta"
        pipeline.add_act(
            act_name=_("从meta删除polaris信息"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )

        # 运行流程
        pipeline.run_pipeline()

    def immute_domain_bind_clb_ip(self):
        """
        主域名绑定clb ip流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 添加活动节点
        self.kwargs.name_service_operation_type = "domain_bind_clb_ip"
        pipeline.add_act(
            act_name=_("主域名绑定clb ip"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )

        # 运行流程
        pipeline.run_pipeline()

    def immute_domain_unbind_clb_ip(self):
        """
        主域名绑定clb ip流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 添加活动节点
        self.kwargs.name_service_operation_type = "domain_unbind_clb_ip"
        pipeline.add_act(
            act_name=_("主域名解绑clb ip"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )

        # 运行流程
        pipeline.run_pipeline()
