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
import urllib.parse
from collections import defaultdict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.bk_web.serializers import AuditedSerializer
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache
from backend.db_monitor import mock_data
from backend.db_monitor.constants import (
    AlertLevelEnum,
    AlertStageEnum,
    AlertStatusEnum,
    DetectAlgEnum,
    OperatorEnum,
    TargetLevel,
)
from backend.db_monitor.exceptions import AutofixException
from backend.db_monitor.mock_data import CALLBACK_REQUEST
from backend.db_monitor.models import CollectTemplate, MonitorPolicy, NoticeGroup, RuleTemplate
from backend.db_monitor.models.alarm import DutyRule
from backend.db_periodic_task.constants import NoticeSignalEnum
from backend.ticket.constants import TicketType


class GetDashboardSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=True)
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), required=True)
    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    instance_id = serializers.IntegerField(help_text=_("节点实例ID"), required=False)


class DashboardUrlSerializer(serializers.Serializer):
    url = serializers.URLField(help_text=_("监控仪表盘地址"))


class NoticeGroupSerializer(AuditedSerializer, serializers.ModelSerializer):
    used_count = serializers.SerializerMethodField()

    def get_used_count(self, obj):
        return self.context["group_used"].get(obj.id, 0)

    class Meta:
        model = NoticeGroup
        fields = "__all__"


class NoticeGroupCreateSerializer(NoticeGroupSerializer):
    class Meta:
        model = NoticeGroup
        fields = ["name", "bk_biz_id", "receivers", "details"]
        swagger_schema_fields = {"example": mock_data.CREATE_NOTICE_GROUP}


class NoticeGroupUpdateSerializer(NoticeGroupSerializer):
    class Meta:
        model = NoticeGroup
        fields = ["name", "bk_biz_id", "receivers", "details"]
        swagger_schema_fields = {"example": mock_data.UPDATE_NOTICE_GROUP}


class DutyRuleSerializer(AuditedSerializer, serializers.ModelSerializer):
    biz_config_display = serializers.SerializerMethodField(help_text=_("业务配置信息"))

    @property
    def biz_name_map(self):
        if not hasattr(self, "_biz_name_map"):
            setattr(self, "_biz_name_map", AppCache.get_appcache(key="appcache_dict"))
        return self._biz_name_map

    class Meta:
        model = DutyRule
        fields = "__all__"

    def get_biz_config_display(self, obj):
        biz_config_display = defaultdict(dict)
        for key, bizs in obj.biz_config.items():
            infos = [{"bk_biz_id": biz, "bk_biz_name": self.biz_name_map[str(biz)]["bk_biz_name"]} for biz in bizs]
            biz_config_display[key] = infos
        return biz_config_display


class DutyRuleCreateSerializer(DutyRuleSerializer):
    class Meta:
        model = DutyRule
        fields = "__all__"
        swagger_schema_fields = {"example": mock_data.CREATE_HANDOFF_DUTY_RULE}


class DutyRuleUpdateSerializer(DutyRuleSerializer):
    class Meta:
        model = DutyRule
        fields = "__all__"
        swagger_schema_fields = {"example": mock_data.CREATE_CUSTOM_DUTY_RULE}


class CollectTemplateSerializer(AuditedSerializer, serializers.ModelSerializer):
    class Meta:
        model = CollectTemplate
        fields = "__all__"


class RuleTemplateSerializer(AuditedSerializer, serializers.ModelSerializer):
    class Meta:
        model = RuleTemplate
        fields = "__all__"


class MonitorPolicySerializer(AuditedSerializer, serializers.ModelSerializer):
    event_url = serializers.SerializerMethodField(method_name="get_event_url")

    def get_event_url(self, obj):
        """
        监控事件跳转链接
        """

        bk_biz_id = obj.bk_biz_id or env.DBA_APP_BK_BIZ_ID
        query_string = urllib.parse.urlencode(
            {
                "queryString": _("策略ID : {} AND 状态 : {}").format(obj.monitor_policy_id, _("未恢复")),
                "from": "now-30d",
                "to": "now",
                # -2 代表有告警的空间
                "bizIds": -2,
            }
        )

        return f"{env.BKMONITOR_URL}/?bizId={bk_biz_id}#/event-center?{query_string}"

    class Meta:
        model = MonitorPolicy
        fields = "__all__"


class MonitorPolicyListSerializer(MonitorPolicySerializer):
    event_count = serializers.SerializerMethodField(method_name="get_event_count")

    def get_event_count(self, obj):
        bk_biz_id = int(self.context["request"].query_params.get("bk_biz_id"))
        policy_events = self.context["events"].get(str(obj.monitor_policy_id), {})
        if bk_biz_id > 0:
            return int(policy_events.get(str(bk_biz_id), 0))
        return sum(map(lambda x: int(x), policy_events.values()))

    class Meta:
        model = MonitorPolicy
        exclude = ["details", "parent_details"]


class MonitorPolicyUpdateSerializer(AuditedSerializer, serializers.ModelSerializer):
    class TargetSerializer(serializers.Serializer):
        """
        告警目标
        """

        class TargetRuleSerializer(serializers.Serializer):
            key = serializers.ChoiceField(choices=TargetLevel.get_choices())
            value = serializers.ListSerializer(child=serializers.CharField(), allow_empty=True)

        level = serializers.ChoiceField(choices=TargetLevel.get_choices())
        rule = TargetRuleSerializer()

    class TestRuleSerializer(serializers.Serializer):
        """
        检测规则
        """

        class TestRuleConfigSerializer(serializers.Serializer):
            method = serializers.ChoiceField(choices=OperatorEnum.get_choices())
            threshold = serializers.IntegerField()

        type = serializers.ChoiceField(choices=DetectAlgEnum.get_choices(), required=False)
        level = serializers.ChoiceField(choices=AlertLevelEnum.get_choices())
        config = serializers.ListSerializer(
            child=serializers.ListField(child=TestRuleConfigSerializer()), allow_empty=False
        )
        unit_prefix = serializers.CharField(allow_blank=True)

    targets = serializers.ListField(child=TargetSerializer(), allow_empty=False)
    test_rules = serializers.ListField(child=TestRuleSerializer(), allow_empty=False)
    notify_rules = serializers.ListField(
        child=serializers.ChoiceField(choices=NoticeSignalEnum.get_choices()), allow_empty=False
    )
    notify_groups = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)

    class Meta:
        model = MonitorPolicy
        fields = ["targets", "test_rules", "notify_rules", "notify_groups", "custom_conditions"]


class BatchUpdateMonitorPolicyNotifySerializer(serializers.Serializer):
    policy_ids = serializers.ListField(help_text=_("策略ID列表"), child=serializers.IntegerField())
    notify_groups = serializers.ListField(help_text=_("告警组ID列表"), child=serializers.IntegerField())


class MonitorPolicyCloneSerializer(MonitorPolicyUpdateSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), min_value=1)
    custom_conditions = serializers.ListSerializer(child=serializers.JSONField(), allow_empty=True)

    def validate(self, attrs):
        """补充校验
        1. 非平台级告警必须指定目标业务
        """
        bk_biz_id = str(attrs["bk_biz_id"])
        target_app = list(
            filter(lambda x: x["level"] == TargetLevel.APP and x["rule"]["value"] == [bk_biz_id], attrs["targets"])
        )

        if not target_app:
            raise serializers.ValidationError(_("请确认告警目标包含当前业务"))

        return attrs

    class Meta:
        model = MonitorPolicy
        fields = [
            "name",
            "bk_biz_id",
            "parent_id",
            "targets",
            "test_rules",
            "notify_rules",
            "notify_groups",
            "custom_conditions",
        ]


class MonitorPolicyEmptySerializer(serializers.Serializer):
    pass


class ListClusterSerializer(serializers.Serializer):
    dbtype = serializers.ChoiceField(help_text=_("数据库类型"), choices=DBType.get_choices())
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class ListModuleSerializer(ListClusterSerializer):
    pass


class AlarmCallBackDataSerializer(serializers.Serializer):
    """
    告警回调数据
    """

    class CallBackMessageSerializer(serializers.Serializer):
        event = serializers.DictField(help_text=_("告警事件"))
        strategy = serializers.DictField(help_text=_("监控策略"))
        latest_anomaly_record = serializers.DictField(help_text=_("最新异常点信息"))
        labels = serializers.ListSerializer(help_text=_("标签"), child=serializers.CharField())

    appointees = serializers.CharField(help_text=_("告警负责人"))
    callback_message = CallBackMessageSerializer(help_text=_("回调消息体"))

    class Meta:
        swagger_schema_fields = {"example": CALLBACK_REQUEST}

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        ticket_types = []

        # 取关联的的故障自愈处理单据
        for label in data["callback_message"].get("labels") or []:
            if label.startswith("NEED_AUTOFIX"):
                ticket_type = label.split("/")[1]
                if ticket_type in TicketType.get_values():
                    ticket_types.append(ticket_type)

        # 未匹配到故障自愈处理单据
        if not ticket_types:
            raise AutofixException(_("未匹配到对应的故障自愈处理单据，请确认是否配置正确"))

        data.update({"ticket_types": ticket_types, "creator": "bkmonitor"})
        return data


class ListAlertSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    self_manage = serializers.BooleanField(help_text=_("是否待我处理"), default=False)
    self_assist = serializers.BooleanField(help_text=_("是否待我协助"), default=False)
    db_types = serializers.ListSerializer(help_text=_("数据库类型"), child=serializers.CharField(), required=False)
    severity = serializers.ChoiceField(help_text=_("告警级别"), choices=AlertLevelEnum.get_choices(), required=False)
    stage = serializers.ChoiceField(help_text=_("处理阶段"), choices=AlertStageEnum.get_choices(), required=False)
    status = serializers.ChoiceField(help_text=_("状态"), choices=AlertStatusEnum.get_choices(), required=False)
    page = serializers.IntegerField(help_text=_("页码"), default=1)
    page_size = serializers.IntegerField(help_text=_("每页数量"), default=100)
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))

    class Meta:
        swagger_schema_fields = {
            "example": {
                "bk_biz_id": 101068,
                "self_manage": True,
                "self_assist": False,
                "start_time": None,
                "end_time": None,
            }
        }


class CreateAlarmShieldSerializer(serializers.Serializer):
    category = serializers.CharField(help_text=_("屏蔽类型"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=True)
    dimension_config = serializers.DictField(help_text=_("屏蔽维度配置"))
    shield_notice = serializers.BaseSerializer(help_text=_("告警屏蔽通知"), default=False)
    begin_time = serializers.CharField(help_text=_("开始时间"))
    end_time = serializers.CharField(help_text=_("结束时间"))
    description = serializers.CharField(help_text=_("屏蔽原因"))

    def to_internal_value(self, data):
        return data

    def validate(self, attrs):
        # 取维度中的 appid 维度作为业务，这里要求屏蔽策略的维度一定要有业务
        for condition in attrs["dimension_config"]["dimension_conditions"]:
            if condition["key"] == "appid":
                attrs["bk_biz_id"] = condition["value"][0]
        if "bk_biz_id" not in attrs:
            raise serializers.ValidationError(_("维度配置中必须包含业务ID"))
        return attrs

    class Meta:
        swagger_schema_fields = {"example": mock_data.CREATE_ALARM_SHIELD_FOR_DIMENSION}


class UpdateAlarmShieldSerializer(serializers.Serializer):
    begin_time = serializers.CharField(help_text=_("开始时间"))
    end_time = serializers.CharField(help_text=_("结束时间"))
    description = serializers.CharField(help_text=_("屏蔽原因"))
    cycle_config = serializers.DictField(help_text=_("屏蔽周期"))
    shield_notice = serializers.BooleanField(help_text=_("是否有屏蔽通知"), default=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.UPDATE_ALARM_SHIELD}


class DisableAlarmShieldSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("屏蔽 ID"))


class ListAlarmShieldSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    is_active = serializers.BooleanField(help_text=_("是否生效"), default=True)
    time_range = serializers.CharField(help_text=_("时间范围"), required=False)
    page = serializers.IntegerField(help_text=_("页码"), default=1)
    page_size = serializers.IntegerField(help_text=_("每页数量"), default=10)
    category = serializers.CharField(help_text=_("屏蔽类型"), required=False)
    conditions = serializers.ListSerializer(help_text=_("查询条件"), child=serializers.DictField(), required=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.LIST_ALARM_SHIELD}
