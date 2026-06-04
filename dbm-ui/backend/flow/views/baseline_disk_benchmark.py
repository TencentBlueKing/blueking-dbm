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
import logging
import os

from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from backend.flow.engine.controller.dbm_aiagent import DbmAiAgentController
from backend.flow.views.base import FlowTestView
from backend.ticket.constants import TicketType
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")

# target 路径白名单, 必须以这些前缀之一开头, 与 actuator 端 allowedTargetPrefixes 保持一致
# 详见 dbm-services/mysql/db-tools/dbactuator/pkg/components/oscomp/disk_benchmark.go
ALLOWED_TARGET_PREFIXES = ("/data/", "/data1/", "/tmp/", "/var/tmp/")


class _DiskItemSerializer(serializers.Serializer):
    target = serializers.CharField(help_text=_("测试目标文件绝对路径 (必须落在 /data/ /tmp/ /var/tmp/ 之一下)"))
    disk_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
        help_text=_(
            "BaselineDisk 唯一键；约定为 disk_type 与 capacity_gb 下划线拼接。target 在 /dataN 下时可省略,"
            "由流程按 CVM+Job 合并结果回填 disk_type/capacity_gb 后自动生成"
        ),
    )
    test_file_size = serializers.CharField(
        required=False, default="8G", help_text=_("fio 压测时写入的测试文件大小(非磁盘容量), 如 8G、4G; 默认 8G")
    )
    disk_type = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text=_("磁盘类型；target 在 /dataN 下时可省略, 由合并结果(CVM 云盘类型/IT 本地盘)兜底"),
    )
    disk_model = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_local = serializers.BooleanField(
        required=False, allow_null=True, default=None, help_text=_("是否本地盘；默认 False, IT 开头机型由合并结果置 True")
    )
    capacity_gb = serializers.IntegerField(required=False, allow_null=True, default=None)
    runtime = serializers.IntegerField(required=False, default=None, allow_null=True)
    jobs = serializers.IntegerField(required=False, default=None, allow_null=True)
    throughput_jobs = serializers.IntegerField(required=False, default=None, allow_null=True)

    def validate_target(self, value):
        if not value.startswith("/"):
            raise ValidationError(_("target 必须是绝对路径"))
        if value.startswith("/dev/"):
            raise ValidationError(_("拒绝执行: target 不允许指向 /dev/ 设备节点 ({})").format(value))
        # 规范化, 防 /data/../etc/passwd 这种 ../ 注入
        cleaned = os.path.normpath(value)
        if not cleaned.startswith(ALLOWED_TARGET_PREFIXES):
            raise ValidationError(
                _("拒绝执行: target 必须落在白名单目录 {} 下, got {} (规范化后 {}). 仅允许在数据盘/临时目录上做压测").format(
                    list(ALLOWED_TARGET_PREFIXES), value, cleaned
                )
            )
        return cleaned


class _HostItemSerializer(serializers.Serializer):
    ip = serializers.IPAddressField(help_text=_("主机 IP"))
    bk_cloud_id = serializers.IntegerField(required=False, default=0)
    disks = _DiskItemSerializer(many=True, allow_empty=False)


class BaselineDiskBenchmarkSerializer(serializers.Serializer):
    """flow 入参 Serializer, 仅做基础结构校验; 业务级校验放在 Flow.run_flow 内"""

    bk_biz_id = serializers.IntegerField(required=False, default=None)
    bk_cloud_id = serializers.IntegerField(required=False, default=0)
    strict_idle_check = serializers.BooleanField(required=False, default=False)
    runtime = serializers.IntegerField(required=False, default=30)
    jobs = serializers.IntegerField(required=False, default=64)
    throughput_jobs = serializers.IntegerField(required=False, default=16)
    hosts = _HostItemSerializer(many=True, allow_empty=False)


class BaselineDiskBenchmarkSceneApiView(FlowTestView):
    """
    BaselineDisk 性能基线采集 (管理员 API)

    权限: 限超管或 DEBUG 模式 (继承自 FlowTestView)

    入参说明: target 在 /dataN 且提供 disk_type 时, disk_name、capacity_gb 可省略, 由 BaselineDiskBenchmarkFlow
    在 run_flow 内合并 CVM+Job 后回填并生成 disk_name；其它路径须自带 disk_name。

    入参示例:
    {
        "bk_biz_id": 100100,
        "bk_cloud_id": 0,
        "strict_idle_check": false,
        "runtime": 30,
        "hosts": [
            {
                "ip": "127.0.0.1",
                "bk_cloud_id": 0,
                "disks": [
                    {
                        "target": "/data/baseline_bench/fio.bin",
                        "test_file_size": "8G"
                    }
                ]
            }
        ]
    }

    返回: {"root_id": "<生成的流程 id>"}
    """

    def post(self, request):
        # 注意: ENABLE_DBM_AI 关闭时仍允许跑 flow, 仅跳过最后写库节点 (在 disk_benchmark_flow 内做 graceful skip)。
        # 这种 ad-hoc 模式下结果只在 dbactuator 节点 stdout 的 <ctx>...</ctx> 里可见, 不入 BaselineDisk 表。
        # 长期基线采集仍需开 ENABLE_DBM_AI
        serializer = BaselineDiskBenchmarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket_data = dict(serializer.validated_data)

        # 注入 FlowTree 必需字段, 用户无需在 payload 里填
        ticket_data["ticket_type"] = TicketType.RESOURCE_OS_DISK_BENCHMARK.value
        ticket_data["created_by"] = request.user.username or "admin"
        ticket_data.setdefault("uid", "")

        root_id = generate_root_id()
        DbmAiAgentController(root_id=root_id, ticket_data=ticket_data).disk_benchmark_flow()
        return Response({"root_id": root_id})
