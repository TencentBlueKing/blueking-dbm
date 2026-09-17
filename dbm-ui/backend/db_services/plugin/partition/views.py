from django.utils.translation import gettext_lazy as _
from rest_framework import status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.partition.serializers import (
    PartitionCreateSerializer,
    PartitionDryRunResponseSerializer,
    PartitionListResponseSerializer,
    PartitionListSerializer,
    PartitionUpdateSerializer,
)
from backend.db_services.partition.views import DBPartitionViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class DBPartitionApiGwViewSet(BaseOpenAPIViewSet, DBPartitionViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("获取分区策略列表"),
        query_serializer=PartitionListSerializer(),
        responses={status.HTTP_200_OK: PartitionListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("修改分区策略"),
        request_body=PartitionUpdateSerializer(),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("增加分区策略"),
        request_body=PartitionCreateSerializer(),
        responses={status.HTTP_200_OK: PartitionDryRunResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
