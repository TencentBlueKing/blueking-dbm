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
from typing import Any, Dict

from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import JobApi
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.jobapi.serializers import (
    FastExecuteScriptResponseSerializer,
    FastExecuteScriptSerializer,
    GetJobInstanceIpLogResponseSerializer,
    GetJobInstanceIpLogSerializer,
    GetJobInstanceStatusResponseSerializer,
    JobInstanceStatusSerializer,
    TransferFileResponseSerializer,
    TransferFileSerializer,
)
from backend.db_proxy.views.views import BaseProxyPassViewSet
from backend.utils.string import base64_encode


class JobApiProxyPassViewSet(BaseProxyPassViewSet):
    """
    Job api接口透传视图
    """

    @common_swagger_auto_schema(
        operation_summary=_("[jobapi]快速执行脚本"),
        request_body=FastExecuteScriptSerializer(),
        responses={status.HTTP_200_OK: FastExecuteScriptResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=FastExecuteScriptSerializer,
        url_path="jobapi/fast_execute_script",
    )
    def fast_execute_script(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        job_payloads: Dict[str, Any] = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": _("DBM 快速脚本执行"),
            "script_content": base64_encode(validated_data["script_content"]),
            "script_language": validated_data["script_language"],
            "target_server": {"ip_list": validated_data["ip_list"]},
            "timeout": validated_data["timeout"],
            "account_alias": validated_data["account"],
            "is_param_sensitive": 0,
        }
        job_result = JobApi.fast_execute_script(job_payloads, use_admin=True)
        return Response(job_result)

    @common_swagger_auto_schema(
        operation_summary=_("[jobapi]查询任务执行状态"),
        request_body=JobInstanceStatusSerializer(),
        responses={status.HTTP_200_OK: GetJobInstanceStatusResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=JobInstanceStatusSerializer,
        url_path="jobapi/get_job_instance_status",
    )
    def get_job_instance_status(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        job_status_payloads: Dict[str, Any] = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": validated_data["job_instance_id"],
            "return_ip_result": True,
        }
        job_status = JobApi.get_job_instance_status(job_status_payloads, use_admin=True)
        return Response(job_status)

    @common_swagger_auto_schema(
        operation_summary=_("[jobapi]查询任务执行日志"),
        request_body=GetJobInstanceIpLogSerializer(),
        responses={status.HTTP_200_OK: GetJobInstanceIpLogResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=GetJobInstanceIpLogSerializer,
        url_path="jobapi/batch_get_job_instance_ip_log",
    )
    def get_job_instance_ip_log(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        job_log_payloads: Dict[str, Any] = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": validated_data["job_instance_id"],
            "step_instance_id": validated_data["step_instance_id"],
            "ip_list": validated_data["ip_list"],
        }
        job_log = JobApi.batch_get_job_instance_ip_log(job_log_payloads, use_admin=True)
        return Response(job_log)

    @common_swagger_auto_schema(
        operation_summary=_("[jobapi]查询任务执行日志"),
        request_body=TransferFileSerializer(),
        responses={status.HTTP_200_OK: TransferFileResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"], detail=False, serializer_class=TransferFileSerializer, url_path="jobapi/fast_transfer_file"
    )
    def transfer_file(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        source_list = []
        for source in validated_data["source_list"]:
            source_list.append(
                {
                    "account": {"alias": source["account"]},
                    "server": {"ip_list": [{"bk_cloud_id": source["bk_cloud_id"], "ip": source["ip"]}]},
                    "file_list": source["file_list"],
                    "file_type": 1,
                }
            )
        transfer_file_payload = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": _("DBM 快速文件分发"),
            "transfer_mode": 2,
            "file_source_list": source_list,
            "file_target_path": validated_data["target_dir"],
            "target_server": {
                "ip_list": [
                    {"bk_cloud_id": item["bk_cloud_id"], "ip": item["ip"]} for item in validated_data["target_ip_list"]
                ]
            },
            "account_alias": validated_data["target_account"],
            "timeout": validated_data["timeout"],
        }
        transfer_file_result = JobApi.fast_transfer_file(transfer_file_payload, raw=True, use_admin=True)
        return Response(transfer_file_result)
