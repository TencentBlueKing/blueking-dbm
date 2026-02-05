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


class GenerateMySQLApplyPrivParamInputSerializer(serializers.Serializer):
    # bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    account_name = serializers.CharField(help_text=_("权限模版中的用户名"))
    dbnames = serializers.ListField(child=serializers.CharField(), help_text=_("权限模版中用户名下的 db 名"))
    apply_source_ips = serializers.ListField(child=serializers.CharField(), help_text=_("新权限访问来源 IP 列表, 允许带有 % 通配符"))
