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
from collections import Counter

from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.transfer_host_across_biz import (
    TransferHostAcrossBizInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.transfer_host_to_idlemodule import (
    TransferHostToIdlemoduleInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.update_hosts_operator import (
    UpdateHostsOperatorInputSerializer,
)


def update_hosts_operator_plan_checker(
    plan_slz: UpdateHostsOperatorInputSerializer, requested_slz: UpdateHostsOperatorInputSerializer
):
    plan = plan_slz.validated_data
    requested = requested_slz.validated_data
    if (
        Counter(plan["bk_host_ids"]) != Counter(requested["bk_host_ids"])
        or Counter(plan["operators"]) != Counter(requested["operators"])
        or Counter(plan["bak_operators"]) != Counter(requested["bak_operators"])
    ):
        raise Exception(
            f"The request parameters do not match those registered in the plan. "
            f"plan params: {plan_slz.data}, but received: {requested_slz.data}. "
            f"You must call this tool with exactly the same parameters you announced, "
            f"or create a new plan via `register_callee_plan` with the correct parameters."
        )


def transfer_host_to_idlemodule_plan_checker(
    plan_slz: TransferHostToIdlemoduleInputSerializer, requested_slz: TransferHostToIdlemoduleInputSerializer
):
    plan = plan_slz.validated_data
    requested = requested_slz.validated_data
    if plan["bk_biz_id"] != requested["bk_biz_id"] or Counter(plan["bk_host_ids"]) != Counter(
        requested["bk_host_ids"]
    ):
        raise Exception(
            f"The request parameters do not match those registered in the plan. "
            f"plan params: {plan_slz.data}, but received: {requested_slz.data}. "
            f"You must call this tool with exactly the same parameters you announced, "
            f"or create a new plan via `register_callee_plan` with the correct parameters."
        )


def transfer_host_across_biz_plan_checker(
    plan_slz: TransferHostAcrossBizInputSerializer, requested_slz: TransferHostAcrossBizInputSerializer
):
    plan = plan_slz.validated_data
    requested = requested_slz.validated_data
    if (
        plan["src_bk_biz_id"] != requested["src_bk_biz_id"]
        or plan["dst_bk_biz_id"] != requested["dst_bk_biz_id"]
        or Counter(plan["bk_host_ids"]) != Counter(requested["bk_host_ids"])
    ):
        raise Exception(
            f"The request parameters do not match those registered in the plan. "
            f"plan params: {plan_slz.data}, but received: {requested_slz.data}. "
            f"You must call this tool with exactly the same parameters you announced, "
            f"or create a new plan via `register_callee_plan` with the correct parameters."
        )
