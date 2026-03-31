from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.cluster_entry.serializers import RetrieveClusterEntrySLZ
from backend.db_services.cluster_entry.views import ClusterEntryViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class ClusterEntryOpenAPIViewSet(BaseOpenAPIViewSet, ClusterEntryViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("获取集群入口列表"),
        query_serializer=RetrieveClusterEntrySLZ(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="get_cluster_entries",
        serializer_class=RetrieveClusterEntrySLZ,
        pagination_class=None,
    )
    def get_cluster_entries(self, request, *args, **kwargs):
        """获取集群入口列表"""
        return super().get_cluster_entries(request, *args, **kwargs)
