from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.cmdb import serializers
from backend.db_services.cmdb.views import CMDBViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class CMDBApiGwViewSet(BaseOpenAPIViewSet, CMDBViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("业务列表"),
        query_serializer=serializers.ListBizWithActionSLZ(),
        responses={status.HTTP_200_OK: serializers.BIZSLZ(label=_("业务信息"), many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.ListBizWithActionSLZ)
    def list_bizs(self, request):
        return super().list_bizs(request)

    @common_swagger_auto_schema(
        operation_summary=_("创建数据库模块"),
        request_body=serializers.CreateModuleSLZ(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=serializers.CreateModuleSLZ)
    def create_module(self, request, bk_biz_id):
        return super().create_module(request, bk_biz_id)
