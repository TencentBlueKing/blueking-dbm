from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.sql_import.serializers import (
    SQLGrammarCheckResponseSerializer,
    SQLGrammarCheckSerializer,
    SQLSemanticCheckResponseSerializer,
    SQLSemanticCheckSerializer,
)
from backend.db_services.mysql.sql_import.views import SQLImportViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class MySQLSQLImportApiGwViewSet(BaseOpenAPIViewSet, SQLImportViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("sql语法检查"),
        request_body=SQLGrammarCheckSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: SQLGrammarCheckResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=SQLGrammarCheckSerializer)
    def grammar_check(self, request, bk_biz_id):
        return super().grammar_check(request, bk_biz_id)

    @common_swagger_auto_schema(
        operation_summary=_("sql语义检查"),
        request_body=SQLSemanticCheckSerializer(),
        responses={status.HTTP_200_OK: SQLSemanticCheckResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SQLSemanticCheckSerializer)
    def semantic_check(self, request, bk_biz_id):
        return super().semantic_check(request, bk_biz_id)
