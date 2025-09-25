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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_services.risk_memo.constants import RiskOpType, Status
from backend.db_services.risk_memo.models.risk_memo import RiskMemo, RiskMemoFollowUp, RiskOperateRecord


class RiskMemoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskMemo
        fields = [
            "id",
            "name",
            "bk_biz_id",
            "level",
            "status",
            "db_type",
            "description",
            "biz_inpact",
            "inpact_cluster",
            "is_special",
            "duration_time",
        ]
        read_only_fields = model.AUDITED_FIELDS

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["biz_inpact"] = representation["biz_inpact"].split(",")
        representation["inpact_cluster"] = representation["inpact_cluster"].split(",")
        return representation


class RiskMemoDtailSerializer(serializers.ModelSerializer):
    follow_ups = serializers.SerializerMethodField()

    class Meta:
        model = RiskMemo
        fields = "__all__"

    def get_follow_ups(self, obj):
        follow_ups = obj.riskmemofollowup_set.all().order_by("-create_at")

        return RiskMemoFollowUpSerializer(follow_ups, many=True, context=self.context).data


class RiskMemoFollowUpSerializer(serializers.ModelSerializer):
    is_follow_up_owner = serializers.SerializerMethodField(help_text=_("是否跟进创建者"))

    class Meta:
        model = RiskMemoFollowUp
        fields = "__all__"
        read_only_fields = model.AUDITED_FIELDS + ("is_follow_up_owner",)

    def get_is_follow_up_owner(self, obj):
        """根据跟进类型调用相应管理器方法返回是否创建者。"""
        request = self.context["request"]
        return RiskMemoFollowUp.objects.get_is_follow_up_owner(request, obj)


class UpdateRiskMemoFollowUpSerializer(serializers.ModelSerializer):
    """修改跟进序列化器"""

    class Meta:
        model = RiskMemoFollowUp
        fields = "__all__"
        read_only_fields = model.AUDITED_FIELDS

    def validate(self, attrs):
        # 从上下文中获取request对象
        request = self.context.get("request")

        if attrs["risk"].status != Status.DOING.value:
            raise serializers.ValidationError(_("状态非[进行中]时，不支持修改跟进。"))
        if not request.user.is_superuser or self.instance.creator != request.user.username:
            raise serializers.ValidationError(_("暂不支持修改跟进。"))
        return attrs


class DeleteFollowUpSerializer(serializers.ModelSerializer):
    """删除跟进序列化器"""

    class Meta:
        model = RiskMemoFollowUp
        fields = ("risk",)

    def validate(self, attrs):
        # 从上下文中获取request对象
        request = self.context.get("request")
        if not request.user.is_superuser or self.instance.creator != request.user.username:
            raise serializers.ValidationError(_("暂不支持删除跟进。"))
        return attrs


class UpdateRiskStatusSerializer(serializers.ModelSerializer):
    """更新风险状态序列化器"""

    final_content = serializers.CharField(required=False, help_text=_("结项内容"))

    class Meta:
        model = RiskMemo
        fields = ["status", "final_content"]


class RiskOpSerializer(serializers.ModelSerializer):
    oper_type_value = serializers.SerializerMethodField(help_text=_("操作类型"))

    class Meta:
        model = RiskOperateRecord
        fields = "__all__"

    def get_oper_type_value(self, obj):
        return RiskOpType.get_choice_label(obj.oper_type)
