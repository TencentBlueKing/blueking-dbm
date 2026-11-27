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

from typing import Dict, List, Type

from django.utils.translation import gettext as _
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.models import Cluster
from backend.db_monitor.constants import TargetLevel
from backend.db_monitor.models import MonitorPolicy, NoticeGroup
from backend.db_monitor.utils import parse_shield_description_biz
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.exceptions import ActionNotExistError
from backend.iam_app.handlers.drf_perm.base import (
    BizDBTypeResourceActionPermission,
    BizOrGlobalResourceActionPermission,
    MoreResourceActionPermission,
    ResourceActionPermission,
    get_alarm_shield_request_key_id,
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
        if view.action in ["list"]:
            self.actions = [ActionEnum.DB_MANAGE]
            self.resource_meta = ResourceEnum.BUSINESS
            return [get_request_key_id(request, key="bk_biz_id")]
        elif view.action in ["partial_update", "update", "destroy", "create"]:
            if view.action == "create":
                bk_biz_id = get_request_key_id(request, key="bk_biz_id")
            else:
                notify_group = NoticeGroup.objects.get(id=view.kwargs.get("pk"))
                bk_biz_id = notify_group.bk_biz_id
            if bk_biz_id:
                self.actions = [ActionEnum.NOTIFY_GROUP_MANAGE]
                self.resource_meta = ResourceEnum.BUSINESS
                return [bk_biz_id]
            else:
                self.actions = []
                self.resource_meta = None
                return []
        else:
            raise ActionNotExistError(_("不合法的告警组任务ID：{}").format(view.action))

    def has_object_permission(self, request, view, obj):
        """告警组粒度是业务级别，无需obj鉴权"""
        return True


def get_request_data(request) -> dict:
    """统一获取请求体，兼容非字典结构的 data"""
    return request.data if isinstance(request.data, dict) else {}


def to_int(value, default: int = 0) -> int:
    """安全转换为整数"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_monitor_policy(policy_id) -> MonitorPolicy:
    """获取策略，ID 非法或不存在时返回 None（交由视图统一返回 404）"""
    try:
        return MonitorPolicy.objects.filter(id=int(policy_id)).first()
    except (TypeError, ValueError):
        return None


def parse_monitor_policy_ids(policy_ids) -> List[int]:
    """过滤出合法的策略ID，非法值交由序列化器兜底报错"""
    if not isinstance(policy_ids, (list, tuple)):
        return []

    result = []
    for policy_id in policy_ids:
        try:
            result.append(int(policy_id))
        except (TypeError, ValueError):
            continue

    return result


def get_default_db_type() -> str:
    """策略 DB 类型的默认值（创建策略时未指定 DB 类型则按默认值鉴权）"""
    return MonitorPolicy._meta.get_field("db_type").default


class MonitorPolicyListPermission(ResourceActionPermission):
    """
    策略列表鉴权：平台视角（bk_biz_id=0）不做业务鉴权，业务视角要求业务管理权限
    """

    def __init__(self):
        super().__init__([ActionEnum.DB_MANAGE], ResourceEnum.BUSINESS, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        bk_biz_id = request.query_params.get("bk_biz_id")
        # 缺失 bk_biz_id 时列表不会按业务过滤，必须直接拒绝，避免返回全部业务的策略
        if bk_biz_id in (None, ""):
            raise ValidationError(_("参数 bk_biz_id 不能为空"))

        bk_biz_id = to_int(bk_biz_id)
        return [bk_biz_id] if bk_biz_id > 0 else []


class MonitorPolicyCreatePermission(BizDBTypeResourceActionPermission):
    """
    创建策略鉴权：
    - 平台级策略（不传 bk_biz_id 或为 0）由后台同步生成，不允许通过接口创建
    - 业务级策略按（业务, DB类型）校验策略管理权限
    """

    def __init__(self):
        super().__init__(
            [ActionEnum.MONITOR_POLICY_MANAGE],
            instance_biz_getter=self.instance_biz_getter,
            instance_dbtype_getter=self.instance_dbtype_getter,
        )

    def has_permission(self, request, view):
        if not self.get_bk_biz_id(request):
            raise PermissionDenied(_("平台级告警策略不支持通过接口创建，请指定业务ID"))

        return super().has_permission(request, view)

    @staticmethod
    def get_bk_biz_id(request) -> int:
        bk_biz_id = to_int(get_request_data(request).get("bk_biz_id"))
        return bk_biz_id if bk_biz_id > 0 else 0

    def instance_biz_getter(self, request, view):
        return [self.get_bk_biz_id(request)]

    def instance_dbtype_getter(self, request, view):
        return [get_request_data(request).get("db_type") or get_default_db_type()]


class MonitorPolicyRetrievePermission(ResourceActionPermission):
    """
    策略详情鉴权：业务策略要求策略所属业务的管理权限；
    平台策略与列表的平台视角一致，不做业务鉴权
    """

    def __init__(self):
        super().__init__([ActionEnum.DB_MANAGE], ResourceEnum.BUSINESS, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        policy = get_monitor_policy(view.kwargs.get("pk"))
        return [policy.bk_biz_id] if policy and policy.bk_biz_id else []


class MonitorPolicyManagePermission(MoreResourceActionPermission):
    """
    单个策略的编辑/启停/删除鉴权，按策略归属决定动作与资源：
    - 业务策略：（业务, DB类型）的 MONITOR_POLICY_MANAGE
    - 平台策略：DB类型的 GLOBAL_ALARM_POLICY_MANAGE
    """

    def __init__(self):
        super().__init__(
            [ActionEnum.MONITOR_POLICY_MANAGE],
            [ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
            self.instance_ids_getter,
        )

    def instance_ids_getter(self, request, view):
        # 资源类型在 getter 中动态调整：MoreResourceActionPermission 会先取资源ID，再按 resource_metes 构造资源
        policy = get_monitor_policy(view.kwargs.get("pk"))
        # 策略不存在时不做鉴权，由 get_object() 返回 404
        if policy is None:
            self.actions = []
            return []

        # 平台策略没有所属业务，只按 DB 类型校验全局告警策略管理权限
        if not policy.bk_biz_id:
            self.actions = [ActionEnum.GLOBAL_ALARM_POLICY_MANAGE]
            self.resource_metes = [ResourceEnum.DBTYPE]
            return [(policy.db_type,)]

        self.actions = [ActionEnum.MONITOR_POLICY_MANAGE]
        self.resource_metes = [ResourceEnum.BUSINESS, ResourceEnum.DBTYPE]
        return [(policy.bk_biz_id, policy.db_type)]


class MonitorPolicyClonePermission(BizDBTypeResourceActionPermission):
    """
    克隆策略鉴权：按目标业务与父策略的DB类型校验策略管理权限
    """

    def __init__(self):
        super().__init__(
            [ActionEnum.MONITOR_POLICY_MANAGE],
            instance_biz_getter=self.instance_biz_getter,
            instance_dbtype_getter=self.instance_dbtype_getter,
        )

    def instance_biz_getter(self, request, view):
        return [get_request_key_id(request, "bk_biz_id")]

    def instance_dbtype_getter(self, request, view):
        policy = get_monitor_policy(get_request_data(request).get("parent_id"))
        return [policy.db_type] if policy else []


class MonitorPolicyBatchDestroyPermission(BizDBTypeResourceActionPermission):
    """
    批量删除策略（patch_destroy）鉴权：逐条按策略所属（业务, DB类型）校验策略管理权限；
    平台策略不会被删除（与删除逻辑一致），无需业务鉴权
    """

    def __init__(self):
        self._biz_policies = None
        super().__init__(
            [ActionEnum.MONITOR_POLICY_MANAGE],
            instance_biz_getter=self.instance_biz_getter,
            instance_dbtype_getter=self.instance_dbtype_getter,
        )

    def get_biz_policies(self, request) -> List[MonitorPolicy]:
        """实际会被删除的业务级策略"""
        if self._biz_policies is None:
            policy_ids = parse_monitor_policy_ids(get_request_data(request).get("ids"))
            self._biz_policies = list(
                MonitorPolicy.objects.filter(id__in=policy_ids, target_level=TargetLevel.APP.value).only(
                    "id", "bk_biz_id", "db_type"
                )
            )

        return self._biz_policies

    def instance_biz_getter(self, request, view):
        return [policy.bk_biz_id for policy in self.get_biz_policies(request) if policy.bk_biz_id]

    def instance_dbtype_getter(self, request, view):
        return [policy.db_type for policy in self.get_biz_policies(request) if policy.bk_biz_id]


class MonitorPolicyBatchUpdateNotifyGroupPermission(BizDBTypeResourceActionPermission):
    """
    批量修改告警组鉴权：按请求的业务 + 每条策略的DB类型校验策略管理权限
    （平台策略会克隆到当前业务，统一按当前业务鉴权；策略归属关系由序列化器校验）
    """

    def __init__(self):
        self._policies = None
        super().__init__(
            [ActionEnum.MONITOR_POLICY_MANAGE],
            instance_biz_getter=self.instance_biz_getter,
            instance_dbtype_getter=self.instance_dbtype_getter,
        )

    def get_policies(self, request) -> List[MonitorPolicy]:
        if self._policies is None:
            notify_groups = get_request_data(request).get("notify_groups")
            policy_ids = parse_monitor_policy_ids(
                [info.get("policy_id") for info in notify_groups if isinstance(info, dict)]
                if isinstance(notify_groups, list)
                else []
            )
            self._policies = list(MonitorPolicy.objects.filter(id__in=policy_ids).only("id", "bk_biz_id", "db_type"))

        return self._policies

    def instance_biz_getter(self, request, view):
        # bk_biz_id 非法（缺失或为 0）时由序列化器直接拒绝请求，此处无需鉴权
        bk_biz_id = to_int(get_request_data(request).get("bk_biz_id"))
        return [bk_biz_id] if bk_biz_id > 0 else []

    def instance_dbtype_getter(self, request, view):
        return [policy.db_type for policy in self.get_policies(request)]


class GlobalMonitorPolicyPermission(ResourceActionPermission):
    """
    全局（平台）监控策略鉴权：资源类型固定为 DB 类型，按策略的DB类型校验
    """

    def __init__(self, actions: List[ActionMeta] = None, policy_id: int = None):
        self.policy_id = policy_id
        super().__init__(
            actions=actions, resource_meta=ResourceEnum.DBTYPE, instance_ids_getter=self.instance_ids_getter
        )

    def instance_ids_getter(self, request, view):
        # 未指定策略ID时，从路由或请求体中解析（兼容 pk/parent_id/policy_id）
        policy_id = self.policy_id
        if policy_id is None:
            request_data = get_request_data(request)
            policy_id = view.kwargs.get("pk") or request_data.get("parent_id") or request_data.get("policy_id")

        policy = get_monitor_policy(policy_id)
        return [policy.db_type] if policy else []

    def has_object_permission(self, request, view, obj):
        """策略鉴权已经在has permission完成了，无需obj鉴权"""
        return True


class MonitorPolicyResetPermission(GlobalMonitorPolicyPermission):
    """
    平台策略恢复初始值鉴权：会影响全平台阈值，按DB类型校验全局告警策略管理权限
    """

    def __init__(self):
        super().__init__(actions=[ActionEnum.GLOBAL_ALARM_POLICY_MANAGE])


# 监控策略（MonitorPolicyViewSet）各动作对应的鉴权类，命中后按请求实例化
MONITOR_POLICY_PERMISSIONS: Dict[str, Type[permissions.BasePermission]] = {
    "list": MonitorPolicyListPermission,
    "create": MonitorPolicyCreatePermission,
    "retrieve": MonitorPolicyRetrievePermission,
    "clone_strategy": MonitorPolicyClonePermission,
    "update_strategy": MonitorPolicyManagePermission,
    "destroy": MonitorPolicyManagePermission,
    "enable": MonitorPolicyManagePermission,
    "disable": MonitorPolicyManagePermission,
    "patch_destroy": MonitorPolicyBatchDestroyPermission,
    "batch_update_notify_group": MonitorPolicyBatchUpdateNotifyGroupPermission,
    "reset": MonitorPolicyResetPermission,
}


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
            self.actions = [ActionEnum.ALERT_SHIELD_MANAGE]
            return [get_alarm_shield_request_key_id(request, "bk_biz_id")]

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


class SaveSubscribePermission(ResourceActionPermission):
    """
    订阅相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        # 固定资源是业务
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        domains = [c["cluster_domain"] for c in get_request_key_id(request, "clusters")]
        cluster_types = [c["cluster_type"] for c in get_request_key_id(request, "clusters")]
        # 订阅不允许跨组件，这里只取第一个集群的类型判断
        self.resource_meta = ResourceEnum.cluster_type_to_resource_meta(cluster_types[0])
        self.actions = [ActionEnum.cluster_type_to_action(cluster_types[0], action_key="subscribe_monitor")]
        # 获取集群ID资源
        cluster_ids = Cluster.objects.filter(immute_domain__in=domains).values_list("id", flat=True)
        return list(cluster_ids)
