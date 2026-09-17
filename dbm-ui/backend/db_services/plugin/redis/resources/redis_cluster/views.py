from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from rest_framework import status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbbase.resources import serializers
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.db_services.redis.resources.redis_cluster import yasg_slz
from backend.db_services.redis.resources.redis_cluster.views import RedisClusterViewSet


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群列表"),
        query_serializer=serializers.ListResourceSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[SWAGGER_TAG],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群详情"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceSLZ()},
        tags=[SWAGGER_TAG],
    ),
)
class RedisClusterApiGwViewSet(BaseOpenAPIViewSet, RedisClusterViewSet):
    def list(self, request, bk_biz_id: int):
        return super().list(request, bk_biz_id)

    def retrieve(self, request, bk_biz_id: int, cluster_id: int):
        return super().retrieve(request, bk_biz_id, cluster_id)
