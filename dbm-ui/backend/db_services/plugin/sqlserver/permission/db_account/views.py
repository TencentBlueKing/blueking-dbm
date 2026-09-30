from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbpermission.db_account.serializers import (
    FilterAccountRulesSerializer,
    ListAccountRulesSerializer,
    PageAccountRulesSerializer,
)
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.db_services.sqlserver.permission.db_account.views import DBAccountViewSet


class DBAccountApiGwViewSet(BaseOpenAPIViewSet, DBAccountViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("查询账号规则清单"),
        query_serializer=FilterAccountRulesSerializer(),
        responses={status.HTTP_200_OK: ListAccountRulesSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=PageAccountRulesSerializer)
    def list_account_rules(self, request, bk_biz_id):
        return super().list_account_rules(request, bk_biz_id)
