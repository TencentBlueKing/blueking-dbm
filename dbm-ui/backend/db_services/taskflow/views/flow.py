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

from django.http import HttpResponse
from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.db_services.taskflow.serializers import (
    BatchRetryNodesSerializer,
    CallbackNodeSerializer,
    DownloadExcelSerializer,
    FlowTaskSerializer,
    NodeSerializer,
    VersionSerializer,
)
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.taskflow import TaskFlowPermission
from backend.iam_app.handlers.permission import Permission
from backend.ticket.builders.common.base import fetch_host_ids
from backend.ticket.constants import TODO_RUNNING_STATUS, TodoType
from backend.ticket.models import Flow, Todo
from backend.ticket.serializers import TodoSerializer

logger = logging.getLogger("root")
SWAGGER_TAG = "taskflow"


class TaskFlowViewSet(viewsets.AuditedModelViewSet):
    lookup_field = "root_id"
    serializer_class = FlowTaskSerializer
    queryset = FlowTree.objects.all()
    filter_fields = {
        "uid": ["exact"],
        "bk_biz_id": ["exact"],
        "status": ["exact", "in"],
        "ticket_type": ["exact", "in"],
        "created_at": ["gte", "lte"],
        "created_by": ["exact", "in"],
    }

    action_permission_map = {("list",): [DBManagePermission()]}
    default_permission_class = [TaskFlowPermission([ActionEnum.FLOW_DETAIL], ResourceEnum.TASKFLOW)]

    def get_queryset(self):
        if self.action != self.list.__name__:
            return super().get_queryset()

        # 对root_ids支持批量过滤
        root_ids = self.request.query_params.get("root_ids", None)
        if root_ids:
            self.queryset = self.queryset.filter(root_id__in=root_ids.split(","))

        return self.queryset

    @common_swagger_auto_schema(
        operation_summary=_("任务列表"),
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_permission_field(
        id_field=lambda d: d["root_id"],
        data_field=lambda d: d["results"],
        actions=[ActionEnum.FLOW_DETAIL],
        resource_meta=ResourceEnum.TASKFLOW,
    )
    @Permission.decorator_permission_field(
        id_field=lambda d: d["uid"],
        data_field=lambda d: d["results"],
        actions=[ActionEnum.TICKET_VIEW],
        resource_meta=ResourceEnum.TICKET,
    )
    def list(self, requests, *args, **kwargs):
        return super().list(requests, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("任务详情"),
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, requests, *args, **kwargs):
        root_id = kwargs["root_id"]
        tree_states = BambooEngine(root_id=root_id).get_pipeline_tree_states()
        flow_info = super().retrieve(requests, *args, **kwargs).data

        # 补充获取业务和主机信息
        try:
            # 递归遍历字典，获取主机ID
            details = Flow.objects.get(flow_obj_id=root_id).details["ticket_data"]
            bk_biz_id, bk_host_ids = details["bk_biz_id"], fetch_host_ids(details)
            # 如果当前pipeline整在运行中，并且是从资源池拿取的机器，则bk_biz_id设置为DBA_APP_BK_BIZ_ID
            if flow_info["status"] != StateType.FINISHED and details.get("ip_source") == IpSource.RESOURCE_POOL:
                bk_biz_id = env.DBA_APP_BK_BIZ_ID
            flow_info.update(bk_host_ids=bk_host_ids, bk_biz_id=bk_biz_id)
        except Exception as e:
            # 如果没找到flow或者相关bk_host_id参数，则忽略
            logger.info("can not find related host, root_id: {} Exception: {} ".format(root_id, e))

        # 补充获取正在进行的todo
        todo_qs = Todo.objects.filter(
            flow__flow_obj_id=root_id, type=TodoType.INNER_APPROVE, status__in=TODO_RUNNING_STATUS
        )
        todos = TodoSerializer(todo_qs, many=True).data

        return Response({"flow_info": flow_info, "todos": todos, **tree_states})

    @common_swagger_auto_schema(
        operation_summary=_("撤销流程"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True)
    def revoke_pipeline(self, requests, *args, **kwargs):
        root_id = kwargs["root_id"]
        return Response(TaskFlowHandler(root_id=root_id).revoke_pipeline().result)

    @common_swagger_auto_schema(
        operation_summary=_("重试节点"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=NodeSerializer)
    def retry_node(self, requests, *args, **kwargs):
        # 非超级用户，暂不允许调用此接口
        # if not requests.user.is_superuser:
        #     raise RetryNodeException(_("非超级用户，暂不允许调用此接口"))

        root_id = kwargs["root_id"]
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(TaskFlowHandler(root_id=root_id).retry_node(node_id=validated_data["node_id"]).result)

    @common_swagger_auto_schema(
        operation_summary=_("批量重试"),
        request_body=BatchRetryNodesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=BatchRetryNodesSerializer)
    def batch_retry_nodes(self, requests, *args, **kwargs):
        root_id = kwargs["root_id"]
        return Response(TaskFlowHandler(root_id=root_id).batch_retry_nodes())

    @common_swagger_auto_schema(
        operation_summary=_("跳过节点"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=NodeSerializer)
    def skip_node(self, requests, *args, **kwargs):
        root_id = kwargs["root_id"]
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(TaskFlowHandler(root_id=root_id).skip_node(node_id=validated_data["node_id"]).result)

    @common_swagger_auto_schema(
        operation_summary=_("强制失败节点"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=NodeSerializer)
    def force_fail_node(self, requests, *args, **kwargs):
        root_id = kwargs["root_id"]
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(TaskFlowHandler(root_id=root_id).force_fail_node(node_id=validated_data["node_id"]).result)

    @common_swagger_auto_schema(
        operation_summary=_("节点版本列表"),
        query_serializer=NodeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=True, serializer_class=NodeSerializer)
    def node_histories(self, requests, *args, **kwargs):
        root_id = kwargs["root_id"]
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(TaskFlowHandler(root_id=root_id).get_node_histories(node_id=validated_data["node_id"]))

    @common_swagger_auto_schema(
        operation_summary=_("节点日志"),
        query_serializer=VersionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=True, serializer_class=VersionSerializer)
    def node_log(self, requests, *args, **kwargs):
        root_id = kwargs["root_id"]
        validated_data = self.params_validate(self.get_serializer_class())
        node_id = validated_data["node_id"]
        version_id = validated_data["version_id"]
        logs = TaskFlowHandler(root_id=root_id).get_version_logs(node_id, version_id)
        if validated_data["download"]:
            # 导出下载日志
            return HttpResponse(
                logs,
                content_type="application/text charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{root_id}-{node_id}-{version_id}.log"'},
            )
        else:
            return Response(logs)

    @common_swagger_auto_schema(
        operation_summary=_("回调节点"),
        query_serializer=CallbackNodeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=CallbackNodeSerializer)
    def callback_node(self, requests, *args, **kwargs):
        root_id = kwargs["root_id"]

        validated_data = self.params_validate(self.get_serializer_class())
        node_id = validated_data["node_id"]
        desc = {"info": validated_data.get("desc"), "operator": requests.user.username}

        return Response(TaskFlowHandler(root_id=root_id).callback_node(node_id=node_id, desc=desc).result)

    @common_swagger_auto_schema(
        operation_summary=_("流程Excel文件下载"),
        query_serializer=DownloadExcelSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=DownloadExcelSerializer)
    def excel_download(self, request):
        # 获取root_id缓存数据
        validated_data = self.params_validate(self.get_serializer_class())
        results = BaseService().excel_download(**validated_data)
        if not results:
            return Response({"error": _("获取root_id缓存数据失败")})
        # 返回响应
        return results
