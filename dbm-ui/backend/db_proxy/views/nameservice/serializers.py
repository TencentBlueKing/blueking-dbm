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


class CLBDeregisterPartTargetSerializer(BaseProxyPassSerialier):
    region = serializers.CharField(help_text=_("中文区域名称"))
    loadbalancerid = serializers.CharField(help_text=_("clb的id"))
    listenerid = serializers.CharField(help_text=_("clb监听器的id"))
    ips = serializers.ListField(help_text=_("需要解绑的后端主机端口数组"), child=serializers.CharField())


class CLBGetTargetPrivateIps(BaseProxyPassSerialier):
    region = serializers.CharField(help_text=_("中文区域名称"))
    loadbalancerid = serializers.CharField(help_text=_("clb的id"))
    listenerid = serializers.CharField(help_text=_("clb监听器的id"))


class PolarisDescribeTargetsSerializer(BaseProxyPassSerialier):
    servicename = serializers.CharField(help_text=_("北极星服务名称"))


class PolarisUnbindPartTargetsSerializer(BaseProxyPassSerialier):
    servicename = serializers.CharField(help_text=_("北极星服务名称"))
    servicetoken = serializers.CharField(help_text=_("北极星服务token"))
    ips = serializers.ListField(help_text=_("需要解绑的后端主机端口数组, 格式为“ip:port"), child=serializers.CharField())
