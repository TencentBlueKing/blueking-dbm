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

import datetime
import itertools
import time
import uuid

from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.models import AppCache
from backend.db_services.dbresource.constants import (
    RESOURCE_IMPORT_EXPIRE_TIME,
    RESOURCE_IMPORT_TASK_FIELD,
    SWAGGER_TAG,
)
from backend.db_services.dbresource.serializers import (
    ListDBAHostsSerializer,
    ListSubzonesSerializer,
    ResourceApplySerializer,
    ResourceConfirmSerializer,
    ResourceDeleteSerializer,
    ResourceImportResponseSerializer,
    ResourceImportSerializer,
    ResourceListResponseSerializer,
    ResourceListSerializer,
    ResourceUpdateSerializer,
)
from backend.db_services.ipchooser.constants import ModeType
from backend.db_services.ipchooser.handlers.topo_handler import TopoHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.consts import FAILED_STATES, SUCCEED_STATES
from backend.flow.engine.controller.base import BaseController
from backend.flow.models import FlowTree
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission
from backend.ticket.constants import TicketType
from backend.utils.redis import RedisConn


class DBResourceViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("资源池资源列表"),
        request_body=ResourceListSerializer(),
        responses={status.HTTP_200_OK: ResourceListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="list", serializer_class=ResourceListSerializer)
    def resource_list(self, request):
        resource_data = DBResourceApi.resource_list(params=self.params_validate(self.get_serializer_class()))
        if not resource_data["details"]:
            return Response({"count": 0, "results": []})

        # 格式化资源列表信息，填充必要参数
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        for_biz_ids = list(set(itertools.chain(*[data["for_bizs"] for data in resource_data["details"]])))
        for_biz_ids = list(map(int, for_biz_ids))
        for_biz_infos = AppCache.batch_get_app_attr(bk_biz_ids=for_biz_ids, attr_name="bk_biz_name")
        for data in resource_data.get("details") or []:
            data.update(
                {
                    "bk_cloud_name": cloud_info[str(data["bk_cloud_id"])]["bk_cloud_name"],
                    "bk_host_innerip": data["ip"],
                    "bk_mem": data.pop("dram_cap") // 1024,
                    "bk_cpu": data.pop("cpu_num"),
                    "bk_disk": data.pop("total_storage_cap"),
                    "resource_types": data.pop("resource_types"),
                    "for_bizs": [
                        {"bk_biz_id": int(bk_biz_id), "bk_biz_name": for_biz_infos[int(bk_biz_id)]}
                        for bk_biz_id in data.pop("for_bizs")
                    ],
                }
            )

        # 填充agent信息
        resource_data["results"] = resource_data.pop("details")
        ResourceQueryHelper.fill_agent_status(resource_data["results"], fill_key="agent_status")

        return Response(resource_data)

    @common_swagger_auto_schema(
        operation_summary=_("获取DBA业务下的主机信息"),
        query_serializer=ListDBAHostsSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], url_path="list_dba_hosts", serializer_class=ListDBAHostsSerializer)
    def list_dba_hosts(self, request):
        params = self.params_validate(self.get_serializer_class())

        # 查询DBA空闲机模块的meta，构造查询空闲机参数的node_list
        scope_list = [{"scope_id": env.DBA_APP_BK_BIZ_ID, "scope_type": "biz", "bk_biz_id": env.DBA_APP_BK_BIZ_ID}]
        trees = TopoHandler.trees(all_scope=True, mode=ModeType.IDLE_ONLY.value, scope_list=scope_list)
        node_list = [{"instance_id": trees[0]["instance_id"], "meta": trees[0]["meta"], "object_id": "module"}]
        params.update(readable_node_list=node_list)

        # 查询DBA业务下的空闲机
        return Response(TopoHandler.query_hosts_in_batch(params))

    @common_swagger_auto_schema(
        operation_summary=_("资源导入"),
        request_body=ResourceImportSerializer(),
        responses={status.HTTP_200_OK: ResourceImportResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="import", serializer_class=ResourceImportSerializer)
    def resource_import(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        root_id = f"{datetime.date.today()}{uuid.uuid1().hex[:6]}".replace("-", "")

        # 补充必要的单据参数
        validated_data.update(
            ticket_type=TicketType.RESOURCE_IMPORT,
            created_by=request.user.username,
            uid=None,
            # 额外补充资源池导入的参数，用于记录操作日志
            bill_id=None,
            task_id=root_id,
            operator=request.user.username,
        )

        # 执行资源导入的后台flow
        BaseController(root_id=root_id, ticket_data=validated_data).import_resource_init_step()

        # 缓存当前任务，并删除过期导入任务
        now = int(time.time())
        cache_key = RESOURCE_IMPORT_TASK_FIELD.format(user=request.user.username)
        RedisConn.zadd(cache_key, {root_id: now})
        expired_tasks = RedisConn.zrangebyscore(cache_key, "-inf", now - RESOURCE_IMPORT_EXPIRE_TIME)
        if expired_tasks:
            RedisConn.zrem(cache_key, *expired_tasks)

        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("查询资源导入任务"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], url_path="query_import_tasks")
    def query_resource_import_tasks(self, request):
        cache_key = RESOURCE_IMPORT_TASK_FIELD.format(user=request.user.username)
        task_ids = RedisConn.zrange(cache_key, 0, -1)

        # 查询正在进行的task和已经结束的task
        flow_tree_list = FlowTree.objects.filter(root_id__in=task_ids)
        done_tasks, processing_tasks = [], []
        for tree in flow_tree_list:
            if tree.status in SUCCEED_STATES:
                # TODO: tree.status in FAILED_STATES
                done_tasks.append(tree.root_id)
            else:
                processing_tasks.append(tree.root_id)

        # 移除已经结束的task
        if done_tasks:
            RedisConn.zrem(cache_key, *done_tasks)

        return Response(processing_tasks)

    @common_swagger_auto_schema(
        operation_summary=_("资源申请"),
        request_body=ResourceApplySerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="apply", serializer_class=ResourceApplySerializer)
    def resource_apply(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBResourceApi.resource_apply(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取挂载点"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def get_mountpoints(self, request):
        return Response(DBResourceApi.get_mountpoints())

    @common_swagger_auto_schema(
        operation_summary=_("获取磁盘类型"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def get_disktypes(self, request):
        return Response(DBResourceApi.get_disktypes())

    @common_swagger_auto_schema(
        operation_summary=_("根据逻辑城市查询园区"),
        query_serializer=ListSubzonesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], serializer_class=ListSubzonesSerializer)
    def get_subzones(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBResourceApi.get_subzones(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取机型列表"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def get_device_class(self, request):
        return Response(DBResourceApi.get_device_class())

    @common_swagger_auto_schema(
        operation_summary=_("资源预申请"),
        request_body=ResourceApplySerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="pre_apply", serializer_class=ResourceApplySerializer)
    def resource_pre_apply(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        resp = DBResourceApi.resource_pre_apply(params=validated_data, raw=True)
        resp["resource_request_id"] = resp["request_id"]
        return Response(resp)

    @common_swagger_auto_schema(
        operation_summary=_("资源确认"),
        request_body=ResourceConfirmSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="confirm", serializer_class=ResourceConfirmSerializer)
    def resource_confirm(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBResourceApi.resource_confirm(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("资源删除"),
        request_body=ResourceDeleteSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="delete", serializer_class=ResourceDeleteSerializer)
    def resource_delete(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBResourceApi.resource_delete(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("资源更新"),
        request_body=ResourceUpdateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="update", serializer_class=ResourceUpdateSerializer)
    def resource_update(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBResourceApi.resource_update(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取资源导入相关链接"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], url_path="resource_import_urls")
    def resource_import_urls(self, request):
        return Response(
            {"bk_cmdb_url": env.BK_CMDB_URL, "bk_nodeman_url": env.BK_NODEMAN_URL, "bk_scr_url": env.BK_SCR_URL}
        )
