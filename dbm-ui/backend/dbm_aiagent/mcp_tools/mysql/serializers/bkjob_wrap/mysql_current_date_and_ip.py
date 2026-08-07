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


class MysqlCurrentDateAndIpInputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("目标 IP 列表"))
    bk_scope_type = serializers.CharField(help_text=_("资源范围类型，例如 biz_set"))
    bk_scope_id = serializers.CharField(help_text=_("资源范围 ID"))
