from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import (
    PaginatedResponseSwaggerAutoSchema,
    ResponseSwaggerAutoSchema,
    common_swagger_auto_schema,
)
from backend.db_services.mysql.open_area.serializers import (
    TendbOpenAreaResultPreviewResponseSerializer,
    TendbOpenAreaResultPreviewSerializer,
)
from backend.db_services.mysql.open_area.views import OpenAreaViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class OpenAreaApiGwViewSet(BaseOpenAPIViewSet, OpenAreaViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("开区模板列表"),
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("获取开区结果预览"),
        request_body=TendbOpenAreaResultPreviewSerializer(),
        responses={status.HTTP_200_OK: TendbOpenAreaResultPreviewResponseSerializer()},
        auto_schema=ResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TendbOpenAreaResultPreviewSerializer)
    def preview(self, request, *args, **kwargs):
        return super().preview(request, *args, **kwargs)
