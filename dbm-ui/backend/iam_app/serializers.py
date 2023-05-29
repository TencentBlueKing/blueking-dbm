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


class IamActionResourceRequestSerializer(serializers.Serializer):
    class ResourceSerializer(serializers.Serializer):
        type = serializers.CharField(help_text=_("资源类型"))
        id = serializers.CharField(help_text=_("资源ID"))

    action_ids = serializers.ListField(help_text=_("动作ID列表"), min_length=0)
    resources = serializers.ListField(help_text=_("资源列表"), child=ResourceSerializer(), min_length=0)
