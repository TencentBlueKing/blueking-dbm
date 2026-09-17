from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbpermission.db_authorize.serializers import (
    PreCheckAuthorizeRulesResponseSerializer,
    PreCheckAuthorizeRulesSerializer,
)
from backend.db_services.mysql.permission.authorize.serializers import IntegrationGrantSerializer
from backend.db_services.mysql.permission.authorize.views import DBAuthorizeViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class DBAuthorizeApiGwViewSet(BaseOpenAPIViewSet, DBAuthorizeViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("MySQL集成授权"),
        request_body=IntegrationGrantSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=IntegrationGrantSerializer)
    def integration_grant(self, request, bk_biz_id):
        return super().integration_grant(request, bk_biz_id)

    @common_swagger_auto_schema(
        operation_summary=_("规则前置检查"),
        request_body=PreCheckAuthorizeRulesSerializer(),
        responses={status.HTTP_200_OK: PreCheckAuthorizeRulesResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PreCheckAuthorizeRulesSerializer)
    def pre_check_rules(self, request, bk_biz_id):
        return super().pre_check_rules(request, bk_biz_id)
