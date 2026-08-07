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
from backend.core.notify.constants import MsgType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache
from backend.db_monitor import mock_data
from backend.db_monitor.constants import (
    AlertLevelEnum,
    AlertRecoveryStatusEnum,
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


class GetBusinessDashboardSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class DashboardUrlSerializer(serializers.Serializer):
    url = serializers.URLField(help_text=_("监控仪表盘地址"))


class NoticeGroupSerializer(AuditedSerializer, serializers.ModelSerializer):
    used_count = serializers.SerializerMethodField()

    def get_used_count(self, obj):
        return self.context["group_used"].get(obj.id, {})

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
        exclude = ["parent_details"]


class MonitorPolicyUpdateSerializer(AuditedSerializer, serializers.ModelSerializer):
    class TargetSerializer(serializers.Serializer):
        """
        告警目标
        """

        class TargetRuleSerializer(serializers.Serializer):
            key = serializers.CharField(help_text=_("指标名"))
            value = serializers.ListSerializer(child=serializers.CharField(), allow_empty=True)
            method = serializers.CharField(help_text=_("条件符号"))

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

    class DetectsConfigSerializer(serializers.Serializer):
        class TriggerConfigSerializer(serializers.Serializer):
            count = serializers.IntegerField(help_text=_("触发次数"))
            check_window = serializers.IntegerField(help_text=_("检测周期（分钟）"))
            uptime = serializers.JSONField(help_text=_("生效时间配置"))

        class RecoveryConfigSerializer(serializers.Serializer):
            check_window = serializers.IntegerField(help_text=_("检测周期（分钟）"))
            status_setter = serializers.ChoiceField(
                help_text=_("告警恢复目标状态"),
                default=AlertRecoveryStatusEnum.RECOVERY,
                choices=AlertRecoveryStatusEnum.get_choices(),
            )

        trigger_config = TriggerConfigSerializer()
        recovery_config = RecoveryConfigSerializer()

    class NoDataConfigSerializer(serializers.Serializer):
        level = serializers.ChoiceField(choices=AlertLevelEnum.get_choices(), help_text=_("告警级别"))
        continuous = serializers.IntegerField(help_text=_("周期"))
        is_enabled = serializers.BooleanField(help_text=_("无数据开关"), default=False)
        agg_dimension = serializers.ListSerializer(help_text=_("维度"), child=serializers.CharField(), allow_empty=True)

    class NotifyConfigSerializer(serializers.Serializer):
        interval_notify_mode = serializers.CharField(help_text=_("通知间隔类型"))
        notify_interval = serializers.IntegerField(help_text=_("通知间隔时间（秒）"))
        voice_notice = serializers.CharField(help_text=_("拨打语音方式"), required=False)

    class AggInfoSerializer(serializers.Serializer):
        metric_id = serializers.CharField(help_text=_("metric id"))
        agg_interval = serializers.IntegerField(help_text=_("周期"), required=False, allow_null=True)
        agg_method = serializers.CharField(help_text=_("汇聚方式"), required=False, allow_null=True)
        metric_field = serializers.CharField(help_text=_("指标名称"), required=False, allow_null=True)
        promql = serializers.CharField(help_text=_("sql语句"), required=False, allow_null=True)

    targets = serializers.ListField(child=TargetSerializer(), allow_empty=False)
    test_rules = serializers.ListField(child=TestRuleSerializer(), allow_empty=False)
    detects_config = DetectsConfigSerializer()
    no_data_config = NoDataConfigSerializer()
    notify_config = NotifyConfigSerializer()
    agg_info = serializers.ListField(child=AggInfoSerializer(), allow_empty=False)
    notify_rules = serializers.ListField(
        child=serializers.ChoiceField(choices=NoticeSignalEnum.get_choices()), allow_empty=False
    )
    notify_groups = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)
    name = serializers.CharField(help_text=_("策略名称"), required=False)
    get_data_time = serializers.DateTimeField(help_text=_("获取到数据的时间"), required=False)

    class Meta:
        model = MonitorPolicy
        fields = [
            "name",
            "is_enabled",
            "policy_tag",
            "targets",
            "test_rules",
            "notify_rules",
            "notify_groups",
            "custom_conditions",
            "detects_config",
            "no_data_config",
            "notify_config",
            "agg_info",
            "get_data_time",
        ]


class BatchUpdateMonitorPolicyNotifySerializer(serializers.Serializer):
    class NoticeGroupInfoSerializer(serializers.Serializer):
        policy_id = serializers.IntegerField(help_text=_("策略ID"))
        groups = serializers.ListField(help_text=_("告警组ID列表"), child=serializers.IntegerField())

    notify_groups = serializers.ListSerializer(help_text=_("告警组ID列表"), child=NoticeGroupInfoSerializer())
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    voice_notice = serializers.CharField(help_text=_("语音拨打类型"), required=False)


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
            "is_enabled",
            "policy_tag",
            "bk_biz_id",
            "parent_id",
            "targets",
            "test_rules",
            "notify_rules",
            "notify_groups",
            "custom_conditions",
            "detects_config",
            "no_data_config",
            "notify_config",
            "agg_info",
            "get_data_time",
        ]


class MonitorPolicyEmptySerializer(serializers.Serializer):
    pass


class MonitorPolicyResetSerializer(serializers.Serializer):
    policy_id = serializers.IntegerField(help_text=_("策略ID"))

    def validate(self, attrs):
        policy = MonitorPolicy.objects.filter(id=attrs["policy_id"], target_level=TargetLevel.PLATFORM.value).first()
        if not policy:
            raise serializers.ValidationError(_("此策略id非平台策略，不可重置"))
        return attrs


class ListClusterSerializer(serializers.Serializer):
    dbtype = serializers.ChoiceField(help_text=_("数据库类型"), choices=DBType.get_choices(), required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class ListModuleSerializer(ListClusterSerializer):
    pass


class AlarmStrategySerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务id"), default=env.DBA_APP_BK_BIZ_ID)
    monitor_policy_id = serializers.IntegerField(help_text=_("监控策略id"))


class AlarmCallBackDataSerializer(serializers.Serializer):
    """
    告警回调数据
    """

    class CallBackMessageSerializer(serializers.Serializer):
        event = serializers.DictField(help_text=_("告警事件"))
        strategy = serializers.DictField(help_text=_("监控策略"))
        latest_anomaly_record = serializers.DictField(help_text=_("最新异常点信息"))
        labels = serializers.ListSerializer(help_text=_("标签"), child=serializers.CharField())

        class Meta:
            ref_name = "AlarmCallBackMessage"

    appointees = serializers.CharField(help_text=_("告警负责人"))
    callback_message = CallBackMessageSerializer(help_text=_("回调消息体"))

    class Meta:
        swagger_schema_fields = {"example": CALLBACK_REQUEST}

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        ticket_types = []

        # 取关联的的故障自愈处理单据
        for label in data["callback_message"].get("labels") or []:
            if label.upper().startswith("NEED_AUTOFIX"):
                ticket_type = label.split("/")[1]
                if ticket_type in TicketType.get_values():
                    ticket_types.append(ticket_type)

        # 未匹配到故障自愈处理单据
        if not ticket_types:
            raise AutofixException(_("未匹配到对应的故障自愈处理单据，请确认是否配置正确"))

        data.update({"ticket_types": ticket_types, "creator": "bkmonitor"})
        return data


class MySQLAlarmCallbackDataSerializer(serializers.Serializer):
    """
    告警回调数据（处理套餐），不含故障自愈的 NEED_AUTOFIX 校验逻辑
    """

    class AlertCallBackMessageSerializer(serializers.Serializer):
        event = serializers.DictField(help_text=_("告警事件"))
        strategy = serializers.DictField(help_text=_("监控策略"))
        latest_anomaly_record = serializers.DictField(help_text=_("最新异常点信息"))
        labels = serializers.ListSerializer(help_text=_("标签"), child=serializers.CharField(), required=False)

        class Meta:
            ref_name = "MySQLAlarmCallBackMessage"

    appointees = serializers.CharField(help_text=_("告警负责人"))
    callback_message = AlertCallBackMessageSerializer(help_text=_("回调消息体"))


class ListAlertSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    self_manage = serializers.BooleanField(help_text=_("是否待我处理"), default=False)
    self_assist = serializers.BooleanField(help_text=_("是否待我协助"), default=False)
    db_types = serializers.ListSerializer(help_text=_("数据库类型"), child=serializers.CharField(), required=False)
    cluster_domain = serializers.CharField(help_text=_("告警集群"), required=False)
    instance = serializers.CharField(help_text=_("告警实例"), required=False)
    ip = serializers.CharField(help_text=_("告警IP"), required=False)
    alert_name = serializers.CharField(help_text=_("告警名称"), required=False)
    description = serializers.CharField(help_text=_("告警内容"), required=False)
    severity = serializers.ChoiceField(help_text=_("告警级别"), choices=AlertLevelEnum.get_choices(), required=False)
    stage = serializers.ChoiceField(help_text=_("处理阶段"), choices=AlertStageEnum.get_choices(), required=False)
    status = serializers.ChoiceField(help_text=_("状态"), choices=AlertStatusEnum.get_choices(), required=False)
    offset = serializers.IntegerField(help_text=_("分页偏移量"), default=0)
    limit = serializers.IntegerField(help_text=_("每页数量"), default=100)
    ordering = serializers.ListSerializer(help_text=_("排序字段"), child=serializers.CharField(), required=False)
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))

    class Meta:
        swagger_schema_fields = {
            "example": {
                "bk_biz_id": 3,
                "self_manage": True,
                "self_assist": False,
                "offset": 0,
                "limit": 10,
                "stage": "is_handled",
                "status": "ABNORMAL",
                "start_time": None,
                "end_time": None,
            }
        }


class MetricListSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务id"))
    conditions = serializers.JSONField(help_text=_("查询条件"))


class CreateAlarmShieldSerializer(serializers.Serializer):
    category = serializers.CharField(help_text=_("屏蔽类型"))
    dimension_config = serializers.DictField(help_text=_("屏蔽维度配置"))
    shield_notice = serializers.BooleanField(help_text=_("告警屏蔽通知"), default=False)
    begin_time = serializers.CharField(help_text=_("开始时间"))
    end_time = serializers.CharField(help_text=_("结束时间"))
    description = serializers.CharField(help_text=_("屏蔽原因"))

    def to_internal_value(self, data):
        return data

    def validate(self, attrs):
        # 取维度中的 appid 维度作为业务，这里要求屏蔽策略的维度一定要有业务
        appid = 0
        for condition in attrs["dimension_config"]["dimension_conditions"]:
            if "appid" in condition["key"]:
                appid = condition["value"][0]
        if not appid:
            raise serializers.ValidationError(_("暂不支持屏蔽[不包含业务]维度的告警"))
        attrs["bk_biz_id"] = appid
        return attrs

    class Meta:
        swagger_schema_fields = {"example": mock_data.CREATE_ALARM_SHIELD_FOR_DIMENSION}


class UpdateAlarmShieldSerializer(serializers.Serializer):
    begin_time = serializers.CharField(help_text=_("开始时间"))
    end_time = serializers.CharField(help_text=_("结束时间"))
    description = serializers.CharField(help_text=_("屏蔽原因"))
    cycle_config = serializers.DictField(help_text=_("屏蔽周期"))
    level = serializers.ListField(required=False, label=_("策略的屏蔽等级"))
    shield_notice = serializers.BooleanField(help_text=_("是否有屏蔽通知"), default=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.UPDATE_ALARM_SHIELD}


class DisableAlarmShieldSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("屏蔽 ID"))


class PatchDestroySerializer(serializers.Serializer):
    ids = serializers.ListSerializer(child=serializers.IntegerField(), help_text=_("策略id列表"))


class ListAlarmShieldSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    is_active = serializers.BooleanField(help_text=_("是否生效"), default=True)
    time_range = serializers.CharField(help_text=_("时间范围"), required=False)
    category = serializers.CharField(help_text=_("屏蔽类型"), required=False)
    conditions = serializers.ListSerializer(help_text=_("查询条件"), child=serializers.DictField(), required=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.LIST_ALARM_SHIELD}


class UpdateDutyNoticeSerializer(serializers.Serializer):
    class DutyCrontabSerializer(serializers.Serializer):
        minute = serializers.CharField(help_text=_("分钟"))
        hour = serializers.CharField(help_text=_("小时"))
        day_of_week = serializers.CharField(help_text=_("每周几天(eg: 1,4,5 表示一周的周一，周四，周五)"), required=False)
        day_of_month = serializers.CharField(help_text=_("每月几天(eg: 1, 11, 13 表示每月的1号，11号，13号)"), required=False)

    db_type = serializers.ChoiceField(help_text=_("数据库类型"), choices=DBType.get_choices())
    cron = DutyCrontabSerializer(help_text=_("值班通知周期"))
    after = serializers.IntegerField(help_text=_("通知几天后的排班表"))
    enabled = serializers.BooleanField(help_text=_("是否启用"))
    channels = serializers.JSONField(help_text=_("通知渠道"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.DUTY_NOTICE_RULE_DATA}


class SendDutyNoticeScheduleSerializer(serializers.Serializer):
    db_type = serializers.ChoiceField(help_text=_("数据库类型"), choices=DBType.get_choices())


class SaveMonitorSubscribeSerializer(serializers.Serializer):
    class SubscribeClusterInfo(serializers.Serializer):
        cluster_domain = serializers.CharField(help_text=_("集群域名"))
        cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())

    clusters = serializers.ListField(help_text=_("订阅集群"), child=SubscribeClusterInfo())
    alert_level = serializers.ListField(help_text=_("告警级别"), child=serializers.IntegerField())
    notice_ways = serializers.ListField(
        help_text=_("通知方式"), child=serializers.ChoiceField(choices=MsgType.get_choices())
    )

    def validate(self, attrs):
        cluster_types = {cluster["cluster_type"] for cluster in attrs["clusters"]}
        db_type = [ClusterType.cluster_type_to_db_type(cluster_type) for cluster_type in cluster_types]
        if len(set(db_type)) != 1:
            raise serializers.ValidationError(_("订阅集群组件类型不一致"))
        return attrs


class DeleteMonitorSubscribeSerializer(serializers.Serializer):
    ids = serializers.ListField(help_text=_("订阅ID列表"), child=serializers.IntegerField())

    def validate(self, attrs):
        return attrs


class ListMonitorSubscribeSerializer(serializers.Serializer):
    pass


class SyncCollectStrategySerializer(serializers.Serializer):
    """加载/同步采集策略参数"""

    db_type = serializers.ChoiceField(help_text=_("数据库类型，不传则同步全部类型"), choices=DBType.get_choices(), required=False)
    force = serializers.BooleanField(help_text=_("是否强制执行(采集对象有变更时使用)"), default=False, required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID，不传则使用默认DBA业务"), required=False)


class ListCollectPluginSerializer(serializers.Serializer):
    """查询采集插件列表参数"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID，不传则使用默认DBA业务"), required=False)


class ImportCollectPluginSerializer(serializers.Serializer):
    """导入采集插件参数"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID，不传则使用默认DBA业务"), required=False)
    file = serializers.FileField(help_text=_("插件包文件(.tgz), 以 multipart 方式上传到监控平台"), required=True)
