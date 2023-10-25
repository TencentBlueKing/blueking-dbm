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
from typing import Type, Union

from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.permission.constants import AccountType
from backend.db_services.mysql.permission.db_account.dataclass import AccountMeta, AccountRuleMeta
from backend.db_services.mysql.permission.db_account.handlers import AccountHandler
from backend.db_services.mysql.permission.db_account.serializers import (
    AddMySQLAccountRuleSerializer,
    CreateMySQLAccountSerializer,
    DeleteMySQLAccountRuleSerializer,
    DeleteMySQLAccountSerializer,
    FilterMySQLAccountRulesSerializer,
    ListMySQLAccountRulesSerializer,
    ModifyMySQLAccountRuleSerializer,
    QueryMySQLAccountRulesSerializer,
    UpdateMySQLAccountSerializer,
)
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, ResourceActionPermission
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = "db_services/permission/account"


class DBAccountViewSet(viewsets.SystemViewSet):
    lookup_field = "bk_biz_id"

    def _get_custom_permissions(self):
        if self.action not in ["create_account", "delete_account", "add_account_rule"]:
            return [DBManagePermission()]

        account_type = self.request.data.get("account_type", AccountType.MYSQL)
        account_action = getattr(ActionEnum, f"{account_type}_{self.action}".upper())
        return [ResourceActionPermission([account_action], ResourceEnum.BUSINESS)]

    def _view_common_handler(
        self, request, bk_biz_id: int, meta: Union[Type[AccountMeta], Type[AccountRuleMeta]], func: str
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
            "account_type": validated_data.pop("account_type", None),
            "context": {},
        }
        meta_init_data = meta.from_dict(validated_data)
        return Response(getattr(AccountHandler(**base_info), func)(meta_init_data))

    @common_swagger_auto_schema(
        operation_summary=_("创建账号"), request_body=CreateMySQLAccountSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=CreateMySQLAccountSerializer)
    def create_account(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, AccountMeta, AccountHandler.create_account.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("删除账号"), request_body=DeleteMySQLAccountSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteMySQLAccountSerializer)
    def delete_account(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, AccountMeta, AccountHandler.delete_account.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("修改密码"), request_body=UpdateMySQLAccountSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=UpdateMySQLAccountSerializer)
    def update_password(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, AccountMeta, AccountHandler.update_password.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("添加账号规则"), request_body=AddMySQLAccountRuleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=AddMySQLAccountRuleSerializer)
    def add_account_rule(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, AccountRuleMeta, AccountHandler.add_account_rule.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("查询账号规则清单"),
        query_serializer=FilterMySQLAccountRulesSerializer(),
        responses={status.HTTP_200_OK: ListMySQLAccountRulesSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=FilterMySQLAccountRulesSerializer)
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["bk_biz_id"],
        actions=ActionEnum.get_match_actions(name="account"),
        resource_meta=ResourceEnum.BUSINESS,
    )
    def list_account_rules(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, AccountRuleMeta, AccountHandler.list_account_rules.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询账号规则"),
        request_body=QueryMySQLAccountRulesSerializer(),
        responses={status.HTTP_200_OK: ListMySQLAccountRulesSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryMySQLAccountRulesSerializer)
    def query_account_rules(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, AccountRuleMeta, AccountHandler.query_account_rules.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("修改账号规则"), request_body=ModifyMySQLAccountRuleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=ModifyMySQLAccountRuleSerializer)
    def modify_account_rule(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, AccountRuleMeta, AccountHandler.modify_account_rule.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("删除账号规则"), request_body=DeleteMySQLAccountRuleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteMySQLAccountRuleSerializer)
    def delete_account_rule(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, AccountRuleMeta, AccountHandler.delete_account_rule.__name__
        )
