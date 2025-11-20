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

from backend.db_meta.enums import ClusterPhase, ClusterStatus, ClusterType
from backend.db_proxy.views.serialiers import BaseProxyPassSerializer


class CreateClusterSerializer(BaseProxyPassSerializer):
    """创建集群序列化器"""

    name = serializers.CharField(help_text=_("集群名称"))
    alias = serializers.CharField(help_text=_("集群别名"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    major_version = serializers.CharField(help_text=_("主版本"))
    phase = serializers.ChoiceField(help_text=_("阶段"), choices=ClusterPhase.get_choices())
    status = serializers.ChoiceField(help_text=_("状态"), choices=ClusterStatus.get_choices())
    region = serializers.CharField(help_text=_("区域"))
    operator = serializers.CharField(help_text=_("操作人"))


class DeleteClusterSerializer(BaseProxyPassSerializer):
    """删除集群序列化器"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    name = serializers.CharField(help_text=_("集群名称"))


class UpdateClusterSerializer(CreateClusterSerializer):
    """更新集群序列化器"""

    cluster_entry_type = serializers.CharField(help_text=_("入口类型"))
