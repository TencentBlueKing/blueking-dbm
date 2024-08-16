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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.bk_web.serializers import AuditedSerializer
from backend.db_meta.models import Tag


class TagSerializer(AuditedSerializer, serializers.ModelSerializer):
    """
    标签序列化器
    """

    class Meta:
        model = Tag
        fields = "__all__"


class BatchCreateTagsSerializer(serializers.Serializer):
    class CreateTagSerializer(serializers.Serializer):
        key = serializers.CharField(help_text=_("标签key"))
        value = serializers.CharField(help_text=_("标签value"))

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    tags = serializers.ListField(child=CreateTagSerializer())


class UpdateTagSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    id = serializers.IntegerField(help_text=_("标签 ID"))
    value = serializers.CharField(help_text=_("标签value"))


class DeleteTagsSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    ids = serializers.ListSerializer(child=serializers.IntegerField(help_text=_("标签 ID")), help_text=_("标签 ID 列表"))


class QueryRelatedResourceSerializer(serializers.Serializer):
    ids = serializers.ListSerializer(child=serializers.IntegerField(help_text=_("标签 ID")), help_text=_("标签 ID 列表"))
    resource_type = serializers.CharField(help_text=_("资源类型"), required=False)
