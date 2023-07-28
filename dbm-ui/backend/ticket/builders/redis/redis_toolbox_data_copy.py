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

from backend.db_services.redis_dts.enums import DtsCopyType
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, DataCheckRepairSettingSerializer
from backend.ticket.constants import RemindFrequencyType, SyncDisconnectSettingType, TicketType, WriteModeType


class RedisDataCopyDetailSerializer(serializers.Serializer):
    """数据复制"""

    class SyncDisconnectSettingSerializer(serializers.Serializer):
        type = serializers.ChoiceField(choices=SyncDisconnectSettingType.get_choices())
        reminder_frequency = serializers.ChoiceField(
            choices=RemindFrequencyType.get_choices(), required=False, allow_blank=True
        )

    class BaseInfoSerializer(serializers.Serializer):
        key_white_regex = serializers.CharField(help_text=_("包含key"), allow_blank=True)
        key_black_regex = serializers.CharField(help_text=_("排除key"), allow_blank=True)

    class RedisDataCopyInnerInfoSerializer(BaseInfoSerializer):
        """业务内"""

        src_cluster = serializers.IntegerField(help_text=_("集群ID"))
        dst_cluster = serializers.IntegerField(help_text=_("集群ID"))

    class RedisDataCopyInnerTo3rdInfoSerializer(BaseInfoSerializer):
        """业务到第三方"""

        src_cluster = serializers.IntegerField(help_text=_("集群ID"))
        dst_cluster = serializers.CharField(help_text=_("集群IP端口"))
        dst_cluster_password = serializers.CharField(help_text=_("集群访问密码"))

    class RedisDataCopy3rdToInnerInfoSerializer(BaseInfoSerializer):
        """第三方到业务"""

        src_cluster = serializers.CharField(help_text=_("集群IP端口"))
        src_cluster_password = serializers.CharField(help_text=_("集群访问密码"))
        dst_cluster = serializers.IntegerField(help_text=_("集群ID"))

    class RedisDataCopyBetweenInnerInfoSerializer(BaseInfoSerializer):
        """业务之间"""

        src_cluster = serializers.IntegerField(help_text=_("集群ID"))
        dst_cluster = serializers.IntegerField(help_text=_("集群ID"))

    # 区分复制类型
    INFO_SERIALIZER_MAP = {
        DtsCopyType.ONE_APP_DIFF_CLUSTER: RedisDataCopyInnerInfoSerializer,
        DtsCopyType.DIFF_APP_DIFF_CLUSTER: RedisDataCopyBetweenInnerInfoSerializer,
        DtsCopyType.COPY_TO_OTHER_SYSTEM: RedisDataCopyInnerTo3rdInfoSerializer,
        DtsCopyType.USER_BUILT_TO_DBM: RedisDataCopy3rdToInnerInfoSerializer,
    }

    dts_copy_type = serializers.ChoiceField(choices=DtsCopyType.get_choices())
    write_mode = serializers.ChoiceField(choices=WriteModeType.get_choices())
    sync_disconnect_setting = SyncDisconnectSettingSerializer()
    data_check_repair_setting = DataCheckRepairSettingSerializer(required=False)

    infos = serializers.ListField(help_text=_("批量数据复制列表"), child=serializers.DictField(), allow_empty=False)

    def validate(self, attr):
        """根据复制类型校验info"""
        dts_copy_type = attr.get("dts_copy_type")
        info_serializer = self.INFO_SERIALIZER_MAP.get(dts_copy_type)
        info_serializer(data=attr["infos"], many=True).is_valid(raise_exception=True)

        key_white_regex_cnt = sum(map(lambda info: 1 if len(info["key_white_regex"]) else 0, attr["infos"]))
        key_black_regex_cnt = sum(map(lambda info: 1 if len(info["key_black_regex"]) else 0, attr["infos"]))
        if (key_white_regex_cnt + key_black_regex_cnt) < len(attr["infos"]):
            raise serializers.ValidationError("请补齐缺少正则配置的行")

        return attr


class RedisDataCopyParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_data_copy

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisDataCopyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_DATA_COPY)
class RedisDataCopyFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisDataCopyDetailSerializer
    inner_flow_builder = RedisDataCopyParamBuilder
    inner_flow_name = _("Redis 数据复制")
    resource_batch_apply_builder = RedisDataCopyResourceParamBuilder

    @property
    def need_itsm(self):
        return False
