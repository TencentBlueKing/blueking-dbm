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

from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.views.serialiers import BaseProxyPassSerializer


class InsertDBExtensionSerializer(BaseProxyPassSerializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), default=0)
    extension = serializers.ChoiceField(help_text=_("扩展类型"), choices=ExtensionType.get_choices())
    details = serializers.JSONField(help_text=_("详情"))
