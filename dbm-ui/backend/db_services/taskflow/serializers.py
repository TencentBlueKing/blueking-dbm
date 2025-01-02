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
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import AppCache
from backend.flow.consts import PipelineStatus
from backend.flow.models import FlowTree
from backend.utils.time import calculate_cost_time


class FlowTaskSerializer(serializers.ModelSerializer):
    ticket_type_display = serializers.SerializerMethodField(help_text=_("单据类型名称"))
    cost_time = serializers.SerializerMethodField(help_text=_("耗时"))
    bk_biz_name = serializers.SerializerMethodField(help_text=_("业务名"))

    _biz_name_map = None

    @property
    def biz_name_map(self):
        if self._biz_name_map is None:
            bizs = AppCache.get_appcache(key="appcache_dict")
            self._biz_name_map = {int(bk_biz_id): biz["bk_biz_name"] for bk_biz_id, biz in bizs.items()}
        return self._biz_name_map

    class Meta:
        model = FlowTree
        fields = (
            "root_id",
            "ticket_type",
            "ticket_type_display",
            "status",
            "uid",
            "created_by",
            "created_at",
            "updated_at",
            "cost_time",
            "bk_biz_id",
            "bk_biz_name",
        )

    def get_ticket_type_display(self, obj):
        return obj.get_ticket_type_display()

    def get_cost_time(self, obj):
        if obj.status in [PipelineStatus.READY, PipelineStatus.RUNNING]:
            return calculate_cost_time(timezone.now(), obj.created_at)
        return calculate_cost_time(obj.updated_at, obj.created_at)

    def get_bk_biz_name(self, obj):
        return self.biz_name_map.get(obj.bk_biz_id) or obj.bk_biz_id


class NodeSerializer(serializers.Serializer):
    node_id = serializers.CharField(help_text=_("节点ID"))


class BatchRetryNodesSerializer(serializers.Serializer):
    pass


class CallbackNodeSerializer(NodeSerializer):
    desc = serializers.CharField(help_text=_("回调描述"), required=False)


class DownloadExcelSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("流程ID"))
    key = serializers.CharField(help_text=_("查询key"))
    match_header = serializers.BooleanField(help_text=_("是否严格匹配列名"), required=False)


class VersionSerializer(NodeSerializer):
    version_id = serializers.CharField(help_text=_("版本ID"))
    download = serializers.BooleanField(help_text=_("是否下载日志"), default=False)


class BatchDownloadSerializer(serializers.Serializer):
    full_paths = serializers.ListField(
        help_text=_("文件路径列表"), child=serializers.CharField(help_text="full_path"), min_length=1
    )
