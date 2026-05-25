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

from backend.db_dirty.constants import PoolType
from backend.db_services.cmdb.biz import get_resource_biz


class ResourceImportHostSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("机器当前所属的业务id"), required=False, default=get_resource_biz())
    ip = serializers.CharField(help_text=_("主机ipv4(多个则逗号隔开)"), required=False)
    host_name = serializers.CharField(help_text=_("主机名称(多个则逗号隔开)"), required=False)
    ip_v6 = serializers.CharField(help_text=_("主机ipv6(多个则逗号隔开)"), required=False)
    for_biz = serializers.IntegerField(help_text=_("专属业务, 默认公共资源池"), required=False, default=0)
    resource_type = serializers.CharField(help_text=_("专属DB, 默认通用"), required=False, default="PUBLIC")


class ResourceImportOutPutSerializer(serializers.Serializer):
    ticket_ids = serializers.ListField(child=serializers.IntegerField())


class ResourceUnDoImportSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("机器当前所属的业务id"), required=False, default=get_resource_biz())
    ip = serializers.CharField(help_text=_("主机ipv4(多个则逗号隔开)"), required=False)
    host_id = serializers.CharField(help_text=_("主机id(多个则逗号隔开)"), required=False)


class ResourceUnDoImportOutPutSerializer(serializers.Serializer):
    data = serializers.CharField()


class ResourceHostDeleteSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("主机ipv4(多个则逗号隔开)"), required=False)
    host_id = serializers.CharField(help_text=_("主机id(多个则逗号隔开)"), required=False)
    remark = serializers.CharField(help_text=_("备注"), required=False)
    hcm_recycle = serializers.BooleanField(help_text=_("是否从海磊自动回收"), required=False, default=False)


class ResourceHostDeleteOutputSerializer(serializers.Serializer):
    message = serializers.CharField(help_text=_("消息"), required=False)
    hcm_recycle_id = serializers.CharField(help_text=_("海磊单据id"), required=False)


class ResourceTransferPoolSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("主机ipv4(多个则逗号隔开)"), required=False)
    host_id = serializers.CharField(help_text=_("主机id(多个则逗号隔开)"), required=False)
    target = serializers.ChoiceField(help_text=_("主机去向"), choices=PoolType.get_choices())
    remark = serializers.CharField(help_text=_("备注"), required=False)


class ResourceTransferPoolOutPutSerializer(serializers.Serializer):
    message = serializers.CharField(help_text=_("消息"), required=False)


class ResourceListOutPutSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField()
    ip = serializers.CharField()
    bk_host_id = serializers.IntegerField()
    bk_host_innerip = serializers.CharField()
    for_biz = serializers.JSONField()
    storage_device = serializers.JSONField()
    bk_cloud_id = serializers.IntegerField()
    bk_cloud_name = serializers.CharField()
    os_type = serializers.CharField()
    rack_id = serializers.CharField()
    sub_zone = serializers.CharField()
    sub_zone_id = serializers.CharField()
    bk_cpu = serializers.IntegerField()
    bk_disk = serializers.IntegerField()
    bk_mem = serializers.IntegerField()
