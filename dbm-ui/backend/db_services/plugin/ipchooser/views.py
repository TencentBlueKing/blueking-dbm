from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.ipchooser.serializers import topo_sers
from backend.db_services.ipchooser.views import IpChooserTopoViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class IpChooserTopoApiGwViewSet(BaseOpenAPIViewSet, IpChooserTopoViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("根据主机过滤查询主机的拓扑信息"),
        tags=SWAGGER_TAG,
        request_body=topo_sers.QueryHostTopoInfosRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.QueryHostTopoInfosResponseSer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.QueryHostTopoInfosRequestSer)
    def query_host_topo_infos(self, request, *args, **kwargs):
        return super().query_host_topo_infos(request, *args, **kwargs)
