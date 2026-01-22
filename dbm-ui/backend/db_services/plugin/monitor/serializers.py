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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class MonitorImageRenderSerializer(serializers.Serializer):
    class OptionsSerializer(serializers.Serializer):
        bk_biz_id = serializers.IntegerField(help_text=_("业务id"))
        dashboard_uid = serializers.CharField(help_text=_("仪表盘uid"))
        panel_id = serializers.CharField(help_text=_("面板id"), required=False)
        height = serializers.IntegerField(help_text=_("高度"), required=False)
        width = serializers.IntegerField(help_text=_("宽度"))
        variables = serializers.JSONField(help_text=_("变量"), required=False)
        start_time = serializers.IntegerField(help_text=_("开始时间"))
        end_time = serializers.IntegerField(help_text=_("结束时间"))
        scale = serializers.IntegerField(help_text=_("密度"), required=False)
        with_panel_title = serializers.BooleanField(help_text=_("是否显示面板标题"), required=False)

        class Meta:
            ref_name = "MonitorImageRenderOptions"

    type = serializers.CharField(help_text=_("任务类型"))
    options = OptionsSerializer(help_text=_("任务参数"))


class MonitorImageResultSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(help_text=_("业务id"))
