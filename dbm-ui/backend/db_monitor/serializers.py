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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.bk_web.serializers import AuditedSerializer
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_monitor import mock_data
from backend.db_monitor.constants import AlertLevelEnum, DetectAlgEnum, OperatorEnum, TargetLevel
from backend.db_monitor.models import CollectTemplate, MonitorPolicy, NoticeGroup, RuleTemplate
from backend.db_monitor.models.alarm import DutyRule
from backend.db_periodic_task.constants import NoticeSignalEnum


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
    class Meta:
        model = DutyRule
        fields = "__all__"


class DutyRuleCreateSerializer(DutyRuleSerializer):
    class Meta:
        model = NoticeGroup
        fields = "__all__"
        swagger_schema_fields = {"example": mock_data.CREATE_HANDOFF_DUTY_RULE}


class DutyRuleUpdateSerializer(DutyRuleSerializer):
    class Meta:
        model = NoticeGroup
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
        """监控事件跳转链接"""

        bk_biz_id = obj.bk_biz_id or env.DBA_APP_BK_BIZ_ID
        query_string = urllib.parse.urlencode(
            {
                "queryString": _("策略ID : {} AND 状态 : {}").format(obj.monitor_policy_id, _("未恢复")),
                "from": "now-30d",
                "to": "now",
                "bizIds": bk_biz_id,
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
        """告警目标"""

        class TargetRuleSerializer(serializers.Serializer):
            key = serializers.ChoiceField(choices=TargetLevel.get_choices())
            value = serializers.ListSerializer(child=serializers.CharField(), allow_empty=True)

        level = serializers.ChoiceField(choices=TargetLevel.get_choices())
        rule = TargetRuleSerializer()

    class TestRuleSerializer(serializers.Serializer):
        """检测规则"""

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


class ListModuleSerializer(ListClusterSerializer):
    pass
