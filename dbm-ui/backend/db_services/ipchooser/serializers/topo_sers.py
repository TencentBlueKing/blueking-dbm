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
from rest_framework import serializers

from .. import constants, mock_data
from . import base


class TreesRequestSer(base.ScopeSelectorBaseSer):
    mode = serializers.ChoiceField(
        help_text=_("模式"), choices=constants.ModeType.list_choices(), required=False, default=constants.ModeType.ALL
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_TREES_REQUEST}


class TreesResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_TREES_RESPONSE}


class QueryPathRequestSer(serializers.Serializer):
    node_list = serializers.ListField(child=base.TreeNodeSer())

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_PATH_REQUEST}


class QueryPathResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_PATH_RESPONSE}


class QueryHostsRequestSer(base.QueryHostsBaseSer):
    mode = serializers.ChoiceField(
        help_text=_("模式"), choices=constants.ModeType.list_choices(), required=False, default=constants.ModeType.ALL
    )
    node_list = serializers.ListField(child=base.TreeNodeSer())

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOSTS_REQUEST}


class QueryHostsResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOSTS_RESPONSE}


class QueryHostIdInfosRequestSer(QueryHostsRequestSer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOST_ID_INFOS_REQUEST}


class QueryHostIdInfosResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_TOPO_QUERY_HOST_ID_INFOS_RESPONSE}


class QueryHostTopoInfosRequestSer(base.PaginationSer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    filter_conditions = serializers.DictField(help_text=_("查询过滤条件"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_HOST_TOPO_INFOS_REQUEST}


class QueryHostTopoInfosResponseSer(serializers.Serializer):
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
    topo = serializers.ListField(help_text=_("拓扑信息列表"), child=serializers.CharField(help_text=_("拓扑信息")))

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_HOST_TOPO_INFOS_RESPONSE}
