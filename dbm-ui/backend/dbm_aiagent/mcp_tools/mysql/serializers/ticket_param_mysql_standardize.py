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


class GenerateMySQLStandardizeParamInputSerializer(serializers.Serializer):
    # bk_cloud_id = serializers.Serializer(help_text=_("云区域 ID"))
    # bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domains = serializers.ListField(child=serializers.CharField(), help_text=_("集群域名列表"))
    with_instance_standardize = serializers.BooleanField(
        help_text=_("是否实例标准化, 重建 DBM 系统库表和权限. 高危慎用"), default=False, required=False
    )
    with_cc_standardize = serializers.BooleanField(
        help_text=_("是否 CC 标准化, 重建服务实例和部署蓝鲸插件"), default=False, required=False
    )
    with_deploy_binary = serializers.BooleanField(
        help_text=_("是否部署工具二进制, 包含 mysql-monitor, dbbackup, binlog-rotate, checksum"), default=False
    )
    with_push_config = serializers.BooleanField(help_text=_("是否推送工具配置"), default=True)
