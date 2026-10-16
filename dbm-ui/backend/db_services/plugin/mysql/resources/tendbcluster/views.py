from django.utils.decorators import method_decorator
from rest_framework import status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbbase.resources import serializers
from backend.db_services.mysql.resources.tendbcluster import yasg_slz
from backend.db_services.mysql.resources.tendbcluster.views import SpiderViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListTendbClusterResourceSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[SWAGGER_TAG],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        responses={status.HTTP_200_OK: yasg_slz.ResourceSLZ()},
        tags=[SWAGGER_TAG],
    ),
)
class SpiderApiGwViewSet(BaseOpenAPIViewSet, SpiderViewSet):
    def list(self, request, bk_biz_id: int):
        return super().list(request, bk_biz_id)

    def retrieve(self, request, bk_biz_id: int, cluster_id: int):
        return super().retrieve(request, bk_biz_id, cluster_id)
