from django.utils.translation import gettext as _

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.db_services.redis.rollback.views import RollbackViewSet


class RollbackApiGwViewSet(BaseOpenAPIViewSet, RollbackViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("构造实例列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
