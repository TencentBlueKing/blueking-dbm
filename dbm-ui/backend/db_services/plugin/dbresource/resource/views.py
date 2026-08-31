from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbresource.serializers import (
    ResourceDeleteSerializer,
    ResourceImportResponseSerializer,
    ResourceImportSerializer,
)
from backend.db_services.dbresource.views.resource import DBResourceViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class DBResourceApiGwViewSet(BaseOpenAPIViewSet, DBResourceViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("资源删除"),
        request_body=ResourceDeleteSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="delete", serializer_class=ResourceDeleteSerializer)
    def resource_delete(self, request):
        return super().resource_delete(request)

    @common_swagger_auto_schema(
        operation_summary=_("资源导入"),
        request_body=ResourceImportSerializer(),
        responses={status.HTTP_200_OK: ResourceImportResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="import", serializer_class=ResourceImportSerializer)
    def resource_import(self, request):
        return super().resource_import(request)
