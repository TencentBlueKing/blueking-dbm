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
import base64
import json
import re

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from rest_framework import serializers

from backend import env
from backend.components import JobApi
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler
from backend.ticket.models import Flow

cpl = re.compile("<ctx>(?P<context>.+?)</ctx>")


class MongoBackupFileSerializer(BaseFlowOutputSerializer):
    """MongoDB 备份成功后的备份文件交付产物"""

    table_name = "mongo_backup_files"
    table_display_name = _("备份文件")
    table_primary_key = "bs_taskid"

    cluster_domain = serializers.CharField(help_text=_("集群域名"), allow_blank=True, default="")
    set_name = serializers.CharField(help_text=_("分片名"), allow_blank=True, default="")
    instance = serializers.CharField(help_text=_("实例"))
    file_name = serializers.CharField(help_text=_("文件名"))
    file_size = serializers.IntegerField(help_text=_("文件大小(字节)"), required=False, default=0)
    file_path = serializers.CharField(help_text=_("文件路径"), allow_blank=True, default="", required=False)
    bs_taskid = serializers.CharField(help_text=_("备份系统任务ID"))


class MongoBackupExecService(ExecJobComponent2.bound_service):
    """
    MongoDB 备份专用 Job 执行组件：在备份作业成功后解析 actuator <ctx>，
    将备份文件信息写入 FlowSummary（单据「交付结果」）。
    """

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        result = super()._schedule(data, parent_data, callback_data)
        if not result:
            return False
        # 仅在 Job 最终成功时写入；轮询中未结束时 job_execute 尚未置 True
        # 已写入则跳过，避免轮询期间重复拉 Job 日志
        if data.get_one_of_outputs("job_execute") is True and not data.get_one_of_outputs(
            "backup_flow_output_written"
        ):
            self._write_backup_flow_output(data)
            data.outputs.backup_flow_output_written = True
        return True

    def _write_backup_flow_output(self, data) -> None:
        root_id = self.runtime_attrs.get("root_pipeline_id")
        if not root_id or not Flow.objects.filter(flow_obj_id=root_id).exists():
            self.log_info(_("当前流程[{}]未关联单据Flow记录，跳过写入备份交付产物").format(root_id))
            return

        try:
            row = self._parse_backup_ctx_from_job(data)
        except Exception as e:
            self.log_warning(_("解析备份交付产物失败，不影响备份成功: {}").format(e))
            return

        if not row:
            self.log_warning(_("未从作业日志解析到备份文件信息，跳过写入交付产物"))
            return

        try:
            FlowOutputHandler(MongoBackupFileSerializer).insert_data(root_id, row)
            self.log_info(_("备份文件已写入交付产物: {}").format(row.get("file_name")))
        except Exception as e:
            self.log_warning(_("写入备份交付产物失败，不影响备份成功: {}").format(e))

    def _parse_backup_ctx_from_job(self, data) -> dict:
        kwargs = data.get_one_of_inputs("kwargs")
        ext_result = data.get_one_of_outputs("ext_result")
        exec_ips = data.get_one_of_outputs("exec_ips") or []
        if not isinstance(ext_result, dict) or not ext_result.get("data"):
            return {}

        job_instance_id = ext_result["data"]["job_instance_id"]
        status_resp = JobApi.get_job_instance_status(
            {
                "bk_scope_type": "biz_set",
                "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
                "job_instance_id": job_instance_id,
                "return_ip_result": True,
            },
            raw=True,
        )
        if not status_resp.get("result"):
            return {}
        step_list = status_resp.get("data", {}).get("step_instance_list") or []
        if not step_list:
            return {}
        step_instance_id = step_list[0]["step_instance_id"]

        ip = exec_ips[0] if exec_ips else kwargs.get("exec_ip")
        if isinstance(ip, dict):
            ip_dict = ip
        else:
            ip_dict = {"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip}

        log_resp = JobApi.get_job_instance_ip_log(
            {
                "bk_scope_type": "biz_set",
                "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
                "job_instance_id": job_instance_id,
                "step_instance_id": step_instance_id,
                **ip_dict,
            },
            raw=True,
        )
        if not log_resp.get("result"):
            return {}

        log_content = log_resp["data"].get("log_content") or ""
        match = cpl.search(log_content)
        if not match:
            return {}

        ctx_raw = match.group("context")
        try:
            decoded = base64.b64decode(ctx_raw).decode("utf-8")
            ctx = json.loads(decoded)
        except Exception:
            # 兼容非 base64 的原始 JSON
            ctx = json.loads(ctx_raw)

        if not isinstance(ctx, dict):
            return {}

        bs_taskid = str(ctx.get("bs_taskid") or "")
        file_name = ctx.get("file_name") or ""
        if not bs_taskid or not file_name:
            return {}

        return {
            "cluster_domain": ctx.get("cluster_domain") or "",
            "set_name": ctx.get("set_name") or "",
            "instance": ctx.get("instance") or "",
            "file_name": file_name,
            "file_size": int(ctx.get("file_size") or 0),
            "file_path": ctx.get("file_path") or "",
            "bs_taskid": bs_taskid,
        }


class MongoBackupExecJobComponent(Component):
    name = _("MongoDB备份")
    code = "MongoBackupExecJobComponent"
    bound_service = MongoBackupExecService
