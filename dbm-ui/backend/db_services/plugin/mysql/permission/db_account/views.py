from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbpermission.db_account.serializers import (
    AddAccountRuleSerializer,
    CreateAccountSerializer,
    FilterAccountRulesSerializer,
    ListAccountRulesSerializer,
    PageAccountRulesSerializer,
)
from backend.db_services.mysql.permission.db_account.views import DBAccountViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class DBAccountApiGwViewSet(BaseOpenAPIViewSet, DBAccountViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("添加账号规则"), request_body=AddAccountRuleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=AddAccountRuleSerializer)
    def add_account_rule(self, request, bk_biz_id):
        return super().add_account_rule(request, bk_biz_id)

    @common_swagger_auto_schema(
        operation_summary=_("创建账号"), request_body=CreateAccountSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=CreateAccountSerializer)
    def create_account(self, request, bk_biz_id):
        return super().create_account(request, bk_biz_id)

    @common_swagger_auto_schema(
        operation_summary=_("查询账号规则清单"),
        query_serializer=FilterAccountRulesSerializer(),
        responses={status.HTTP_200_OK: ListAccountRulesSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=PageAccountRulesSerializer)
    def list_account_rules(self, request, bk_biz_id):
        return super().list_account_rules(request, bk_biz_id)
