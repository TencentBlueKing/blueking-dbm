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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.name_service.name_service_dataclass as flow_context
from backend.db_services.plugin.nameservice import clb, polaris
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("json")


class ExecNameServiceOperation(BaseService):
    """
    NameServiceCreate服务
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行创建名字服务功能的函数
        global_data 单据全局变量，格式字典
        kwargs 私有变量
        """

        # 从流程节点中获取变量
        kwargs = data.get_one_of_inputs("kwargs")
        name_service_operation_type = kwargs["name_service_operation_type"]
        trans_data = data.get_one_of_inputs("trans_data")
        creator = kwargs["creator"]
        cluster_id = kwargs["cluster_id"]

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 执行功能
        # clb创建
        if name_service_operation_type == "create_clb":
            res = clb.create_lb_and_register_target(cluster_id=cluster_id)
        # polaris创建
        elif name_service_operation_type == "create_polaris":
            res = polaris.create_service_alias_bind_targets(cluster_id=cluster_id)
        # clb删除
        elif name_service_operation_type == "delete_clb":
            res = clb.deregister_target_and_delete_lb(cluster_id=cluster_id)
        # polaris删除
        elif name_service_operation_type == "delete_polaris":
            res = polaris.unbind_targets_delete_alias_service(kwargs["cluster_id"])
        # clb信息写入meta
        elif name_service_operation_type == "add_clb_info_to_meta":
            res = clb.add_clb_info_to_meta(output=trans_data, cluster_id=cluster_id, creator=creator)
        # 从meta删除clb信息
        elif name_service_operation_type == "delete_clb_info_from_meta":
            res = clb.delete_clb_info_from_meta(output=trans_data, cluster_id=cluster_id)
        # polaris信息写入meta
        elif name_service_operation_type == "add_polaris_info_to_meta":
            res = polaris.add_polaris_info_to_meta(output=trans_data, cluster_id=cluster_id, creator=creator)
        # 从meta删除polaris信息
        elif name_service_operation_type == "delete_polaris_info_from_meta":
            res = polaris.delete_polaris_info_from_meta(output=trans_data, cluster_id=cluster_id)
        # 添加clb域名到dns，clb域名信息写入meta
        elif name_service_operation_type == "add_clb_domain_to_dns":
            res = clb.add_clb_domain_to_dns(cluster_id=cluster_id, creator=creator)
        # 从dns删除clb域名，从meta中删除clb域名信息
        elif name_service_operation_type == "delete_clb_domain_from_dns":
            res = clb.delete_clb_domain_from_dns(cluster_id=cluster_id)
        # 主域名绑定clb ip
        elif name_service_operation_type == "domain_bind_clb_ip":
            res = clb.immute_domain_clb_ip(cluster_id=cluster_id, creator=creator, bind=True)
        # 主域名解绑clb ip
        elif name_service_operation_type == "domain_unbind_clb_ip":
            res = clb.immute_domain_clb_ip(cluster_id=cluster_id, creator=creator, bind=False)
        else:
            self.log_error("{} does not support error!".format(name_service_operation_type))
            return False

        # 定义流程节点输出参数值
        trans_data = res
        if res["code"] == 0:
            self.log_info("task:{} execute successfully".format(name_service_operation_type))
            data.outputs["trans_data"] = trans_data
            return True

        self.log_error("task:{} execute fail, error:{}".format(name_service_operation_type, res["message"]))
        return False

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExecNameServiceOperationComponent(Component):
    """
    ExecNameServiceOperation组件
    """

    name = __name__
    code = "name_service_operation"
    bound_service = ExecNameServiceOperation
