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

from django.utils.translation import ugettext as _

from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.exceptions import ActionNotExistError
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id

logger = logging.getLogger("root")


class AccountPermission(ResourceActionPermission):
    """
    账号相关动作鉴权
    """

    def __init__(
        self, account_type: str, view_action: str, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None
    ) -> None:
        self.account_type = account_type
        self.view_action = view_action
        super().__init__(actions, resource_meta, self.instance_id_getter)

    def instance_id_getter(self, request, view):
        try:
            self.actions = [getattr(ActionEnum, f"{self.account_type}_{self.view_action}".upper())]
        except AttributeError:
            ActionNotExistError(_("账号动作:{} 不存在/未实现").format(self.view_action))
        # 只有创建账号的动作是业务的，剩下对账号的操作都是以账号为维度的
        if self.view_action == "create_account":
            self.resource_meta = ResourceEnum.BUSINESS
            return [get_request_key_id(request, "bk_biz_id")]
        else:
            self.resource_meta = getattr(ResourceEnum, f"{self.account_type.upper()}_ACCOUNT")
            return [get_request_key_id(request, "account_id")]
