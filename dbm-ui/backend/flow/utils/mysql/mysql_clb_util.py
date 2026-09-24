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
from dataclasses import asdict
from typing import List, Optional

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.name_service.mysql_clb_comp import (
    ClbOperationType,
    MySQLClbOperationComponent,
)
from backend.flow.utils.name_service.name_service_dataclass import MySQLClbActKwargs, TransDataKwargs


def build_mysql_clb_apply_subs(
    root_id: str,
    data: dict,
    bk_biz_id: int,
    domain_name: str,
    creator: str,
    apply_clb: bool = False,
    spider_role: Optional[str] = None,
) -> List:
    """
    MySQL/TenDBCluster 集群部署成功后，根据单据传参决定是否构建创建CLB的子流程。
    该函数需要在「建立集群元数据」活动节点之后调用，因为创建CLB依赖集群及其proxy/spider已经落库。
    返回的子流程(SubProcess)可直接通过 add_parallel_sub_pipeline 挂接。
    @param root_id: 当前flow的root_id
    @param data: 当前flow的全局参数(即self.data)
    @param bk_biz_id: 业务id
    @param domain_name: 集群主域名，集群刚创建时ticket/flow上下文中还没有cluster_id，
                         需要通过bk_biz_id+domain_name在节点执行态实时解析出cluster_id
    @param creator: 单据创建人
    @param apply_clb: 是否需要给集群创建clb，默认False
    @param spider_role: TenDBCluster 的 spider 角色；TenDBHA 不传
    @return: 子流程(SubProcess)列表，不需要创建clb时返回空列表
    """
    if not apply_clb:
        return []

    clb_sub_pipeline = SubBuilder(root_id=root_id, data=data)
    ns_kwargs = MySQLClbActKwargs()
    ns_kwargs.bk_biz_id = bk_biz_id
    ns_kwargs.domain_name = domain_name
    ns_kwargs.creator = creator
    ns_kwargs.role = spider_role
    ns_kwargs.set_trans_data_dataclass = TransDataKwargs.__name__

    ns_kwargs.name_service_operation_type = ClbOperationType.CREATE_CLB.value
    clb_sub_pipeline.add_act(
        act_name=_("创建clb"),
        act_component_code=MySQLClbOperationComponent.code,
        kwargs=asdict(ns_kwargs),
    )
    ns_kwargs.name_service_operation_type = ClbOperationType.ADD_CLB_INFO_TO_META.value
    clb_sub_pipeline.add_act(
        act_name=_("clb信息写入meta"),
        act_component_code=MySQLClbOperationComponent.code,
        kwargs=asdict(ns_kwargs),
    )
    ns_kwargs.name_service_operation_type = ClbOperationType.ADD_CLB_DOMAIN_TO_DNS.value
    clb_sub_pipeline.add_act(
        act_name=_("clb域名添加到dns,clb域名信息写入meta"),
        act_component_code=MySQLClbOperationComponent.code,
        kwargs=asdict(ns_kwargs),
    )
    return [clb_sub_pipeline.build_sub_process(sub_name=_("创建clb-{}").format(domain_name))]
