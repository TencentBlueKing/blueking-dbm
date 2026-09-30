from django.utils.translation import gettext as _
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.db_services.taskflow.serializers import BatchNodesSerializer, NodeSerializer
from backend.db_services.taskflow.views.flow import TaskFlowViewSet


class TaskFlowApiGwViewSet(BaseOpenAPIViewSet, TaskFlowViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("批量重试"),
        request_body=BatchNodesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=BatchNodesSerializer)
    def batch_retry_nodes(self, requests, *args, **kwargs):
        return super().batch_retry_nodes(requests, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("重试节点"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=NodeSerializer)
    def retry_node(self, requests, *args, **kwargs):
        return super().retry_node(requests, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("任务详情"),
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, requests, *args, **kwargs):
        return super().retrieve(requests, *args, **kwargs)
