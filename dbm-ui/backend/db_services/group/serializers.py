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

from backend.bk_web.serializers import AuditedSerializer
from backend.db_meta.models import Group, GroupInstance


class GroupSerializer(AuditedSerializer, serializers.ModelSerializer):
    instance_count = serializers.SerializerMethodField(help_text=_("实例数量"))

    class Meta:
        model = Group
        fields = "__all__"
        read_only_fields = ("id",) + model.AUDITED_FIELDS
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Group.objects.all(), fields=("bk_biz_id", "name"), message=_("在该业务下已存在同名的分组，请重新命名分组")
            )
        ]

    def get_instance_count(self, obj):
        instance_count = GroupInstance.objects.filter(group_id=obj.id).count()
        return instance_count


class GroupMoveInstancesSerializer(serializers.Serializer):
    new_group_id = serializers.IntegerField(help_text=_("新分组ID"))
    instance_ids = serializers.ListSerializer(help_text=_("待移动实例的ID列表"), child=serializers.IntegerField())
