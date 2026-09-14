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


class VMStorageCLBSerializer(serializers.Serializer):
    """启用/停用 vmstorage 实例级 CLB 暴露的入参

    接受 cluster_id + enable，集群身份、共享 CLB ID 等信息全部由服务端校验与解析。
    """

    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=True)
    enable = serializers.BooleanField(help_text=_("true 启用实例级暴露；false 停用"), required=True)
