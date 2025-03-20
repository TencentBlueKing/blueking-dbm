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

from django.utils.translation import ugettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_monitor.models import MonitorPolicy, NoticeGroup
from backend.db_monitor.utils import parse_shield_description_biz
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.exceptions import ActionNotExistError, ResourceNotExistError
from backend.iam_app.handlers.drf_perm.base import (
    BizOrGlobalResourceActionPermission,
    ResourceActionPermission,
    get_request_key_id,
)


class NotifyGroupPermission(ResourceActionPermission):
    """
    告警组相关动作鉴权
    """

    def __init__(self, view_action, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        self.view_action = view_action
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 从业务或告警组后，决定动作和资源类型
        if view.action in ["list", "create"]:
            self.actions = [getattr(ActionEnum, f"NOTIFY_GROUP_{self.view_action.upper()}")]
            self.resource_meta = ResourceEnum.BUSINESS
            return [get_request_key_id(request, key="bk_biz_id")]
        elif view.action in ["partial_update", "update", "destroy"]:
            notify_group = NoticeGroup.objects.get(id=view.kwargs.get("pk"))
            bk_biz_id = notify_group.bk_biz_id
            if view.action == "destroy":
                action = ActionEnum.NOTIFY_GROUP_DESTROY
            else:
                action = ActionEnum.NOTIFY_GROUP_UPDATE if bk_biz_id else ActionEnum.GLOBAL_NOTIFY_GROUP_UPDATE
            self.actions = [action]
            self.resource_meta = ResourceEnum.NOTIFY_GROUP
            return [notify_group.id]
        else:
            raise ActionNotExistError(_("不合法的告警组任务ID：{}").format(view.action))

    def has_object_permission(self, request, view, obj):
        """告警组粒度是业务级别，无需obj鉴权"""
        return True


class MonitorPolicyPermission(ResourceActionPermission):
    """
    监控策略相关动作鉴权
    """

    def __init__(self, view_action, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        self.view_action = view_action
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 获取策略ID后，决定动作和资源类型
        policy_id = view.kwargs.get("pk") or request.data["parent_id"]
        bk_biz_id = str(MonitorPolicy.objects.get(id=policy_id).bk_biz_id)

        if bk_biz_id is None:
            raise ResourceNotExistError(_("未找到策略ID，无法决定告警组相关动作鉴权。请保证参数包含策略ID"))

        if not int(bk_biz_id):
            self.actions = [getattr(ActionEnum, f"GLOBAL_MONITOR_POLICY_{self.view_action.upper()}")]
            self.resource_meta = ResourceEnum.MONITOR_POLICY
        else:
            self.actions = [getattr(ActionEnum, f"MONITOR_POLICY_{self.view_action.upper()}")]
            self.resource_meta = ResourceEnum.MONITOR_POLICY

        return [policy_id]

    def has_object_permission(self, request, view, obj):
        """策略鉴权已经在has permission完成了，无需obj鉴权"""
        return True


class ListAlertEventPermission(BizOrGlobalResourceActionPermission):
    """
    监控事件查看相关鉴权
    """

    def __init__(self, actions=None, resource_meta=None):
        super().__init__(actions, resource_meta)
        self.biz_action = ActionEnum.DB_MANAGE
        self.global_action = ActionEnum.PLATFORM_ALERT_EVENT_VIEW

    def instance_ids_getter(self, request, view):

        # 如果是个人视角查看，则不鉴权
        if request.data.get("self_manage", False) or request.data.get("self_assist", False):
            self.actions = self.resource_meta = None
            return []

        return super().instance_ids_getter(request, view)


class AlertShieldPermission(ResourceActionPermission):
    """
    告警屏蔽相关鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        # 固定资源是业务
        resource_meta = ResourceEnum.BUSINESS
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 创建动作 -- 告警屏蔽创建鉴权
        if view.action == "create":
            self.actions = [ActionEnum.ALERT_SHIELD_CREATE]
            return [get_request_key_id(request, "bk_biz_id")]

        # 从监控获得告警屏蔽详情
        try:
            shield = BKMonitorV3Api.get_shield({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "id": view.kwargs["pk"]})
            bk_biz_id = parse_shield_description_biz(shield["description"])
        except Exception:  # pylint: disable=broad-except
            bk_biz_id = env.DBA_APP_BK_BIZ_ID

        # 详情 -- 业务管理; 禁用、编辑 -- 告警屏蔽管理
        if view.action == "retrieve":
            self.actions = [ActionEnum.DB_MANAGE]
        elif view.action in ["disable", "update"]:
            self.actions = [ActionEnum.ALERT_SHIELD_MANAGE]

        return [bk_biz_id]
