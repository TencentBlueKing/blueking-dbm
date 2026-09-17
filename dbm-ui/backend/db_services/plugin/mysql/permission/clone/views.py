from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.permission.clone.serializers import (
    PreCheckCloneResponseSerializer,
    PreCheckCloneSerializer,
)
from backend.db_services.mysql.permission.clone.views import DBCloneViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class DBCloneApiGwViewSet(BaseOpenAPIViewSet, DBCloneViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("权限克隆前置检查"),
        request_body=PreCheckCloneSerializer(),
        responses={status.HTTP_200_OK: PreCheckCloneResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PreCheckCloneSerializer)
    def pre_check_clone(self, request, bk_biz_id):
        return super().pre_check_clone(request, bk_biz_id)
