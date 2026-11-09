from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.sql_import.serializers import (
    SQLGrammarCheckResponseSerializer,
    SQLGrammarCheckSerializer,
)
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.db_services.sqlserver.sql_import.views import SQLImportViewSet


class SQLServerImportApiGwViewSet(BaseOpenAPIViewSet, SQLImportViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("sqlserver语法检查"),
        request_body=SQLGrammarCheckSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: SQLGrammarCheckResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=SQLGrammarCheckSerializer)
    def grammar_check(self, request, bk_biz_id):
        return super().grammar_check(request, bk_biz_id)
