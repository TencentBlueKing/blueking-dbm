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

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.name_service.mysql_clb_comp import (
    ClbOperationType,
    MySQLClbOperationComponent,
)
from backend.flow.utils.name_service.name_service_dataclass import MySQLClbActKwargs, TransDataKwargs

logger = logging.getLogger("flow")


class MySQLClbFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data
        self.kwargs = MySQLClbActKwargs()
        self.kwargs.set_trans_data_dataclass = TransDataKwargs.__name__
        self.kwargs.cluster_id = self.data["cluster_id"]
        self.kwargs.creator = self.data["created_by"]
        # role 入参是 spider role 区分是建立spider master clb 还是建立spider slave clb
        self.kwargs.role = self.data.get("spider_role", TenDBClusterSpiderRole.SPIDER_MASTER)

    def clb_create_flow(self):
        """
        clb create流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 添加创建clb活动节点
        self.kwargs.name_service_operation_type = ClbOperationType.CREATE_CLB.value
        pipeline.add_act(
            act_name=_("创建clb"), act_component_code=MySQLClbOperationComponent.code, kwargs=asdict(self.kwargs)
        )
        self.kwargs.name_service_operation_type = ClbOperationType.ADD_CLB_INFO_TO_META.value
        pipeline.add_act(
            act_name=_("clb信息写入meta"),
            act_component_code=MySQLClbOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )
        self.kwargs.name_service_operation_type = ClbOperationType.ADD_CLB_DOMAIN_TO_DNS.value
        pipeline.add_act(
            act_name=_("clb域名添加到dns,clb域名信息写入meta"),
            act_component_code=MySQLClbOperationComponent.code,
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
        self.kwargs.name_service_operation_type = ClbOperationType.DOMAIN_UNBIND_CLB_IP.value
        pipeline.add_act(
            act_name=_("主域名解绑clb ip"),
            act_component_code=MySQLClbOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )
        self.kwargs.name_service_operation_type = ClbOperationType.DELETE_CLB_DOMAIN_FROM_DNS.value
        pipeline.add_act(
            act_name=_("dns删除clb域名,从meta删除clb域名信息"),
            act_component_code=MySQLClbOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )
        self.kwargs.name_service_operation_type = ClbOperationType.DELETE_CLB.value
        pipeline.add_act(
            act_name=_("删除clb"), act_component_code=MySQLClbOperationComponent.code, kwargs=asdict(self.kwargs)
        )
        self.kwargs.name_service_operation_type = ClbOperationType.DELETE_CLB_INFO_FROM_META.value
        pipeline.add_act(
            act_name=_("从meta删除clb信息"),
            act_component_code=MySQLClbOperationComponent.code,
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
        self.kwargs.name_service_operation_type = ClbOperationType.DOMAIN_BIND_CLB_IP.value
        pipeline.add_act(
            act_name=_("主域名绑定clb ip"),
            act_component_code=MySQLClbOperationComponent.code,
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
        self.kwargs.name_service_operation_type = ClbOperationType.DOMAIN_UNBIND_CLB_IP.value
        pipeline.add_act(
            act_name=_("主域名解绑clb ip"),
            act_component_code=MySQLClbOperationComponent.code,
            kwargs=asdict(self.kwargs),
        )

        # 运行流程
        pipeline.run_pipeline()
