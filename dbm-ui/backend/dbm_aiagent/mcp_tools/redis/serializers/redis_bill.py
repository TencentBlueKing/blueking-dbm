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

from backend.flow.consts import DbBackupRoleEnum, RedisBackupEnum


class SubmitBillOutputSerializer(serializers.Serializer):
    bill_id = serializers.IntegerField(help_text=_("单据id"))


class SubmitBillRedisFullBackupInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名，cluster domain"))
    backup_type = serializers.ChoiceField(
        choices=RedisBackupEnum.get_choices(), default=RedisBackupEnum.NORMAL_BACKUP, help_text=_("备份类型")
    )
    target = serializers.ChoiceField(
        choices=DbBackupRoleEnum.get_choices(), default=DbBackupRoleEnum.Slave, help_text=_("备份对象")
    )


class SubmitBillRedisProxyReduceOrIncreaseInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名，cluster domain"))
    proxy_change_count = serializers.IntegerField(help_text=_("proxy变动数量"))


class SubmitBillRedisProxyReduceByIpInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名，cluster domain"))
    reduce_ips = serializers.ListField(child=serializers.CharField(), help_text=_("指定下架proxy的IP列表"))
