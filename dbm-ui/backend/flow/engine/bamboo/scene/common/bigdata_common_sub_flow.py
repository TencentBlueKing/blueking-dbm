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

from django.utils.translation import gettext as _

from backend import env
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.common.sa_init import SaInitComponent

"""
定义大数据组件实施流程上可能会用到的子流程，以减少代码的重复率
"""


def sa_init_machine_sub_flow(
    uid: str,
    root_id: str,
    bk_cloud_id: int,
    bk_biz_id: int,
    init_ips: list,
    idle_check_ips: list = None,
    set_dns_ips: list = None,
):
    """
    定义初始化机器的公共子流程，提供给大数据组件新机器的初始化适用，不支持跨云区域/跨业务处理
    @param uid: 流程单据的uid
    @param root_id: flow流程的root_id
    @param bk_cloud_id: 需要操作的机器的对应云区域ID
    @param bk_biz_id: 需要操作的机器的业务ID
    @param init_ips: 需要初始化的机器ip列表
    @param idle_check_ips: 需要做空闲检查的机器ip列表
    @param set_dns_ips: 需要添加DNS解析配置的机器ip列表(暂未实现)
    """
    if not init_ips and not idle_check_ips and not set_dns_ips:
        raise Exception(_("构建init_machine_sub子流程失败，联系系统管理员, init_ips & idle_check_ips & set_dns_ips is null"))

    sub_pipeline = SubBuilder(root_id=root_id, data={"uid": uid})
    # 并行执行空闲检查
    if env.SA_CHECK_TEMPLATE_ID and idle_check_ips:
        sub_pipeline.add_act(
            act_name=_("执行sa空闲检查"),
            act_component_code=CheckMachineIdleComponent.code,
            kwargs={"ips": idle_check_ips, "bk_biz_id": bk_biz_id},
        )

    # 初始化机器
    if env.SA_INIT_TEMPLATE_ID and init_ips:
        # 执行sa初始化
        sub_pipeline.add_act(
            act_name=_("执行sa初始化"),
            act_component_code=SaInitComponent.code,
            kwargs={"ips": init_ips, "bk_biz_id": bk_biz_id},
        )

    return sub_pipeline.build_sub_process(sub_name=_("机器空闲检查及初始化"))
