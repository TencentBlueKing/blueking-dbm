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
import os

import humanize
from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.core.storages.storage import get_storage
from backend.db_meta.models import Cluster
from backend.db_services.taskflow.serializers import BatchDownloadSerializer, DirDownloadSerializer, FlowTaskSerializer
from backend.flow.models import FlowTree
from backend.ticket.builders.redis.redis_key_extract import KEY_FILE_PREFIX
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str

SWAGGER_TAG = "taskflow"


class BinaryFileRenderer(BaseRenderer):
    media_type = "application/octet-stream"
    format = None
    charset = None
    render_style = "binary"

    def render(self, data, media_type=None, renderer_context=None):
        return data


class KeyOpsViewSet(viewsets.ReadOnlyAuditedModelViewSet):
    """key相关操作视图"""

    lookup_field = "root_id"
    serializer_class = FlowTaskSerializer
    queryset = FlowTree.objects.all()

    @common_swagger_auto_schema(
        operation_summary=_("结果文件列表"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=True)
    def key_files(self, requests, *args, **kwargs):
        """key提取结果文件列表"""

        flow_tree = self.get_object()
        ticket = Ticket.objects.get(id=flow_tree.uid)
        storage = get_storage()

        task_files = []
        for rule in ticket.details["rules"]:
            # key文件名格式要求：{project}/{bucket}/{rule['path']}/biz.ip.keys.x
            biz_domain_name = f'{ticket.id}.{rule["domain"]}'
            # 兼容集群被删除的极端情况
            cluster = Cluster.objects.filter(pk=rule["cluster_id"]).last()
            path = os.path.join(KEY_FILE_PREFIX, biz_domain_name)
            _, files = storage.listdir(path)
            total_size = sum(f["size"] for f in files)
            task_files.append(
                {
                    "name": biz_domain_name,
                    "cluster_id": getattr(cluster, "id", ""),
                    "cluster_alias": getattr(cluster, "alias", ""),
                    "size_display": humanize.naturalsize(total_size),
                    "size": total_size,
                    "domain": rule["domain"],
                    "path": path,
                    "created_time": datetime2str(ticket.create_at),
                    "files": [
                        {
                            "size": f["size"],
                            "name": f["name"],
                            "md5": f["md5"],
                            "full_path": f["fullPath"],
                            "created_time": f["createdDate"],
                        }
                        for f in files
                    ],
                }
            )
        return Response(task_files)

    @common_swagger_auto_schema(
        operation_summary=_("打包下载结果文件列表"),
        request_body=BatchDownloadSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=BatchDownloadSerializer,
        renderer_classes=(BinaryFileRenderer,),
    )
    def download_key_files(self, requests, *args, **kwargs):
        """
        key提取结果文件列表
        考虑到文件列表参数比较长，暂定post请求
        """

        validated_data = self.params_validate(self.get_serializer_class())

        storage = get_storage()
        resp = storage.batch_download(validated_data["full_paths"])

        return Response(
            resp.iter_content(),
            headers={"Content-Disposition": 'attachment; filename="abc.tar.gz"'},
            content_type="application/octet‑stream",
        )

    @common_swagger_auto_schema(
        operation_summary=_("指定目录下载（返回下载链接）"),
        request_body=DirDownloadSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DirDownloadSerializer,
        pagination_class=None,
    )
    def download_dirs(self, requests, *args, **kwargs):
        """
        指定目录下载
        """

        validated_data = self.params_validate(self.get_serializer_class())

        storage = get_storage()

        return Response({path: storage.url(path) for path in validated_data["paths"]})
