from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.bigdata.es.views import EsClusterViewSetBigdata
from backend.db_services.bigdata.resources import yasg_slz
from backend.db_services.dbbase.resources import serializers
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


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
class EsClusterApiGwViewSet(BaseOpenAPIViewSet, EsClusterViewSetBigdata):
    @common_swagger_auto_schema(
        operation_summary=_("获取集群访问密码"),
        responses={status.HTTP_200_OK: yasg_slz.PasswordResourceSLZ()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=True, url_path="get_password", serializer_class=None)
    def get_password(self, request, bk_biz_id: int, cluster_id: int):
        return super().get_password(request, bk_biz_id, cluster_id)

    def list(self, request, bk_biz_id: int, *args, **kwargs):
        return super().list(request, bk_biz_id, *args, **kwargs)

    def retrieve(self, request, bk_biz_id: int, cluster_id: int, *args, **kwargs):
        return super().retrieve(request, bk_biz_id, cluster_id, *args, **kwargs)
