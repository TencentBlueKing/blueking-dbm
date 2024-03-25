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
import base64
import json

from celery.schedules import crontab
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DBPrivManagerApi
from backend.configuration.constants import DBM_PASSWORD_SECURITY_NAME
from backend.configuration.handlers.password import DBPasswordHandler
from backend.configuration.serializers import (
    GetMySQLAdminPasswordResponseSerializer,
    GetMySQLAdminPasswordSerializer,
    ModifyMySQLAdminPasswordSerializer,
    ModifyMySQLPasswordRandomCycleSerializer,
    PasswordPolicySerializer,
    VerifyPasswordResponseSerializer,
    VerifyPasswordSerializer,
)
from backend.db_periodic_task.models import DBPeriodicTask
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission

SWAGGER_TAG = _("密码安全策略")


class PasswordPolicyViewSet(viewsets.SystemViewSet):
    pagination_class = None

    def _get_custom_permissions(self):
        if self.action == [
            self.get_password_policy.__name__,
            self.verify_password_strength.__name__,
            self.get_random_password.__name__,
            self.query_random_cycle.__name__,
        ]:
            return []
        return [ResourceActionPermission([ActionEnum.PASSWORD_POLICY_SET])]

    @common_swagger_auto_schema(
        operation_summary=_("查询密码安全策略"),
        responses={status.HTTP_200_OK: PasswordPolicySerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def get_password_policy(self, request):
        policy = DBPrivManagerApi.get_security_rule({"name": DBM_PASSWORD_SECURITY_NAME})
        policy["rule"] = json.loads(policy["rule"])
        return Response(policy)

    @common_swagger_auto_schema(
        operation_summary=_("更新密码安全策略"), request_body=PasswordPolicySerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=PasswordPolicySerializer)
    def update_password_policy(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        policy = DBPrivManagerApi.modify_security_rule(
            {"rule": json.dumps(validated_data["rule"]), "id": validated_data["id"], "operator": request.user.username}
        )
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
        return Response(DBPasswordHandler.verify_password_strength(password))

    @common_swagger_auto_schema(
        operation_summary=_("获取符合密码强度的字符串"),
        responses={status.HTTP_200_OK: VerifyPasswordSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def get_random_password(self, request, *args, **kwargs):
        random_password = DBPrivManagerApi.get_random_string({"security_rule_name": DBM_PASSWORD_SECURITY_NAME})
        random_password = base64.b64decode(random_password).decode("utf-8")
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
        operation_summary=_("查询mysql生效实例密码(admin)"),
        query_serializer=GetMySQLAdminPasswordSerializer(),
        responses={status.HTTP_200_OK: GetMySQLAdminPasswordResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetMySQLAdminPasswordSerializer, pagination_class=None)
    def query_mysql_admin_password(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        if validated_data.get("instances"):
            validated_data["instances"] = validated_data["instances"].split(",")
        return Response(DBPasswordHandler.query_mysql_admin_password(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("修改db实例密码(admin)"),
        request_body=ModifyMySQLAdminPasswordSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ModifyMySQLAdminPasswordSerializer)
    def modify_admin_password(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        validated_data["operator"] = request.user.username
        return Response(DBPasswordHandler.modify_admin_password(**validated_data))
