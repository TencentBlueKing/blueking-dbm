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
from collections import defaultdict
from typing import List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import RedisHotKeyInfo
from backend.flow.consts import StateType
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import DisplayInfoSerializer, SkipToRepresentationMixin
from backend.ticket.builders.redis.base import ClusterValidateMixin, RedisALLInstanceTicketFlowBuilder
from backend.ticket.constants import TicketFlowStatus, TicketType


class RedisHotKeyAnalysisDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """热key分析参数序列化器"""

    class InfoSerializer(DisplayInfoSerializer, ClusterValidateMixin, serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        ins = serializers.ListField(help_text=_("实例列表"), child=serializers.CharField())
        immute_domain = serializers.CharField(help_text=_("域名"))
        cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    analysis_time = serializers.IntegerField(help_text=_("分析时长"))
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisHotKeyAnalysisParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_hotkey_analysis

    def post_callback(self):
        flow = self.ticket.current_flow()
        # 更新记录表状态
        record_ids = [info["record_id"] for info in self.ticket_data["infos"]]
        if flow.status == TicketFlowStatus.SUCCEEDED.value:
            RedisHotKeyInfo.objects.filter(id__in=record_ids, status=StateType.RUNNING).update(
                status=StateType.FINISHED
            )
        else:
            RedisHotKeyInfo.objects.filter(id__in=record_ids, status=StateType.RUNNING).update(status=flow.status)


@builders.BuilderFactory.register(TicketType.REDIS_HOT_KEY_ANALYSIS)
class RedisHotKeyAnalysisFlowBuilder(RedisALLInstanceTicketFlowBuilder):
    serializer = RedisHotKeyAnalysisDetailSerializer
    inner_flow_builder = RedisHotKeyAnalysisParamBuilder
    inner_flow_name = _("Redis 热key分析")

    def create_hot_key_infos(self):
        # 创建热key记录
        record_infos: List[RedisHotKeyInfo] = []
        for index, info in enumerate(self.ticket.details["infos"]):
            record_info = RedisHotKeyInfo(
                bk_biz_id=self.ticket.bk_biz_id,
                ins_list=info["ins"],
                cluster_id=info["cluster_id"],
                cluster_type=info["cluster_type"],
                immute_domain=info["immute_domain"],
                analysis_time=self.ticket.details["analysis_time"],
                ticket_id=self.ticket.id,
                status=StateType.READY,
                creator=self.ticket.creator,
            )
            record_infos.append(record_info)

        RedisHotKeyInfo.objects.bulk_create(record_infos)
        record_infos = RedisHotKeyInfo.objects.filter(ticket_id=self.ticket.id)

        record_info_map = defaultdict(dict)
        for record_info in record_infos:
            record_info_map[record_info.ticket_id][record_info.cluster_id] = record_info.id

        for info in self.ticket.details["infos"]:
            info["record_id"] = record_info_map[self.ticket.id][info["cluster_id"]]

    def patch_ticket_detail(self):
        self.create_hot_key_infos()
        super().patch_ticket_detail()
