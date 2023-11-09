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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterEntryType


class ModifyClusterEntrySerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    cluster_entry_type = serializers.ChoiceField(help_text=_("集群 ID"), choices=ClusterEntryType.get_choices())

    domain_name = serializers.CharField(help_text=_("域名"), required=False)
    target_instances = serializers.ListSerializer(
        child=serializers.CharField(help_text=_("目标实例，格式为 ip#port ")), help_text=_("目标实例列表"), required=False
    )

    def validate(self, attrs):
        if attrs["cluster_entry_type"] == ClusterEntryType.DNS:
            if not all(key in attrs for key in ("domain_name", "target_instances")):
                raise serializers.ValidationError(_("修改 DNS 访问入口需要传入 domain_name 和 target_instances"))
        return attrs
