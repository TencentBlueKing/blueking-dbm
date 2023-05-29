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

from backend.db_proxy.views.serialiers import BaseProxyPassSerialier


class RPCSerializer(BaseProxyPassSerialier):
    addresses = serializers.ListField(help_text=_("实例列表"), child=serializers.CharField())
    cmds = serializers.ListField(help_text=_("SQL命令列表"), child=serializers.CharField())
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)


class RPCResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {}}
