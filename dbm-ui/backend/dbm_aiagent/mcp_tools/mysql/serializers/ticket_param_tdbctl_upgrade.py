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


class GenerateTdbctlUpgradeParamInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(
        help_text=_("集群域名（可选，与 cluster_id 二选一）"),
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    cluster_id = serializers.IntegerField(
        help_text=_("集群ID（可选，与 cluster_id 二选一）"),
        required=False,
        allow_null=True,
    )
    version = serializers.CharField(
        help_text=_("升级版本号（可选，如 2.4.13，不传则使用最新创建的 tdbctl 包）"),
        required=False,
        allow_null=True,
        allow_blank=True,
    )
