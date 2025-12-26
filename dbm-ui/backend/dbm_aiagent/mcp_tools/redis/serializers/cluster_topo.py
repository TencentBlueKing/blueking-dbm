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

from backend.db_meta.enums import InstanceStatus


class RedisBaseInstanceSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    status = serializers.ChoiceField(choices=InstanceStatus.get_choices(), help_text=_("实例状态"))
    machine_type = serializers.CharField(help_text=_("实例机器类型"))


class RedisStorageInstanceSerializer(RedisBaseInstanceSerializer):
    is_stand_by = serializers.BooleanField(default=True, help_text=_("dbha 切换备选标志"))


class RedisTopoInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class RedisTopoOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    storage = RedisStorageInstanceSerializer(help_text=_("存储层实例信息"))
