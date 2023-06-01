# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets

from ...configuration.models import Profile
from .constants import DEVICE_CLASS, ModeType
from .handlers import host_handler, topo_handler
from .query.resource import ResourceQueryHelper
from .serializers import host_sers, topo_sers

IP_CHOOSER_VIEW_TAGS = ["ipchooser"]


class IpChooserTopoViewSet(viewsets.SystemViewSet):
    URL_BASE_NAME = "ipchooser_topo"

    @swagger_auto_schema(
        operation_summary=_("批量获取含各节点主机数量的拓扑树"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.TreesRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.TreesResponseSer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.TreesRequestSer)
    def trees(self, request, *args, **kwargs):
        return Response(
            topo_handler.TopoHandler.trees(
                all_scope=self.validated_data.get("all_scope", False),
                scope_list=self.validated_data["scope_list"],
                mode=self.validated_data.get("mode", ModeType.ALL.value),
            )
        )

    @swagger_auto_schema(
        operation_summary=_("根据多个拓扑节点与搜索条件批量分页查询所包含的主机信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.QueryHostsRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.QueryHostsResponseSer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.QueryHostsRequestSer)
    def query_hosts(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        params = {
            "readable_node_list": validated_data["node_list"],
            "conditions": validated_data["conditions"],
            "page": self.validated_data["page"],
            "bk_cloud_id": validated_data.get("bk_cloud_id"),
            "mode": validated_data.get("mode", ModeType.ALL.value),
        }
        return Response(topo_handler.TopoHandler.query_hosts(**params))

    @swagger_auto_schema(
        operation_summary=_("根据多个拓扑节点与搜索条件批量分页查询所包含的主机 ID 信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.QueryHostIdInfosRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.QueryHostIdInfosResponseSer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.QueryHostIdInfosRequestSer)
    def query_host_id_infos(self, request, *args, **kwargs):
        return Response(
            topo_handler.TopoHandler.query_host_id_infos(
                readable_node_list=self.validated_data["node_list"],
                conditions=self.validated_data["conditions"],
                start=self.validated_data["start"],
                page_size=self.validated_data["page_size"],
            )
        )

    @swagger_auto_schema(
        operation_summary=_("根据主机过滤查询主机的拓扑信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=topo_sers.QueryHostTopoInfosRequestSer(),
        responses={status.HTTP_200_OK: topo_sers.QueryHostTopoInfosResponseSer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=topo_sers.QueryHostTopoInfosRequestSer)
    def query_host_topo_infos(self, request, *args, **kwargs):
        return Response(
            topo_handler.TopoHandler.query_host_topo_infos(
                bk_biz_id=self.validated_data["bk_biz_id"],
                filter_conditions=self.validated_data["filter_conditions"],
                start=self.validated_data["start"],
                page_size=self.validated_data["page_size"],
            )
        )


class IpChooserHostViewSet(viewsets.SystemViewSet):
    URL_BASE_NAME = "ipchooser_host"
    pagination_class = None

    @swagger_auto_schema(
        operation_summary=_("根据用户手动输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=host_sers.HostCheckRequestSer(),
        responses={status.HTTP_200_OK: host_sers.HostCheckResponseSer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=host_sers.HostCheckRequestSer)
    def check(self, request, *args, **kwargs):
        return Response(
            host_handler.HostHandler.check(
                scope_list=self.validated_data["scope_list"],
                ip_list=self.validated_data["ip_list"],
                ipv6_list=self.validated_data["ipv6_list"],
                key_list=self.validated_data["key_list"],
                mode=self.validated_data.get("mode", ModeType.ALL.value),
            )
        )

    @swagger_auto_schema(
        operation_summary=_("根据主机关键信息获取机器详情信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
        request_body=host_sers.HostDetailsRequestSer(),
        responses={status.HTTP_200_OK: host_sers.HostDetailsResponseSer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=host_sers.HostDetailsRequestSer)
    def details(self, request, *args, **kwargs):
        return Response(
            host_handler.HostHandler.details(
                scope_list=self.validated_data["scope_list"],
                host_list=self.validated_data["host_list"],
                mode=self.validated_data.get("mode", ModeType.ALL.value),
            )
        )


class IpChooserSettingsViewSet(viewsets.SystemViewSet):
    LABEL_BASE_NAME = "ipchooser"
    pagination_class = None

    DEFAULT_SETTINGS = {
        "settings_map": {
            "ip_selector_host_list": {
                "hostListColumn": ["hostId", "ip", "coludArea", "alive", "hostName", "osName"],
                "hostListColumnSort": [
                    "hostId",
                    "ip",
                    "coludArea",
                    "alive",
                    "hostName",
                    "osName",
                    "osType",
                    "ipv6",
                    "coludVerdor",
                    "agentId",
                ],
            }
        }
    }

    @swagger_auto_schema(
        operation_summary=_("获取自定义配置，比如表格列字段及顺序"),
        tags=IP_CHOOSER_VIEW_TAGS,
    )
    @action(methods=["POST"], detail=False)
    def batch_get(self, request, *args, **kwargs):

        username = request.user.username

        try:
            profile = Profile.objects.get(username=username, label=f"{username}_{self.LABEL_BASE_NAME}")
        except Profile.DoesNotExist:
            return Response(self.DEFAULT_SETTINGS)

        return Response(profile.values)

    @swagger_auto_schema(
        operation_summary=_("保存用户自定义配置"),
        tags=IP_CHOOSER_VIEW_TAGS,
    )
    @action(methods=["POST"], detail=False)
    def set(self, request, *args, **kwargs):
        username = request.user.username
        profile, _ = Profile.objects.update_or_create(
            defaults={"values": request.data or self.DEFAULT_SETTINGS},
            username=username,
            label=f"{username}_{self.LABEL_BASE_NAME}",
        )
        return Response(profile.values)

    @swagger_auto_schema(
        operation_summary=_("查询云区域的信息"),
        tags=IP_CHOOSER_VIEW_TAGS,
    )
    @action(methods=["POST"], detail=False)
    def search_cloud_area(self, request, *args, **kwargs):
        cloud_area_list = list(ResourceQueryHelper.search_cc_cloud(get_cache=True).values())
        return Response(cloud_area_list)

    @swagger_auto_schema(
        operation_summary=_("查询磁盘类型"),
        tags=IP_CHOOSER_VIEW_TAGS,
    )
    @action(methods=["GET"], detail=False)
    def search_device_class(self, request, *args, **kwargs):
        return Response(DEVICE_CLASS)
