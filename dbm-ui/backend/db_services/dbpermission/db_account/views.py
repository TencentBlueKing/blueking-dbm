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
from typing import Union

from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbpermission.db_account.dataclass import (
    AccountMeta,
    AccountPrivMeta,
    AccountRuleMeta,
    AccountUserMeta,
)
from backend.db_services.dbpermission.db_account.handlers import AccountHandler
from backend.db_services.dbpermission.db_account.serializers import (
    AccountPrivSerializer,
    AccountUserSerializer,
    AddAccountRuleSerializer,
    CreateAccountSerializer,
    DeleteAccountRuleSerializer,
    DeleteAccountSerializer,
    FilterAccountRulesSerializer,
    FilterPrivSerializer,
    ListAccountRulesSerializer,
    ModifyAccountRuleSerializer,
    PageAccountRulesSerializer,
    QueryAccountRulesSerializer,
    UpdateAccountPasswordSerializer,
)
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.account import AccountPermission
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, ResourceActionPermission, get_request_key_id
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = "db_services/permission/account"


class BaseDBAccountViewSet(viewsets.SystemViewSet):
    account_meta: AccountMeta = AccountMeta
    account_rule_meta: AccountRuleMeta = AccountRuleMeta
    account_priv_meta: AccountPrivMeta = AccountPrivMeta
    account_user_meta: AccountUserMeta = AccountUserMeta
    account_handler: AccountHandler = AccountHandler

    @staticmethod
    def instance_getter(request, view):
        return [get_request_key_id(request, "bk_biz_id")]

    def _get_custom_permissions(self):
        if self.action in ["query_account_rules"]:
            return [DBManagePermission()]
        elif self.action in ["list_account_rules"]:
            account_type = get_request_key_id(self.request, key="account_type")
            account_view_action = getattr(ActionEnum, f"{account_type}_account_rules_view".upper())
            return [ResourceActionPermission([account_view_action], ResourceEnum.BUSINESS, self.instance_getter)]
        else:
            account_type = get_request_key_id(self.request, key="account_type")
            return [AccountPermission(account_type=account_type, view_action=self.action)]

    def _view_common_handler(
        self, request, bk_biz_id: int, meta: Union[AccountMeta, AccountRuleMeta], func: str
    ) -> Response:
        """
        - 视图通用处理函数, 方便统一管理
        :param request: request请求
        :param bk_biz_id: 业务ID
        :param meta: 元信息数据结构
        :param func: handler的回调函数名称
        """
        validated_data = self.params_validate(self.get_serializer_class())
        base_info = {
            "bk_biz_id": bk_biz_id,
            "operator": request.user.username,
            "account_type": validated_data.get("account_type"),
            "context": {},
        }
        meta_init_data = meta.from_dict(validated_data)
        return Response(getattr(self.account_handler(**base_info), func)(meta_init_data))

    @common_swagger_auto_schema(
        operation_summary=_("创建账号"), request_body=CreateAccountSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=CreateAccountSerializer)
    def create_account(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_meta,
            func=self.account_handler.create_account.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("删除账号"), request_body=DeleteAccountSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteAccountSerializer)
    def delete_account(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_meta,
            func=self.account_handler.delete_account.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("修改密码"), request_body=UpdateAccountPasswordSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=UpdateAccountPasswordSerializer)
    def update_password(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_meta,
            func=self.account_handler.update_password.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("添加账号规则"), request_body=AddAccountRuleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=AddAccountRuleSerializer)
    def add_account_rule(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_rule_meta,
            func=self.account_handler.add_account_rule.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询账号规则清单"),
        query_serializer=FilterAccountRulesSerializer(),
        responses={status.HTTP_200_OK: ListAccountRulesSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=PageAccountRulesSerializer)
    @Permission.decorator_permission_field(
        id_field=lambda d: d["account"]["account_id"],
        data_field=lambda d: d["results"],
        action_filed=lambda k: [
            getattr(ActionEnum, f'{k["account_type"].upper()}_DELETE_ACCOUNT'),
            getattr(ActionEnum, f'{k["account_type"].upper()}_ADD_ACCOUNT_RULE'),
        ],
    )
    def list_account_rules(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_rule_meta,
            func=self.account_handler.list_account_rules.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询账号规则"),
        request_body=QueryAccountRulesSerializer(),
        responses={status.HTTP_200_OK: ListAccountRulesSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryAccountRulesSerializer)
    def query_account_rules(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_rule_meta,
            func=self.account_handler.query_account_rules.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("修改账号规则"), request_body=ModifyAccountRuleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=ModifyAccountRuleSerializer)
    def modify_account_rule(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_rule_meta,
            func=self.account_handler.modify_account_rule.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("删除账号规则"), request_body=DeleteAccountRuleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteAccountRuleSerializer)
    def delete_account_rule(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_rule_meta,
            func=self.account_handler.delete_account_rule.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询权限清单"),
        query_serializer=AccountPrivSerializer(),
        responses={status.HTTP_200_OK: AccountPrivSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=FilterPrivSerializer)
    def get_account_privs(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_priv_meta,
            func=self.account_handler.get_account_privs.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询用户列表"),
        query_serializer=AccountUserSerializer(),
        responses={status.HTTP_200_OK: AccountUserSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=AccountUserSerializer)
    def get_account_users(self, request, bk_biz_id):
        return self._view_common_handler(
            request=request,
            bk_biz_id=bk_biz_id,
            meta=self.account_user_meta,
            func=self.account_handler.get_account_users.__name__,
        )

    @common_swagger_auto_schema(
        operation_summary=_("下载权限清单"),
        query_serializer=AccountPrivSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=AccountPrivSerializer)
    def get_download_privs(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        base_info = {
            "bk_biz_id": bk_biz_id,
            "operator": request.user.username,
            "account_type": validated_data.get("account_type"),
            "context": {},
        }
        meta_init_data = self.account_priv_meta.from_dict(validated_data)
        results = getattr(self.account_handler(**base_info), self.account_handler.get_download_privs.__name__)(
            meta_init_data
        )
        if not results:
            return Response({"error": _("下载权限清单失败")})
        # 返回响应
        return results
