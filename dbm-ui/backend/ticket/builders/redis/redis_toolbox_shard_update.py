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
from backend.ticket.builders.redis.base import DataCheckRepairSettingSerializer
from backend.ticket.constants import SwitchConfirmType


class RedisShardUpdateDetailSerializer(serializers.Serializer):
    """集群分片变更"""

    class InfoSerializer(serializers.Serializer):
        src_cluster = serializers.IntegerField(help_text=_("集群ID"))
        current_shard_num = serializers.IntegerField(help_text=_("当前分片数"))
        target_shard_num = serializers.IntegerField(help_text=_("目标分片数"))
        current_deploy_plan = serializers.IntegerField(help_text=_("当前方案"))
        target_deploy_plan = serializers.IntegerField(help_text=_("目标方案"))

    data_check_repair_setting = DataCheckRepairSettingSerializer()
    online_switch_type = serializers.ChoiceField(
        help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
    )
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = InfoSerializer(many=True, help_text=_("批量操作参数列表"))
