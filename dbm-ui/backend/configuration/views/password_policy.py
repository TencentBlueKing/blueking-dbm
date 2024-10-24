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
import json

from celery.schedules import crontab
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DBPrivManagerApi
from backend.configuration.constants import DBPrivSecurityType
from backend.configuration.handlers.password import DBPasswordHandler
from backend.configuration.serializers import (
    GetAdminPasswordSerializer,
    GetMySQLAdminPasswordResponseSerializer,
    GetRandomPasswordSerializer,
    ModifyAdminPasswordSerializer,
    ModifyMySQLPasswordRandomCycleSerializer,
    PasswordPolicySerializer,
    VerifyPasswordResponseSerializer,
    VerifyPasswordSerializer,
)
from backend.db_periodic_task.models import DBPeriodicTask
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.iam_app.handlers.drf_perm.cluster import ModifyClusterPasswordPermission, QueryClusterPasswordPermission

SWAGGER_TAG = _("密码安全策略")


class PasswordPolicyViewSet(viewsets.SystemViewSet):
    pagination_class = None

    action_permission_map = {
        ("get_password_policy", "verify_password_strength", "get_random_password", "query_random_cycle"): [],
        ("modify_admin_password",): [ModifyClusterPasswordPermission()],
        ("query_admin_password",): [QueryClusterPasswordPermission()],
        ("update_password_policy", "modify_random_cycle"): [
            ResourceActionPermission([ActionEnum.PASSWORD_POLICY_SET])
        ],
    }

    @common_swagger_auto_schema(
        operation_summary=_("查询密码安全策略"),
        responses={status.HTTP_200_OK: PasswordPolicySerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def get_password_policy(self, request):
        name = request.GET.get("name", DBPrivSecurityType.MYSQL_PASSWOR.value)
        if name not in DBPrivSecurityType.get_values():
            raise ValueError(_("不支持该name值！"))
        policy = DBPrivManagerApi.get_security_rule({"name": name})
        policy["rule"] = json.loads(policy["rule"])
        return Response(policy)

    @common_swagger_auto_schema(
        operation_summary=_("更新密码安全策略"), request_body=PasswordPolicySerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=PasswordPolicySerializer)
    def update_password_policy(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        data = {"id": validated_data["id"], "operator": request.user.username}
        if validated_data.get("reset"):
            data["reset"] = validated_data["reset"]
        else:
            data["rule"] = json.dumps(validated_data["rule"])
        policy = DBPrivManagerApi.modify_security_rule(data)
        return Response(policy)

    @common_swagger_auto_schema(
        operation_summary=_("校验密码强度规则"),
        request_body=VerifyPasswordSerializer(),
        responses={status.HTTP_200_OK: VerifyPasswordResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=VerifyPasswordSerializer)
    def verify_password_strength(self, request):
        password = self.params_validate(self.get_serializer_class())["password"]
        security_type = self.params_validate(self.get_serializer_class())["security_type"]
        return Response(DBPasswordHandler.verify_password_strength(password=password, security_type=security_type))

    @common_swagger_auto_schema(
        operation_summary=_("获取符合密码强度的字符串"),
        query_serializer=GetRandomPasswordSerializer(),
        responses={status.HTTP_200_OK: VerifyPasswordSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetRandomPasswordSerializer)
    def get_random_password(self, request, *args, **kwargs):
        security_type = self.validated_data["security_type"]
        random_password = DBPasswordHandler.get_random_password(security_type)
        return Response({"password": random_password})

    @common_swagger_auto_schema(
        operation_summary=_("更新密码随机化周期"), request_body=ModifyMySQLPasswordRandomCycleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=ModifyMySQLPasswordRandomCycleSerializer)
    def modify_random_cycle(self, request, *args, **kwargs):
        from backend.db_periodic_task.local_tasks import auto_randomize_password_daily

        crontab_exec = self.params_validate(self.get_serializer_class())["crontab"]
        DBPasswordHandler.modify_periodic_task_run_every(
            run_every=crontab(**crontab_exec), func_name=auto_randomize_password_daily.__name__
        )
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("查询密码随机化周期"),
        responses={status.HTTP_200_OK: ModifyMySQLPasswordRandomCycleSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def query_random_cycle(self, request, *args, **kwargs):
        from backend.db_periodic_task.local_tasks import auto_randomize_password_daily

        task = DBPeriodicTask.objects.get(name__contains=auto_randomize_password_daily.__name__).task
        crontab_exec = {
            "minute": task.crontab.minute,
            "hour": task.crontab.hour,
            "day_of_week": task.crontab.day_of_week,
            "day_of_month": task.crontab.day_of_month,
        }
        return Response({"crontab": crontab_exec})

    @common_swagger_auto_schema(
        operation_summary=_("查询生效实例密码(admin)"),
        request_body=GetAdminPasswordSerializer(),
        responses={status.HTTP_200_OK: GetMySQLAdminPasswordResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetAdminPasswordSerializer, pagination_class=None)
    def query_admin_password(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        if validated_data.get("instances"):
            validated_data["instances"] = validated_data["instances"].split(",")
        return Response(DBPasswordHandler.query_admin_password(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("修改db实例密码(admin)"),
        request_body=ModifyAdminPasswordSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ModifyAdminPasswordSerializer)
    def modify_admin_password(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        validated_data["operator"] = request.user.username
        return Response(DBPasswordHandler.modify_admin_password(**validated_data))
