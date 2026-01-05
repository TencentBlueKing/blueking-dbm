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


class ResourceParamQueryInputSerializer(serializers.Serializer):
    """
    Serializer for resource parameter query input.
    Used to validate the request parameters for querying resource request parameters
    by bill_id or task_id.
    """

    bill_id = serializers.CharField(
        help_text=_(
            "Bill/Ticket ID for resource query. Either bill_id or task_id must be provided. "
            "单据ID，用于查询资源请求参数。bill_id和task_id必须至少提供一个。"
        ),
        required=False,
        allow_blank=True,
        default="",
    )
    task_id = serializers.CharField(
        help_text=_(
            "Task ID for resource query. Either bill_id or task_id must be provided. "
            "任务ID，用于查询资源请求参数。bill_id和task_id必须至少提供一个。"
        ),
        required=False,
        allow_blank=True,
        default="",
    )
    latest = serializers.BooleanField(
        help_text=_("Whether to return only the latest record. Default: True. " "是否只返回最近一条记录，默认为True。"),
        required=False,
        default=True,
    )

    def validate(self, attrs):
        """
        Validate that at least one of bill_id or task_id is provided.
        """
        bill_id = attrs.get("bill_id", "")
        task_id = attrs.get("task_id", "")

        if not bill_id and not task_id:
            raise serializers.ValidationError(_("bill_id 和 task_id 必须至少提供一个"))

        return attrs


class ResourceParamQueryOutputSerializer(serializers.Serializer):
    """
    Serializer for resource parameter query output.
    Returns the resource request parameters as JSON data.
    """

    data = serializers.JSONField(
        help_text=_("Resource request parameter data returned from the query. " "查询返回的资源请求参数数据。"),
        required=False,
        default=None,
    )
