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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpSource
from backend.db_services.redis_dts.constants import DtsCopyType
from backend.ticket.builders.redis.base import DataCheckRepairSettingSerializer
from backend.ticket.constants import RemindFrequencyType, SyncDisconnectSettingType, WriteModeType


class RedisDataCopyBaseDetailSerializer(serializers.Serializer):
    """数据复制"""

    class SyncDisconnectSettingSerializer(serializers.Serializer):
        type = serializers.ChoiceField(choices=SyncDisconnectSettingType.get_choices())
        reminder_frequency = serializers.ChoiceField(choices=RemindFrequencyType.get_choices())

    dts_copy_type = serializers.ChoiceField(choices=DtsCopyType.get_choices())
    write_mode = serializers.ChoiceField(choices=WriteModeType.get_choices())
    sync_disconnect_setting = SyncDisconnectSettingSerializer()
    data_check_repair_setting = DataCheckRepairSettingSerializer()

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())


class BaseInfoSerializer(serializers.Serializer):
    key_white_regex = serializers.CharField(help_text=_("包含key"), allow_null=True)
    key_black_regex = serializers.CharField(help_text=_("排除key"), allow_blank=True)


class RedisDataCopyInnerDetailSerializer(RedisDataCopyBaseDetailSerializer):
    """业务内"""

    class InfoSerializer(BaseInfoSerializer):
        src_cluster = serializers.IntegerField(help_text=_("集群ID"))
        dst_cluster = serializers.IntegerField(help_text=_("集群ID"))

    infos = InfoSerializer(many=True, help_text=_("批量操作参数列表"))


class RedisDataCopyInnerTo3rdDetailSerializer(RedisDataCopyBaseDetailSerializer):
    """业务到第三方"""

    class InfoSerializer(BaseInfoSerializer):
        src_cluster = serializers.IntegerField(help_text=_("集群ID"))
        dst_cluster = serializers.CharField(help_text=_("集群IP端口"))
        dst_cluster_password = serializers.CharField(help_text=_("集群访问密码"))

    infos = InfoSerializer(many=True, help_text=_("批量操作参数列表"))


class RedisDataCopy3rdToInnerDetailSerializer(RedisDataCopyBaseDetailSerializer):
    """第三方到业务"""

    class InfoSerializer(BaseInfoSerializer):
        src_cluster = serializers.CharField(help_text=_("集群IP端口"))
        src_cluster_password = serializers.CharField(help_text=_("集群访问密码"))
        dst_cluster = serializers.IntegerField(help_text=_("集群ID"))

    infos = InfoSerializer(many=True, help_text=_("批量操作参数列表"))


class RedisDataCopyBetweenInnerDetailSerializer(RedisDataCopyBaseDetailSerializer):
    """业务之间"""

    class InfoSerializer(BaseInfoSerializer):
        src_cluster = serializers.IntegerField(help_text=_("集群ID"))
        dst_cluster = serializers.IntegerField(help_text=_("集群ID"))

    infos = InfoSerializer(many=True, help_text=_("批量操作参数列表"))


# 区分复制类型
DETAIL_SERIALIZER_MAP = {
    DtsCopyType.ONE_APP_DIFF_CLUSTER: RedisDataCopyInnerDetailSerializer,
    DtsCopyType.DIFF_APP_DIFF_CLUSTER: RedisDataCopyBetweenInnerDetailSerializer,
    DtsCopyType.COPY_TO_OTHER_SYSTEM: RedisDataCopyInnerTo3rdDetailSerializer,
    DtsCopyType.USER_BUILT_TO_DBM: RedisDataCopy3rdToInnerDetailSerializer,
}
