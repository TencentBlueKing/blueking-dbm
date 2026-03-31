from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.remote_service.serializers import (
    ShowDatabasesRequestSerializer,
    ShowDatabasesResponseSerializer,
    ShowDBWithPatternsResponseSerializer,
    ShowDBWithPatternsSerializer,
)
from backend.db_services.mysql.remote_service.views import RemoteServiceViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class RemoteServiceApiGwViewSet(BaseOpenAPIViewSet, RemoteServiceViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("查询集群数据库列表"),
        request_body=ShowDatabasesRequestSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: ShowDatabasesResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=ShowDatabasesRequestSerializer)
    def show_cluster_databases(self, request, bk_biz_id):
        return super().show_cluster_databases(request, bk_biz_id)

    @common_swagger_auto_schema(
        operation_summary=_("根据库表正则查询集群库信息"),
        request_body=ShowDBWithPatternsSerializer(),
        responses={status.HTTP_200_OK: ShowDBWithPatternsResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ShowDBWithPatternsSerializer)
    def show_databases_with_patterns(self, request, bk_biz_id):
        return super().show_databases_with_patterns(request, bk_biz_id)
