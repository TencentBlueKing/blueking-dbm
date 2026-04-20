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


class ShowDatabasesWithPatternsInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    dbs = serializers.ListField(child=serializers.CharField(), help_text=_('数据库列表, 允许带有 %, ?, * 这样的通配, 所有库["*"]'))
    ignore_dbs = serializers.ListField(child=serializers.CharField(), help_text=_("忽略数据库列表, 默认[], 允许带有 %, ?, * 这样的通配"))


class ShowDatabasesWithPatternsOutputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    databases = serializers.ListField(child=serializers.CharField(), help_text=_("匹配到的数据库列表"))
