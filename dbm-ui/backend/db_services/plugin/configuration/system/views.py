from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.views.system import SystemSettingsViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class SystemSettingsApiGwViewSet(BaseOpenAPIViewSet, SystemSettingsViewSet):
    @common_swagger_auto_schema(operation_summary=_("查询环境变量"), tags=SWAGGER_TAG)
    @action(detail=False, methods=["get"])
    def environ(self, request):
        return super().environ(request)
