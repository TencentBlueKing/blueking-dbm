from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action

from backend.bk_web.swagger import PaginatedResponseSwaggerAutoSchema, common_swagger_auto_schema
from backend.configuration.serializers import ListIPWhitelistSerializer
from backend.configuration.views.ip_whitelist import IPWhitelistViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class IPWhitelistApiGwViewSet(BaseOpenAPIViewSet, IPWhitelistViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("IP白名单列表"),
        request_body=ListIPWhitelistSerializer,
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ListIPWhitelistSerializer)
    def iplist(self, request, *args, **kwargs):
        return super().iplist(request, *args, **kwargs)
