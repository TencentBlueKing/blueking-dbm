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

from typing import List

from backend.db_services.risk_memo.models.risk_memo import RiskMemo, RiskMemoFollowUp
from backend.iam_app.dataclass import ResourceEnum, ResourceMeta
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.handlers.drf_perm.base import (
    BizOrGlobalResourceActionPermission,
    ResourceActionPermission,
    get_request_key_id,
)


class ListRiskMemoPermission(BizOrGlobalResourceActionPermission):
    """
    风险备忘录查看相关鉴权
    """

    def __init__(self, actions=None, resource_meta=None, bk_biz_id: int = None):
        super().__init__(actions, resource_meta)
        self.bk_biz_id = bk_biz_id
        self.biz_action = ActionEnum.DB_MANAGE
        self.global_action = ActionEnum.PLATFROM_RISK_MEMO_VIEW

    def instance_ids_getter(self, request, view):

        # 如果是个人视角查看，则不鉴权
        if "platform" not in request.query_params:
            self.actions = self.resource_meta = None
            return []

        return super().instance_ids_getter(request, view)


class RiskMemoPermission(ResourceActionPermission):
    """
    风险备忘录相关鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        # 固定资源是业务
        resource_meta = ResourceEnum.BUSINESS
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 创建动作 -- 风险备忘录创建
        if view.action == "create":
            self.actions = [ActionEnum.RISK_MEMO_CREATE]
            return [get_request_key_id(request, "bk_biz_id")]
        # 更新 -- 风险备忘录管理
        if view.action in ["update", "update_risk_status"]:
            self.actions = [ActionEnum.RISK_MEMO_MANAGE]
            risk = RiskMemo.objects.get(id=view.kwargs["pk"])
            return [risk.bk_biz_id]

        return []


class RiskFollowUpPermission(ResourceActionPermission):
    """
    风险跟进相关鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        # 固定资源是业务
        actions = [ActionEnum.RISK_MEMO_MANAGE]
        resource_meta = ResourceEnum.BUSINESS
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 新建跟进 -- 风险管理
        if view.action == "create":
            risk_id = get_request_key_id(request, "risk")
            risk = RiskMemo.objects.get(id=risk_id)
            return [risk.bk_biz_id]

        # 更新/删除跟进 -- 风险管理
        if view.action in ["update", "partial_update", "destroy"]:
            follow_up = RiskMemoFollowUp.objects.select_related("risk").get(id=view.kwargs["pk"])
            return [follow_up.risk.bk_biz_id]

        return []
