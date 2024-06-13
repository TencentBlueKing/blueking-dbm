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

from django.http import JsonResponse
from django.utils.translation import ugettext as _
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DBPrivManagerApi
from backend.db_services.dbpermission.constants import AccountType, PrivilegeType
from backend.db_services.dbpermission.db_account.dataclass import AccountMeta, AccountRuleMeta
from backend.db_services.dbpermission.db_authorize.views import DBAuthorizeViewSet as BaseDBAuthorizeViewSet
from backend.db_services.mysql.permission.authorize.dataclass import (
    HostInAuthorizeFilterMeta,
    MySQLAuthorizeMeta,
    MySQLExcelAuthorizeMeta,
)
from backend.db_services.mysql.permission.authorize.handlers import MySQLAuthorizeHandler
from backend.db_services.mysql.permission.authorize.serializers import (
    GetHostInAuthorizeSerializer,
    IntegrationGrantSerializer,
)
from backend.db_services.mysql.permission.db_account.handlers import MySQLAccountHandler
from backend.exceptions import ApiError, ApiResultError
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")

SWAGGER_TAG = "db_services/permission/authorize"


class DBAuthorizeViewSet(BaseDBAuthorizeViewSet):
    handler = MySQLAuthorizeHandler
    authorize_meta = MySQLAuthorizeMeta
    excel_authorize_meta = MySQLExcelAuthorizeMeta

    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询授权主机的信息"),
        query_serializer=GetHostInAuthorizeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetHostInAuthorizeSerializer)
    def get_host_in_authorize(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, HostInAuthorizeFilterMeta, self.handler.get_host_in_authorize.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("MySQL集成授权"),
        request_body=IntegrationGrantSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=IntegrationGrantSerializer)
    def integration_grant(self, request, bk_biz_id):
        """
        集成授权，结合创建账号、创建规则、授权规则，实现一键集成授权
        目前提供给 blueking(398) 和 website(159) 两个平台在使用，暂不考虑对外扩展
        """
        data = self.params_validate(self.get_serializer_class())
        username = data["user_name"]
        password = data["password"]
        client_hosts = data["client_hosts"]
        client_version = data["client_version"]
        db_hosts = data["db_hosts"]
        db_name = data["db_name"]
        privilege = {"dml": [], "ddl": [], "global": []}
        for priv in data["privileges"].split(","):
            pri_type = PrivilegeType.get_enum_class_name(priv.lower(), PrivilegeType.MySQL)
            privilege[pri_type.lower()].append(priv.lower())
        account_handler = MySQLAccountHandler(bk_biz_id=bk_biz_id, account_type=AccountType.MYSQL)
        # 1. 创建账号
        try:
            account_id = account_handler.create_account(AccountMeta(user=username, password=password))["id"]
        except ApiResultError as err:
            account_data = DBPrivManagerApi.get_account(
                params={"bk_biz_id": bk_biz_id, "cluster_type": AccountType.MYSQL.value, "user_like": username}
            )["results"]
            account = {info["user"]: info for info in account_data}.get(username)
            if not account:
                logger.error(f"get or create account[{username}] error, {err}")
                raise err
            account_id = account["id"]

        # 2. 创建账号规则
        try:
            account_handler.add_account_rule(
                AccountRuleMeta(account_id=account_id, privilege=privilege, access_db=db_name)
            )
        except ApiResultError as err:
            logger.error(f"add_account_rule[user:{username}, db_name:{db_name}] error, {err}")

        # 3. 进行授权
        try:
            grant_result = MySQLAuthorizeHandler(bk_biz_id, request.user.username).authorize_apply(
                request,
                username,
                db_name,
                client_hosts,
                db_hosts,
                bk_biz_id=bk_biz_id,
                privileges=data["privileges"],
                client_version=client_version,
                password=password,
                operator=request.user.username,
            )
        except ApiError as err:
            msg = f"authorize_apply[user:{username}, db_name:{db_name}, client_hosts:{client_hosts}] error, {err}"
            logger.error(msg)
            return JsonResponse({"msg": msg, "job_id": -1, "code": 1})
        # 兼容老接口
        return JsonResponse({"msg": "", "job_id": grant_result["job_id"], "code": 0})
