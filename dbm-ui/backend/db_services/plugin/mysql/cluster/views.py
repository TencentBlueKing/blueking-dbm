from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.cluster.serializers import (
    QueryClustersRequestSerializer,
    QueryClustersResponseSerializer,
)
from backend.db_services.mysql.cluster.views import ClusterViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class ClusterApiGwViewSet(BaseOpenAPIViewSet, ClusterViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("通过过滤条件批量查询集群[Deprecated!! 这个方法将被移除，请不要调用]"),
        request_body=QueryClustersRequestSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryClustersResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryClustersRequestSerializer)
    def query_clusters(self, request, bk_biz_id):
        return super().query_clusters(request, bk_biz_id)
