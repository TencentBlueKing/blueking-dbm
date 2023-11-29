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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_proxy.views.serialiers import BaseProxyPassSerialier


class ProxyPasswordSerializer(BaseProxyPassSerialier):
    class InstanceDetailSerializer(serializers.Serializer):
        ip = serializers.CharField(help_text=_("实例ip"))
        port = serializers.IntegerField(help_text=_("实例port"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域id，如果传入ip、port也要传入bk_cloud_id"))

    class UserDetailSerializer(serializers.Serializer):
        username = serializers.CharField(help_text=_("用户名称"))
        component = serializers.CharField(help_text=_("组件，比如mysql、redis、tbinlogdumper等"))

    instances = serializers.ListSerializer(help_text=_("实例列表"), child=InstanceDetailSerializer(), required=False)
    users = serializers.ListSerializer(help_text=_("信息列表"), child=UserDetailSerializer())
    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)
    begin_time = serializers.CharField(help_text=_("开始时间"), required=False)
    end_time = serializers.CharField(help_text=_("结束时间"), required=False)
