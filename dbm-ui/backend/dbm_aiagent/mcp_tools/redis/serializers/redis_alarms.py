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


class RedisClusertAlarmInputSerializer(serializers.Serializer):
    """redis集群级别告警查询"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))

    def validate(self, attrs):
        """验证时间参数"""
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("开始时间必须小于结束时间"))
        return attrs


class RedisAppAlarmInputSerializer(serializers.Serializer):
    """redis业务级别告警查询"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))

    def validate(self, attrs):
        """验证时间参数"""
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("开始时间必须小于结束时间"))
        return attrs


class RedisAlarmItemSerializer(serializers.Serializer):
    """Redis告警项序列化器"""

    alert_name = serializers.CharField(help_text=_("告警名称"), required=True)
    description = serializers.CharField(help_text=_("告警描述"), required=True)
    begin_time = serializers.IntegerField(help_text=_("告警开始时间(Unix时间戳)"), required=True)
    target_key = serializers.CharField(help_text=_("告警目标"), required=False, allow_blank=True, default="")
    cluster_type = serializers.CharField(help_text=_("集群类型"), required=False, allow_blank=True)
    instance_role = serializers.CharField(help_text=_("实例角色"), required=True)
    app = serializers.CharField(help_text=_("应用名称"), required=True)
    bk_target_cloud_id = serializers.CharField(help_text=_("云区域ID"), required=False, allow_blank=True, default="0")


class RedisAlarmItemNamesSerializer(serializers.Serializer):
    """Redis告警项序列化器"""

    alert_name = serializers.CharField(help_text=_("告警名称"))
    alert_detail = RedisAlarmItemSerializer(many=True, help_text=_("告警列表"))


class RedisClusertAlarmOutputSerializer(serializers.Serializer):
    """redis集群级别告警输出结果"""

    total_alarms = serializers.IntegerField(help_text=_("总告警数"))
    alarm_detail = RedisAlarmItemNamesSerializer(many=True, help_text=_("告警列表"))


class RedisAppAlarmOutputSerializer(serializers.Serializer):
    """redis集群级别告警输出结果"""

    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alarm_detail = RedisAlarmItemNamesSerializer(many=True, help_text=_("告警列表"))


class RedisAlertNameAlarmInputSerializer(serializers.Serializer):
    """按告警名称跨业务查询输入"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    alert_name = serializers.CharField(
        help_text=_(
            "告警名称。支持三种匹配方式："
            "1) 关键词(默认模糊)：输入 '主机内存使用率' 会匹配所有包含该关键词的告警，"
            "例如 'Redis(TendisPlus)主机内存使用率'、'xxx主机内存使用率-子告警' 等；"
            "2) 通配符：直接输入 '*主机内存使用率*' 或 'Redis*内存*' 按用户模式匹配；"
            "3) 精确匹配：需将 fuzzy 参数设为 false，按完整告警名精确匹配"
        )
    )
    fuzzy = serializers.BooleanField(
        help_text=_("是否模糊匹配(包含匹配)，默认 True；若 alert_name 已包含 * / ? 则忽略此参数"),
        required=False,
        default=True,
    )

    def validate(self, attrs):
        """验证时间参数"""
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("开始时间必须小于结束时间"))
        return attrs


class RedisAlertNameAlarmOutputSerializer(serializers.Serializer):
    """按告警名称查询的输出结果"""

    query_name = serializers.CharField(help_text=_("用户传入的查询关键词/模式"))
    match_mode = serializers.CharField(help_text=_("实际匹配模式：fuzzy / wildcard / exact"))
    total_alarms = serializers.IntegerField(help_text=_("总告警数"))
    alarm_list = RedisAlarmItemSerializer(many=True, help_text=_("告警明细列表"))
