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
import copy

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.iam_app import mock_data
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum


class IamActionResourceRequestSerializer(serializers.Serializer):
    class ResourceSerializer(serializers.Serializer):
        type = serializers.CharField(help_text=_("资源类型"))
        id = serializers.CharField(help_text=_("资源ID"))

    action_ids = serializers.ListField(help_text=_("动作ID列表"), min_length=0)
    resources = serializers.ListField(help_text=_("资源列表"), child=ResourceSerializer(), min_length=0)


class SimpleIamActionResourceRequestSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    action_id = serializers.CharField(help_text=_("动作ID"))
    resource_ids = serializers.ListField(help_text=_("资源ID列表"), child=serializers.CharField(), min_length=0)

    def validate(self, attrs):
        related_resources = copy.deepcopy(ActionEnum.get_action_by_id(attrs["action_id"]).related_resource_types)
        if len(related_resources) > 2 or (
            len(related_resources) == 2 and ResourceEnum.BUSINESS not in related_resources
        ):
            raise serializers.ValidationError(_("仅支持业务下一个动作关联一种类型的资源"))

        attrs["resources"] = []
        # 如果有业务资源
        if attrs.get("bk_biz_id") and ResourceEnum.BUSINESS in related_resources:
            attrs["resources"] = [{"type": ResourceEnum.BUSINESS.id, "id": attrs["bk_biz_id"]}]
            related_resources.remove(ResourceEnum.BUSINESS)
        # 如果关联其他资源
        if related_resources:
            resource_type = related_resources[0].id
            attrs["resources"].extend([{"type": resource_type, "id": id} for id in attrs["resource_ids"]])

        return attrs


class GetApplyDataResSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.GET_APPLY_DATA}


class CheckAllowedResSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.ACTION_CHECK_ALLOWED}
