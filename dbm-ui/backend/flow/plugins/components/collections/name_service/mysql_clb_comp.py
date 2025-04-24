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

from django.utils.translation import gettext_lazy as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.name_service.name_service_dataclass as flow_context
from backend.db_services.plugin.nameservice import mysql_clb
from backend.flow.plugins.components.collections.common.base_service import BaseService
from blue_krill.data_types.enum import EnumField, StructuredEnum

logger = logging.getLogger("json")


class ClbOperationType(str, StructuredEnum):
    CREATE_CLB = EnumField("create_clb", _("create_clb"))
    DELETE_CLB = EnumField("delete_clb", _("delete_clb"))
    CLB_REGISTER_PART_TARGET = EnumField("clb_register_part_target", _("clb_register_part_target"))
    CLB_DEREGISTER_PART_TARGET = EnumField("clb_deregister_part_target", _("clb_deregister_part_target"))
    ADD_CLB_INFO_TO_META = EnumField("add_clb_info_to_meta", _("add_clb_info_to_meta"))
    DELETE_CLB_INFO_FROM_META = EnumField("delete_clb_info_from_meta", _("delete_clb_info_from_meta"))
    ADD_CLB_DOMAIN_TO_DNS = EnumField("add_clb_domain_to_dns", _("add_clb_domain_to_dns"))
    DELETE_CLB_DOMAIN_FROM_DNS = EnumField("delete_clb_domain_from_dns", _("delete_clb_domain_from_dns"))
    DOMAIN_BIND_CLB_IP = EnumField("domain_bind_clb_ip", _("domain_bind_clb_ip"))
    DOMAIN_UNBIND_CLB_IP = EnumField("domain_unbind_clb_ip", _("domain_unbind_clb_ip"))


class MySQLClbServiceOperation(BaseService):
    """
    NameServiceCreate服务
    """

    def _execute(self, data, parent_data=None) -> bool:  # 修改：将parent_data设为可选参数
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
        role = kwargs["role"]
        cluster_id = kwargs["cluster_id"]

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 使用字典映射替代多重if-else，提高可读性和维护性
        operation_mapping = {
            # clb创建
            ClbOperationType.CREATE_CLB.value: lambda: mysql_clb.create_lb_and_register_target(
                cluster_id=cluster_id, role=role
            ),
            # clb绑定新ip
            # ips: {ip:port, ...}
            ClbOperationType.CLB_REGISTER_PART_TARGET.value: lambda: mysql_clb.operate_part_target(
                cluster_id=cluster_id, ips=kwargs["ips"], bind=True, role=role
            ),
            # clb解绑部分ip
            ClbOperationType.CLB_DEREGISTER_PART_TARGET.value: lambda: mysql_clb.operate_part_target(
                cluster_id=cluster_id, ips=kwargs["ips"], bind=False, role=role
            ),
            # clb删除
            ClbOperationType.DELETE_CLB.value: lambda: mysql_clb.deregister_target_and_delete_lb(
                cluster_id=cluster_id, role=role
            ),
            # clb信息写入meta
            ClbOperationType.ADD_CLB_INFO_TO_META.value: lambda: mysql_clb.add_clb_info_to_meta(
                output=trans_data,
                cluster_id=cluster_id,
                creator=creator,
                role=role,
            ),
            # 从meta删除clb信息
            ClbOperationType.DELETE_CLB_INFO_FROM_META.value: lambda: mysql_clb.delete_clb_info_from_meta(
                output=trans_data, cluster_id=cluster_id, role=role
            ),
            # 添加clb域名到dns，clb域名信息写入meta
            ClbOperationType.ADD_CLB_DOMAIN_TO_DNS.value: lambda: mysql_clb.add_clb_domain_to_dns(
                cluster_id=cluster_id, creator=creator, role=role
            ),
            # 从dns删除clb域名，从meta中删除clb域名信息
            ClbOperationType.DELETE_CLB_DOMAIN_FROM_DNS.value: lambda: mysql_clb.delete_clb_domain_from_dns(
                cluster_id=cluster_id, role=role
            ),
            # 主域名绑定clb ip
            ClbOperationType.DOMAIN_BIND_CLB_IP.value: lambda: mysql_clb.immute_domain_clb_ip(
                cluster_id=cluster_id, creator=creator, bind=True, role=role
            ),
            # 主域名解绑clb ip
            ClbOperationType.DOMAIN_UNBIND_CLB_IP.value: lambda: mysql_clb.immute_domain_clb_ip(
                cluster_id=cluster_id, creator=creator, bind=False, role=role
            ),
        }

        if name_service_operation_type not in operation_mapping:
            self.log_error("{} unsupported operation type".format(name_service_operation_type))
            return False

        res = operation_mapping[name_service_operation_type]()

        # 定义流程节点输出参数值
        trans_data = res
        if res["code"] == 0:
            data.outputs["trans_data"] = trans_data
            return True

        self.log_error("{}execution failed, errMsg:{}".format(name_service_operation_type, res["message"]))
        return False

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MySQLClbOperationComponent(Component):
    """
    MySQLClbOperation组件
    """

    name = __name__
    code = "mysql_clb_operation"
    bound_service = MySQLClbServiceOperation
