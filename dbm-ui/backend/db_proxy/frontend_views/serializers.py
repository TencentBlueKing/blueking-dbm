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


class ListDBExtensionSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))

    class BaseField(serializers.Serializer):
        ip = serializers.CharField(help_text=_("主机IP"))
        status = serializers.CharField(help_text=_("状态"))
        bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        updater = serializers.CharField(help_text=_("更新人"))
        update_at = serializers.CharField(help_text=_("更新时间"))

    class NGINX(BaseField):
        bk_outer_ip = serializers.CharField(help_text=_("外网IP"))

    class DNS(BaseField):
        bk_city = serializers.CharField(help_text=_("城市"))
        is_access = serializers.BooleanField(help_text=_("是否启用"), required=False, default=True)

    class DRS(BaseField):
        pass

    class DBHA(BaseField):
        bk_city_name = serializers.CharField(help_text=_("城市名称"))
        dbha_type = serializers.CharField(help_text=_("类型"))

    class REDIS_DTS(BaseField):
        bk_city_name = serializers.CharField(help_text=_("城市名称"))
