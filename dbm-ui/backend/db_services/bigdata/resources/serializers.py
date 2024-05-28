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


class NodeListSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    ip = serializers.CharField(help_text=_("ip"), required=False)
    node_type = serializers.CharField(help_text=_("实例角色"), required=False)
    agent_status = serializers.CharField(help_text=_("Agent状态"), required=False)
    ordering = serializers.CharField(help_text=_("排序字段"), default="create_at")

    def validate_ordering(self, value):
        """验证排序字段是否合法。"""
        allowed_orderings = ["create_at", "node_count", "-create_at", "-node_count"]
        field_cleaned = value.replace("-", "")  # 移除可能的降序标识符

        if field_cleaned not in allowed_orderings:
            raise serializers.ValidationError(_("排序参数只能是 'create_at' 或 'node_count'。"))

        return value
