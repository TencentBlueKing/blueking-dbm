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

from backend import env
from backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.enums import (
    BkJobHostErrorCode,
    BkJobInstanceStatus,
    BkJobStepStatus,
)


class QueryResultInputSerializer(serializers.Serializer):
    bk_scope_type = serializers.ChoiceField(
        choices=[("biz", _("业务"))],
        help_text=_("资源范围类型，biz 表示单业务"),
        required=False,
        default="biz",
    )
    bk_scope_id = serializers.IntegerField(
        help_text=_("CMDB 业务ID（注意非 DBM 平台内部业务ID）"), required=False, default=env.JOB_BLUEKING_BIZ_ID
    )
    job_instance_id = serializers.IntegerField(help_text=_("作业实例 ID"))


class HostResultSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("主机 IP"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    bk_host_id = serializers.IntegerField(help_text=_("主机 ID"))
    status = serializers.ChoiceField(
        choices=BkJobStepStatus.get_choices(),
        help_text=_("步骤 IP 执行状态"),
    )
    exit_code = serializers.IntegerField(help_text=_("脚本退出码"), allow_null=True)
    error_code = serializers.ChoiceField(
        choices=BkJobHostErrorCode.get_choices(),
        help_text=_("主机任务错误码"),
    )
    log_content = serializers.CharField(help_text=_("脚本执行日志"), allow_blank=True)


class QueryResultOutputSerializer(serializers.Serializer):
    job_finished = serializers.BooleanField(help_text=_("作业是否完成"))
    job_status = serializers.ChoiceField(
        choices=BkJobInstanceStatus.get_choices(),
        help_text=_("作业状态"),
    )
    step_instance_id = serializers.IntegerField(help_text=_("步骤实例 ID"), allow_null=True)
    host_results = serializers.ListField(child=HostResultSerializer(), help_text=_("各主机的执行结果"))
