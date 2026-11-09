from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.db_services.sqlserver.permission.db_authorize.serializers import (
    SQLServerPreCheckAuthorizeRulesResponseSerializer,
    SQLServerPreCheckAuthorizeRulesSerializer,
)
from backend.db_services.sqlserver.permission.db_authorize.views import DBAuthorizeViewSet


class DBAuthorizeApiGwViewSet(BaseOpenAPIViewSet, DBAuthorizeViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("规则前置检查"),
        request_body=SQLServerPreCheckAuthorizeRulesSerializer(),
        responses={status.HTTP_200_OK: SQLServerPreCheckAuthorizeRulesResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SQLServerPreCheckAuthorizeRulesSerializer)
    def pre_check_rules(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, self.authorize_meta, self.handler.multi_user_pre_check_rules.__name__
        )
