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
from contextlib import contextmanager
from unittest.mock import ANY, Mock, patch

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from backend.db_monitor.constants import TargetLevel
from backend.db_monitor.mock_data import CREATE_POLICY
from backend.db_monitor.models import MonitorPolicy
from backend.db_monitor.serializers import BatchUpdateMonitorPolicyNotifySerializer, MonitorPolicyCreateSerializer
from backend.db_monitor.views.policy import MonitorPolicyViewSet
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.exceptions import PermissionDeniedError
from backend.tests.mock_data.db_monitor.bkmonitorv3 import BKMonitorV3MockApi
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db
client = APIClient()
client.login(username="admin")

IAM_PERMISSION_PATH = "backend.iam_app.handlers.drf_perm.base.Permission"
IAM_SKIP_PATH = "backend.iam_app.handlers.drf_perm.base.env.BK_IAM_SKIP"
ADD_AUDIT_EVENT_PATH = "backend.iam_app.handlers.drf_perm.base.IAMPermission.add_audit_event"


@contextmanager
def patched_iam():
    """替换IAM客户端, 便于断言鉴权动作与资源"""
    with (
        patch(IAM_PERMISSION_PATH) as permission,
        patch(ADD_AUDIT_EVENT_PATH),
        patch(IAM_SKIP_PATH, False),
    ):
        yield permission


def make_view(action, data=None, kwargs=None, query_params=None):
    view = MonitorPolicyViewSet()
    view.action = action
    view.kwargs = kwargs or {}
    view.request = Mock(
        method="GET" if query_params is not None else "POST",
        data={} if data is None else data,
        query_params={} if query_params is None else query_params,
        parser_context={"kwargs": kwargs or {}},
        user=Mock(is_superuser=False),
    )
    return view


@pytest.fixture
def policies(db):
    """准备平台策略 + 两个不同业务的业务级策略(绕过save, 避免请求监控平台)"""
    definitions = [
        {"name": "plat-policy", "bk_biz_id": 0, "db_type": "mysql", "target_level": TargetLevel.PLATFORM.value},
        {"name": "biz1-mysql-policy", "bk_biz_id": 1, "db_type": "mysql", "target_level": TargetLevel.APP.value},
        {"name": "biz2-redis-policy", "bk_biz_id": 2, "db_type": "redis", "target_level": TargetLevel.APP.value},
    ]
    MonitorPolicy.objects.bulk_create(
        [
            MonitorPolicy(creator="admin", updater="admin", target_priority=0, **definition)
            for definition in definitions
        ]
    )
    return {policy.name: policy for policy in MonitorPolicy.objects.filter(name__in=[d["name"] for d in definitions])}


def get_resource_pairs(resources_list):
    """(业务ID, DB类型) 资源对"""
    return {(str(resources[0].id), resources[1].id) for resources in resources_list}


def assert_no_permission_check(view):
    """鉴权类已实例化, 但不应发起 IAM 校验"""
    with patched_iam() as iam:
        for permission in view._get_custom_permissions():
            assert permission.has_permission(view.request, view)

    iam.return_value.is_allowed.assert_not_called()
    iam.return_value.batch_is_allowed.assert_not_called()


@pytest.fixture
@patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
@patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
@patch("backend.db_monitor.models.alarm.bkm_save_alarm_strategy")
def add_policy(mocked_bkm_save_alarm_strategy, db):
    mocked_bkm_save_alarm_strategy.return_value = {"id": 3, "other_details": "mocked response"}
    policy = MonitorPolicy.objects.create(**CREATE_POLICY[0])
    return policy


class TestMonitorPolicyViewSet:
    @pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
    def set_empty_middleware(self):
        with patch.object(settings, "MIDDLEWARE", []):
            yield

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    @patch("backend.db_monitor.models.alarm.bkm_save_alarm_strategy")
    def test_create_policy(self, mocked_bkm_save_alarm_strategy, add_policy):
        mocked_bkm_save_alarm_strategy.return_value = {"id": 3, "other_details": "mocked response"}
        url = "/apis/monitor/policy/"
        response = client.post(url, data={"bk_biz_id": 1, **CREATE_POLICY[1]})
        assert response.status_code == 201
        assert MonitorPolicy.objects.count() == 2

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    def test_create_policy_without_business_rejected(self, add_policy):
        """接口侧不允许创建平台级策略"""
        response = client.post("/apis/monitor/policy/", data=CREATE_POLICY[1], format="json")
        assert response.json()["result"] is False
        assert "bk_biz_id" in response.json()["message"]
        assert MonitorPolicy.objects.count() == 1

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.iam_app.handlers.permission.Permission", PermissionMock)
    def test_list_policies(self, add_policy):
        url = "/apis/monitor/policy/?bk_biz_id=0&db_type=mysql"
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "OK"
        assert MonitorPolicy.objects.count() == 1

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_retrive_policies_details(self, add_policy):
        add_policy_id = add_policy.pk
        url = reverse("policy-detail", kwargs={"pk": add_policy_id})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "OK"

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    @patch("backend.db_monitor.models.alarm.bkm_delete_alarm_strategy")
    def test_delete_policy(self, mocked_bkm_delete_alarm_strategy, add_policy):
        mocked_bkm_delete_alarm_strategy.return_value = None
        add_policy_id = add_policy.pk
        url = "/apis/monitor/policy/"
        response = client.delete(f"{url}{add_policy_id}/")
        assert response.status_code == 200
        assert MonitorPolicy.objects.exists() is False

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_db_module_list(self):
        url = "/apis/monitor/policy/db_module_list/?dbtype=mysql&bk_biz_id=0"
        response = client.get(url)
        assert response.status_code == 200


class TestMonitorPolicyPermission:
    """复核 M-06: 策略接口按策略所属业务鉴权"""

    def test_list_platform_view_requires_no_permission(self):
        view = make_view("list", query_params={"bk_biz_id": "0"})
        assert_no_permission_check(view)

    def test_list_business_view_checks_business_manage(self):
        view = make_view("list", query_params={"bk_biz_id": "1"})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_called_once_with(
            action=ActionEnum.DB_MANAGE, resources=[ANY], is_raise_exception=True
        )
        [resource] = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert (resource.type, resource.id) == (ResourceEnum.BUSINESS.id, "1")

    def test_list_without_business_denied(self):
        """缺少 bk_biz_id 时列表不会按业务过滤, 必须拒绝"""
        view = make_view("list", query_params={})
        [permission] = view._get_custom_permissions()

        with pytest.raises(ValidationError):
            permission.has_permission(view.request, view)

    def test_create_business_policy_checks_policy_business(self):
        view = make_view("create", data={"bk_biz_id": 1, "db_type": "redis"})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_called_once_with(
            action=ActionEnum.MONITOR_POLICY_MANAGE, resources=[ANY, ANY], is_raise_exception=True
        )
        resources = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert {resource.id for resource in resources} == {"1", "redis"}

    def test_create_business_policy_uses_default_db_type(self):
        view = make_view("create", data={"bk_biz_id": 1, "name": "policy"})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        resources = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert {resource.id for resource in resources} == {"1", "mysql"}

    @pytest.mark.parametrize("data", [{}, {"bk_biz_id": 0}, {"bk_biz_id": 0, "db_type": "mysql"}, {"bk_biz_id": None}])
    def test_create_platform_policy_denied(self, data):
        """平台级策略只由后台同步生成, 接口一律不允许创建"""
        view = make_view("create", data=data)

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            with pytest.raises(PermissionDenied):
                permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_not_called()

    def test_retrieve_business_policy_checks_policy_business(self, policies):
        policy = policies["biz1-mysql-policy"]
        view = make_view("retrieve", kwargs={"pk": policy.id})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_called_once_with(
            action=ActionEnum.DB_MANAGE, resources=[ANY], is_raise_exception=True
        )
        [resource] = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert resource.type == ResourceEnum.BUSINESS.id
        assert resource.id == str(policy.bk_biz_id)

    def test_retrieve_platform_policy_requires_no_permission(self, policies):
        """平台策略与 list 保持一致, 不做业务鉴权"""
        view = make_view("retrieve", kwargs={"pk": policies["plat-policy"].id})
        assert_no_permission_check(view)

    def test_retrieve_unknown_policy_requires_no_permission(self):
        view = make_view("retrieve", kwargs={"pk": 0})
        assert_no_permission_check(view)

    @pytest.mark.parametrize("action", ["update_strategy", "destroy", "enable", "disable"])
    def test_manage_business_policy_checks_biz_and_db_type(self, policies, action):
        policy = policies["biz1-mysql-policy"]
        view = make_view(action, kwargs={"pk": policy.id})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_called_once_with(
            action=ActionEnum.MONITOR_POLICY_MANAGE, resources=[ANY, ANY], is_raise_exception=True
        )
        resources = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert {(resource.type, resource.id) for resource in resources} == {
            (ResourceEnum.BUSINESS.id, str(policy.bk_biz_id)),
            (ResourceEnum.DBTYPE.id, policy.db_type),
        }

    def test_manage_platform_policy_requires_global_alarm_policy_manage(self, policies):
        policy = policies["plat-policy"]
        view = make_view("enable", kwargs={"pk": policy.id})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_called_once_with(
            action=ActionEnum.GLOBAL_ALARM_POLICY_MANAGE, resources=[ANY], is_raise_exception=True
        )
        [resource] = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert (resource.type, resource.id) == (ResourceEnum.DBTYPE.id, policy.db_type)

    def test_manage_unknown_policy_requires_no_permission(self):
        """策略不存在时由 get_object() 返回 404, 此处不鉴权"""
        view = make_view("enable", kwargs={"pk": 999999})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            assert permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_not_called()

    def test_clone_strategy_checks_target_business_and_parent_db_type(self, policies):
        view = make_view("clone_strategy", data={"parent_id": policies["plat-policy"].id, "bk_biz_id": 1})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        resources = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert {(resource.type, resource.id) for resource in resources} == {
            (ResourceEnum.BUSINESS.id, "1"),
            (ResourceEnum.DBTYPE.id, "mysql"),
        }

    def test_patch_destroy_checks_every_policy(self, policies):
        policy_ids = [policies["biz1-mysql-policy"].id, policies["biz2-redis-policy"].id]
        view = make_view("patch_destroy", data={"ids": policy_ids})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        iam.return_value.batch_is_allowed.assert_called_once_with(
            actions=[ActionEnum.MONITOR_POLICY_MANAGE], resources_list=ANY, is_raise_exception=True
        )
        assert get_resource_pairs(iam.return_value.batch_is_allowed.call_args.kwargs["resources_list"]) == {
            ("1", "mysql"),
            ("2", "redis"),
        }

    def test_patch_destroy_ignores_non_business_level_policies(self, policies):
        """平台级策略不会被删除(与实际删除逻辑一致), 无需鉴权"""
        view = make_view("patch_destroy", data={"ids": [policies["plat-policy"].id, 999999]})
        assert_no_permission_check(view)

    def test_patch_destroy_ignores_invalid_ids(self):
        view = make_view("patch_destroy", data={"ids": ["abc", None]})
        assert_no_permission_check(view)

    def test_patch_destroy_cross_business_denied(self, policies):
        view = make_view("patch_destroy", data={"ids": [policies["biz2-redis-policy"].id]})

        with patched_iam() as iam:
            iam.return_value.is_allowed.side_effect = PermissionDeniedError(ActionEnum.MONITOR_POLICY_MANAGE.name, [])
            [permission] = view._get_custom_permissions()
            with pytest.raises(PermissionDeniedError):
                permission.has_permission(view.request, view)

    def test_reset_requires_global_alarm_policy_manage(self, policies):
        view = make_view("reset", data={"policy_id": policies["plat-policy"].id})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_called_once_with(
            action=ActionEnum.GLOBAL_ALARM_POLICY_MANAGE, resources=[ANY], is_raise_exception=True
        )
        [resource] = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert resource.type == ResourceEnum.DBTYPE.id
        assert resource.id == policies["plat-policy"].db_type

    def test_reset_requires_no_permission_for_unknown_policy(self):
        view = make_view("reset", data={"policy_id": 999999})

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            assert permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_not_called()

    def test_batch_update_notify_group_checks_body_business(self, policies):
        view = make_view(
            "batch_update_notify_group",
            data={
                "bk_biz_id": 1,
                "notify_groups": [{"policy_id": policies["biz1-mysql-policy"].id, "groups": [1]}],
            },
        )

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        iam.return_value.is_allowed.assert_called_once_with(
            action=ActionEnum.MONITOR_POLICY_MANAGE, resources=[ANY, ANY], is_raise_exception=True
        )
        resources = iam.return_value.is_allowed.call_args.kwargs["resources"]
        assert {resource.type for resource in resources} == {ResourceEnum.BUSINESS.id, ResourceEnum.DBTYPE.id}
        assert {resource.id for resource in resources} == {"1", "mysql"}

    def test_batch_update_notify_group_checks_all_policy_db_types(self, policies):
        """多条策略跨DB类型时, 每条策略的DB类型都要鉴权"""
        MonitorPolicy.objects.bulk_create(
            [
                MonitorPolicy(
                    creator="admin",
                    updater="admin",
                    target_priority=0,
                    name="plat-redis-policy",
                    bk_biz_id=0,
                    db_type="redis",
                    target_level=TargetLevel.PLATFORM.value,
                )
            ]
        )
        plat_redis_policy = MonitorPolicy.objects.get(name="plat-redis-policy")
        view = make_view(
            "batch_update_notify_group",
            data={
                "bk_biz_id": 1,
                "notify_groups": [
                    {"policy_id": policies["plat-policy"].id, "groups": []},
                    {"policy_id": plat_redis_policy.id, "groups": []},
                ],
            },
        )

        with patched_iam() as iam:
            [permission] = view._get_custom_permissions()
            permission.has_permission(view.request, view)

        assert get_resource_pairs(iam.return_value.batch_is_allowed.call_args.kwargs["resources_list"]) == {
            ("1", "mysql"),
            ("1", "redis"),
        }

    def test_batch_update_notify_group_requires_no_permission_with_zero_business(self, policies):
        """bk_biz_id 为 0/缺失时由序列化器直接拒绝, 不再走兜底鉴权"""
        for data in (
            {"bk_biz_id": 0, "notify_groups": [{"policy_id": policies["biz1-mysql-policy"].id, "groups": []}]},
            {"notify_groups": [{"policy_id": policies["biz1-mysql-policy"].id, "groups": []}]},
        ):
            view = make_view("batch_update_notify_group", data=data)
            assert_no_permission_check(view)


class TestBatchUpdateMonitorPolicyNotifySerializer:
    """批量修改告警组: 策略归属校验"""

    def test_reject_zero_bk_biz_id(self, policies):
        serializer = BatchUpdateMonitorPolicyNotifySerializer(
            data={"bk_biz_id": 0, "notify_groups": [{"policy_id": policies["biz1-mysql-policy"].id, "groups": []}]}
        )
        assert not serializer.is_valid()
        assert "bk_biz_id" in serializer.errors

    def test_reject_other_business_policy(self, policies):
        serializer = BatchUpdateMonitorPolicyNotifySerializer(
            data={"bk_biz_id": 1, "notify_groups": [{"policy_id": policies["biz2-redis-policy"].id, "groups": []}]}
        )
        assert not serializer.is_valid()
        assert str(policies["biz2-redis-policy"].id) in str(serializer.errors)

    def test_reject_unknown_policy(self, policies):
        serializer = BatchUpdateMonitorPolicyNotifySerializer(
            data={"bk_biz_id": 1, "notify_groups": [{"policy_id": 999999, "groups": []}]}
        )
        assert not serializer.is_valid()
        assert "999999" in str(serializer.errors)

    def test_allow_platform_and_own_business_policy(self, policies):
        serializer = BatchUpdateMonitorPolicyNotifySerializer(
            data={
                "bk_biz_id": 1,
                "notify_groups": [
                    {"policy_id": policies["plat-policy"].id, "groups": [1]},
                    {"policy_id": policies["biz1-mysql-policy"].id, "groups": [1]},
                ],
            }
        )
        assert serializer.is_valid(), serializer.errors


class TestMonitorPolicyCreateSerializer:
    """创建策略: 接口侧只允许创建业务级策略"""

    @pytest.mark.parametrize("data", [{"name": "policy", "target_priority": 0}, {"bk_biz_id": 0, "name": "policy"}])
    def test_reject_platform_policy(self, data):
        serializer = MonitorPolicyCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "bk_biz_id" in serializer.errors

    def test_allow_business_policy(self):
        serializer = MonitorPolicyCreateSerializer(data={"bk_biz_id": 1, "name": "policy", "target_priority": 0})
        assert serializer.is_valid(), serializer.errors


class TestMonitorPolicyApiPermission:
    """接口级校验: 跨业务被拒, 本业务正常"""

    @pytest.fixture(autouse=True)
    def set_empty_middleware(self):
        with patch.object(settings, "MIDDLEWARE", []):
            yield

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: x._get_custom_permissions())
    @patch(IAM_PERMISSION_PATH, PermissionMock)
    @patch(ADD_AUDIT_EVENT_PATH)
    def test_batch_update_notify_group_cross_business_rejected(self, mocked_add_audit_event, policies):
        response = client.post(
            "/apis/monitor/policy/batch_update_notify_group/",
            data={"bk_biz_id": 1, "notify_groups": [{"policy_id": policies["biz2-redis-policy"].id, "groups": []}]},
            format="json",
        )
        assert response.json()["result"] is False
        assert str(policies["biz2-redis-policy"].id) in response.json()["message"]

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: x._get_custom_permissions())
    @patch(IAM_PERMISSION_PATH, PermissionMock)
    @patch.object(MonitorPolicy, "update", lambda *args, **kwargs: {})
    @patch.object(MonitorPolicy, "clone", lambda *args, **kwargs: {})
    @patch(ADD_AUDIT_EVENT_PATH)
    def test_batch_update_notify_group_own_business_allowed(self, mocked_add_audit_event, policies):
        response = client.post(
            "/apis/monitor/policy/batch_update_notify_group/",
            data={
                "bk_biz_id": 1,
                "notify_groups": [
                    {"policy_id": policies["biz1-mysql-policy"].id, "groups": [1]},
                    {"policy_id": policies["plat-policy"].id, "groups": [1]},
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: x._get_custom_permissions())
    @patch(IAM_PERMISSION_PATH, PermissionMock)
    @patch("backend.db_monitor.models.alarm.bkm_delete_alarm_strategy")
    @patch(ADD_AUDIT_EVENT_PATH)
    def test_patch_destroy_only_removes_own_business_policy(self, mocked_add_audit_event, mocked_bkm_delete, policies):
        biz1_policy_id = policies["biz1-mysql-policy"].id
        biz2_policy_id = policies["biz2-redis-policy"].id

        response = client.post("/apis/monitor/policy/patch_destroy/", data={"ids": [biz1_policy_id]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert not MonitorPolicy.objects.filter(id=biz1_policy_id).exists()
        assert MonitorPolicy.objects.filter(id=biz2_policy_id).exists()

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: x._get_custom_permissions())
    @patch(ADD_AUDIT_EVENT_PATH)
    def test_create_platform_policy_rejected(self, mocked_add_audit_event):
        response = client.post("/apis/monitor/policy/", data={"name": "plat-policy"}, format="json")
        assert response.json()["result"] is False
        assert "平台级告警策略" in response.json()["message"]
        assert not MonitorPolicy.objects.exists()

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: x._get_custom_permissions())
    @patch(IAM_PERMISSION_PATH, PermissionMock)
    @patch("backend.db_monitor.models.alarm.bkm_save_alarm_strategy")
    @patch(ADD_AUDIT_EVENT_PATH)
    def test_create_business_policy_allowed(self, mocked_add_audit_event, mocked_bkm_save_alarm_strategy):
        mocked_bkm_save_alarm_strategy.return_value = {"id": 3, "other_details": "mocked response"}

        response = client.post("/apis/monitor/policy/", data={"bk_biz_id": 1, **CREATE_POLICY[1]}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert MonitorPolicy.objects.filter(bk_biz_id=1, name=CREATE_POLICY[1]["name"]).exists()
