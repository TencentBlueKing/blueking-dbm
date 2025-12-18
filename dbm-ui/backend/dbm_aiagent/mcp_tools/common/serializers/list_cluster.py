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

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.flow.consts import ClusterStatus


class ListBizClustersInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"), required=True)
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), help_text=_("集群类型"), required=True)


class ClusterBaseInfoSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), help_text=_("集群类型"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    region = serializers.CharField(help_text=_("所在地域, 城市, city"))
    affinity = serializers.ChoiceField(choices=AffinityEnum.get_choices(), help_text=_("亲和性"))
    status = serializers.ChoiceField(choices=ClusterStatus.get_choices(), help_text=_("集群状态"))


class ListBizClustersOutputSerializer(serializers.Serializer):
    clusters = serializers.ListSerializer(child=ClusterBaseInfoSerializer(), help_text=_("集群列表"))
