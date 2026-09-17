from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.db_services.sqlserver.cluster.serializers import (
    MultiGetDBForDrsResponseSerializer,
    MultiGetDBForDrsSerializer,
)
from backend.db_services.sqlserver.cluster.views import ClusterViewSet


class ClusterApiGwViewSet(BaseOpenAPIViewSet, ClusterViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("通过库表匹配批量查询db"),
        request_body=MultiGetDBForDrsSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: MultiGetDBForDrsResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=MultiGetDBForDrsSerializer)
    def multi_get_sqlserver_dbs(self, request, bk_biz_id):
        return super().multi_get_sqlserver_dbs(request, bk_biz_id)
