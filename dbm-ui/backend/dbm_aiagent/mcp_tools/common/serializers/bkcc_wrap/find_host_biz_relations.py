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


class FindHostBizRelationsInputSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(child=serializers.IntegerField(), help_text=_("主机 ID"))


class HostBizRelationSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bk_host_id = serializers.IntegerField(help_text=_("主机 ID"))
    bk_module_id = serializers.IntegerField(help_text=_("模块 ID"))
    bk_set_id = serializers.IntegerField(help_text=_("集群 ID"))
    bk_supplier_account = serializers.CharField(help_text=_("开发商账号"))


class FindHostBizRelationsOutputSerializer(serializers.Serializer):
    info = serializers.ListField(child=HostBizRelationSerializer(), help_text=_("主机归属关系列表"))
