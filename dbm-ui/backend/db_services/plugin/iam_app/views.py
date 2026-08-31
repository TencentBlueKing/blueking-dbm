from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.iam_app.serializers import (
    AssignAuthToDBASerializer,
    CheckAllowedResSerializer,
    IamActionResourceRequestSerializer,
    SimpleIamActionResourceRequestSerializer,
)
from backend.iam_app.views.views import IAMViewSet


class IAMApiGwViewSet(BaseOpenAPIViewSet, IAMViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("检查当前用户对该动作是否有权限"),
        request_body=IamActionResourceRequestSerializer(),
        responses={status.HTTP_200_OK: CheckAllowedResSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=IamActionResourceRequestSerializer)
    def check_allowed(self, request, *args, **kwargs):
        return super().check_allowed(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("检查当前用户对该动作是否有权限(仅适用于鉴权业务下一个动作对应一种资源类型，如果是多种动作对应多种资源类型，请切换为check_allowed接口)"),
        request_body=SimpleIamActionResourceRequestSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=SimpleIamActionResourceRequestSerializer)
    def simple_check_allowed(self, request, *args, **kwargs):
        return super().simple_check_allowed(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("自动分配权限给DBA"),
        request_body=AssignAuthToDBASerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=AssignAuthToDBASerializer)
    def assign_auth_to_dba(self, request, *args, **kwargs):
        return super().assign_auth_to_dba(request, *args, **kwargs)
