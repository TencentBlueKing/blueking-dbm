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


class ListHostsWithoutBizInputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("IP 列表"))


class CCHostInfoSerializer(serializers.Serializer):
    bk_agent_id = serializers.CharField(help_text=_("Agent ID"))
    bk_bak_operator = serializers.CharField(help_text=_("备份负责人"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    bk_cloud_inst_id = serializers.CharField(help_text=_("云实例 ID"))
    bk_host_id = serializers.IntegerField(help_text=_("主机 ID"))
    bk_host_innerip = serializers.CharField(help_text=_("内网 IP"))
    bk_idc_area = serializers.CharField(help_text=_("IDC 区域"))
    bk_idc_area_id = serializers.IntegerField(help_text=_("IDC 区域 ID"))
    bk_os_name = serializers.CharField(help_text=_("操作系统"))
    bk_svr_device_cls_name = serializers.CharField(help_text=_("机型"))
    idc_city_id = serializers.CharField(help_text=_("城市 ID"))
    idc_city_name = serializers.CharField(help_text=_("城市"))
    idc_id = serializers.IntegerField(help_text=_("IDC ID"))
    idc_name = serializers.CharField(help_text=_("IDC 名称"))
    net_device_id = serializers.CharField(help_text=_("网络设备 ID"))
    operator = serializers.CharField(help_text=_("负责人"))
    rack = serializers.CharField(help_text=_("机架"))
    rack_id = serializers.CharField(help_text=_("机架 ID"))
    sub_zone = serializers.CharField(help_text=_("园区"))
    sub_zone_id = serializers.CharField(help_text=_("园区 ID"))


class ListHostsWithoutBizOutputSerializer(serializers.Serializer):
    info = serializers.ListField(child=CCHostInfoSerializer())
