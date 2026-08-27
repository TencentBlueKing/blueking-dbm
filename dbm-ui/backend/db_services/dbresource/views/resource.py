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
from typing import Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.dbresource.client import DBResourceApi
from backend.components.hcm.client import HCMApi
from backend.components.xwork.client import XworkApi
from backend.db_dirty.models import MachineEvent
from backend.db_meta.models import AppCache
from backend.db_services.dbresource.constants import RESOURCE_IMPORT_TASK_FIELD, SWAGGER_TAG
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.db_services.dbresource.serializers import (  # CheckFaultHostsSerializer,
    AppendHostLabelSerializer,
    CalcResourceWaterLevelSerializer,
    CheckFaultHostsSerializer,
    GetDiskTypeResponseSerializer,
    GetMountPointResponseSerializer,
    ListDBAHostsSerializer,
    ListSubzonesSerializer,
    QueryDBAHostsSerializer,
    QueryOperationListSerializer,
    ResourceApplySerializer,
    ResourceConfirmSerializer,
    ResourceDeleteSerializer,
    ResourceImportResponseSerializer,
    ResourceImportSerializer,
    ResourceListResponseSerializer,
    ResourceListSerializer,
    ResourceSummaryResponseSerializer,
    ResourceSummarySerializer,
    ResourceUpdateSerializer,
    SameSvrOwnerIpsSerializer,
    SpecCostEstimateSerializer,
    SpecCountResourceResponseSerializer,
    SpecCountResourceSerializer,
)
from backend.db_services.ipchooser.constants import BkOsType
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.db_services.ipchooser.types import ScopeList
from backend.flow.consts import FAILED_STATES, SUCCEED_STATES
from backend.flow.models import FlowTree
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.iam_app.handlers.permission import Permission
from backend.ticket.constants import BAMBOO_STATE__TICKET_STATE_MAP, TicketStatus, TicketType
from backend.ticket.models import Ticket
from backend.utils.redis import RedisConn


class DBResourceViewSet(viewsets.SystemViewSet):
    action_permission_map = {
        (
            "resource_import",
            "resource_apply",
            "resource_pre_apply",
            "resource_confirm",
            "resource_delete",
            "resource_update",
            "resource_export",
            "resource_osname",
            "append_labels",
        ): [ResourceActionPermission([ActionEnum.RESOURCE_POLL_MANAGE])],
        (
            "spec_resource_count",
            "spec_cost_estimate",
            "get_mountpoints",
            "get_disktypes",
            "get_subzones",
            "get_device_class",
            "list_dba_hosts",
            "resource_list",
            "query_dba_hosts",
            "resource_import_urls",
            "get_os_types",
            "check_fault_hosts",
            "same_svr_owner_ips",
        ): [],
    }
    default_permission_class = [ResourceActionPermission([ActionEnum.RESOURCE_MANAGE])]
    filter_class = None
    pagination_class = None

    @common_swagger_auto_schema(
        operation_summary=_("资源池资源列表"),
        request_body=ResourceListSerializer(),
        responses={status.HTTP_200_OK: ResourceListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="list", serializer_class=ResourceListSerializer)
    @Permission.decorator_external_permission_field(
        param_field=lambda d: None,
        actions=[ActionEnum.RESOURCE_POLL_MANAGE],
        resource_meta=None,
    )
    def resource_list(self, request):
        params = self.params_validate(self.get_serializer_class())
        return Response(ResourceHandler.resource_list(params))

    @common_swagger_auto_schema(
        operation_summary=_("查询同母机 IP"),
        request_body=SameSvrOwnerIpsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="same_svr_owner_ips",
        serializer_class=SameSvrOwnerIpsSerializer,
    )
    def same_svr_owner_ips(self, request):
        params = self.params_validate(self.get_serializer_class())
        return Response(DBResourceApi.same_svr_owner_ips(params=params))

    @common_swagger_auto_schema(
        operation_summary=_("获取DBA业务下的主机信息"),
        query_serializer=ListDBAHostsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], url_path="list_dba_hosts", serializer_class=ListDBAHostsSerializer)
    def list_dba_hosts(self, request):
        params = self.params_validate(self.get_serializer_class())
        bk_biz_id = params.pop("bk_biz_id")

        # 查询DBA空闲机模块的meta，构造查询空闲机参数的node_list
        host_infos = ResourceHandler.list_dba_hosts(params, bk_biz_id)

        return Response(host_infos)

    @common_swagger_auto_schema(
        operation_summary=_("资源池操作系统列表"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"])
    def resource_osname(self, request):
        data = {}
        os_names = DBResourceApi.resource_osname()
        if os_names:
            bk_os_names = [{"value": os_name, "text": os_name} for os_name in os_names]
            data["os_names"] = bk_os_names

        return Response(data=data)

    @common_swagger_auto_schema(
        operation_summary=_("查询DBA业务下的主机信息"),
        query_serializer=QueryDBAHostsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], url_path="query_dba_hosts", serializer_class=QueryDBAHostsSerializer)
    def query_dba_hosts(self, request):
        host_ids = self.params_validate(self.get_serializer_class())["bk_host_ids"].split(",")
        host_list = [{"host_id": int(host_id)} for host_id in host_ids]
        scope_list: ScopeList = [{"bk_biz_id": env.DBA_APP_BK_BIZ_ID}]
        return Response(HostHandler.details(scope_list=scope_list, host_list=host_list))

    @common_swagger_auto_schema(
        operation_summary=_("资源导入"),
        request_body=ResourceImportSerializer(),
        responses={status.HTTP_200_OK: ResourceImportResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="import", serializer_class=ResourceImportSerializer)
    def resource_import(self, request):
        data = self.params_validate(self.get_serializer_class())
        return Response({"ticket_ids": ResourceHandler.resource_import(data, request.user.username)})

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
            if tree.status in [*FAILED_STATES, *SUCCEED_STATES]:
                done_tasks.append(tree.root_id)
            else:
                processing_tasks.append(tree.root_id)

        # 移除已经结束的task
        if done_tasks:
            RedisConn.zrem(cache_key, *done_tasks)

        return Response({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "task_ids": processing_tasks})

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
        responses={status.HTTP_200_OK: GetMountPointResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def get_mountpoints(self, request):
        return Response(DBResourceApi.get_mountpoints())

    @common_swagger_auto_schema(
        operation_summary=_("获取磁盘类型"),
        responses={status.HTTP_200_OK: GetDiskTypeResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def get_disktypes(self, request):
        return Response(DBResourceApi.get_disktypes())

    @common_swagger_auto_schema(
        operation_summary=_("获取操作系统类型"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def get_os_types(self, request):
        return Response(BkOsType.get_values())

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
        device_classes = sorted(DBResourceApi.get_device_class())
        return Response(device_classes)

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
        data = self.params_validate(self.get_serializer_class())
        resp = ResourceHandler.resource_delete(data, request.user.username)

        return Response(resp)

    @common_swagger_auto_schema(
        operation_summary=_("资源更新"),
        request_body=ResourceUpdateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], url_path="update", serializer_class=ResourceUpdateSerializer)
    def resource_update(self, request):
        update_params = self.params_validate(self.get_serializer_class())
        # 修改主机属性和主机资源归属时添加操作记录
        if update_params.get("update_type") and update_params.get("remark"):
            update_type = update_params.pop("update_type")
            remark = update_params.pop("remark")
            bk_biz_id = update_params.pop("bk_biz_id")
            host_id_ip_map = update_params.pop("host_id_ip_map")
            remark_map, hosts = ResourceHandler.get_evnet_info(update_params["bk_host_ids"], remark, host_id_ip_map)
            MachineEvent.create_machine_events(
                bk_biz_id, hosts, update_type, None, request.user.username, None, "", remark_map
            )
        return Response(DBResourceApi.resource_batch_update(params=update_params))

    @common_swagger_auto_schema(
        operation_summary=_("按照组件统计资源数量"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def resource_group_count(self, request):
        return Response(DBResourceApi.resource_group_count())

    @common_swagger_auto_schema(
        operation_summary=_("按照条件聚合资源统计"),
        query_serializer=ResourceSummarySerializer(),
        responses={status.HTTP_200_OK: ResourceSummaryResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ResourceSummarySerializer)
    def resource_summary(self, request):
        group_params = self.params_validate(self.get_serializer_class())
        data = DBResourceApi.resource_summary(params=group_params)
        no_spec_ip_list, summary_data = data["no_spec_ip_list"], data["summary_data"]
        # 补充业务名
        for_biz_ids = [data["dedicated_biz"] for data in summary_data]
        for_biz_infos = AppCache.batch_get_app_attr(bk_biz_ids=for_biz_ids, attr_name="bk_biz_name")
        summary_data = [{"for_biz_name": for_biz_infos.get(data["dedicated_biz"]), **data} for data in summary_data]
        return Response({"no_spec_ip_list": no_spec_ip_list, "summary_data": summary_data})

    @common_swagger_auto_schema(
        operation_summary=_("获取资源导入相关链接"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], url_path="resource_import_urls")
    def resource_import_urls(self, request):
        return Response(
            {"bk_cmdb_url": env.BK_CMDB_URL, "bk_nodeman_url": env.BK_NODEMAN_URL, "bk_scr_url": env.BK_SCR_URL}
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询资源操作记录"),
        query_serializer=QueryOperationListSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="query_operation_list",
        serializer_class=QueryOperationListSerializer,
        pagination_class=None,
    )
    @Permission.decorator_permission_field(
        id_field=lambda d: d["task_id"],
        data_field=lambda d: d["results"],
        actions=[ActionEnum.FLOW_DETAIL],
        resource_meta=ResourceEnum.TASKFLOW,
    )
    @Permission.decorator_permission_field(
        id_field=lambda d: d["ticket_id"],
        data_field=lambda d: d["results"],
        actions=[ActionEnum.TICKET_VIEW],
        resource_meta=ResourceEnum.TICKET,
    )
    def query_operation_list(self, request):
        query_params = self.params_validate(self.get_serializer_class())
        operation_list = DBResourceApi.operation_list(query_params)
        operation_list["results"] = operation_list.pop("details") or []

        task_ids: List[int] = [op["task_id"] for op in operation_list["results"]]
        task_id__task: Dict[int, Ticket] = {
            task.root_id: task for task in FlowTree.objects.filter(root_id__in=task_ids)
        }
        for op in operation_list["results"]:
            # 格式化操作记录参数
            op["ticket_id"] = int(op.pop("bill_id") or 0)
            op["ticket_type"] = op.pop("bill_type", "")
            op["ticket_type_display"] = TicketType.get_choice_label(op["ticket_type"])
            op["bk_biz_id"] = getattr(task_id__task.get(op["task_id"]), "bk_biz_id", env.DBA_APP_BK_BIZ_ID)
            task_status = getattr(task_id__task.get(op["task_id"]), "status", "")
            op["status"] = BAMBOO_STATE__TICKET_STATE_MAP.get(task_status, TicketStatus.RUNNING)

        # 过滤单据状态的操作记录
        operation_list["results"] = [
            op
            for op in operation_list["results"]
            if not query_params.get("status") or op["status"] == query_params["status"]
        ]

        return Response(operation_list)

    @common_swagger_auto_schema(
        operation_summary=_("规格数量的预计"),
        request_body=SpecCountResourceSerializer(),
        responses={status.HTTP_200_OK: SpecCountResourceResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="spec_resource_count",
        serializer_class=SpecCountResourceSerializer,
        pagination_class=None,
    )
    def spec_resource_count(self, request):
        apply_params = self.params_validate(self.get_serializer_class())
        return Response(ResourceHandler.spec_resource_count(**apply_params))

    @common_swagger_auto_schema(
        operation_summary=_("规格成本预估"),
        request_body=SpecCostEstimateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=SpecCostEstimateSerializer, pagination_class=None)
    def spec_cost_estimate(self, request):
        data = self.params_validate(self.get_serializer_class())
        return Response(ResourceHandler.spec_cost_estimate(**data))

    @common_swagger_auto_schema(
        operation_summary=_("查询故障主机信息(检查uwork/xwork单)"),
        request_body=CheckFaultHostsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=CheckFaultHostsSerializer)
    def check_fault_hosts(self, request):
        data = self.params_validate(self.get_serializer_class())

        host_ip__id_map = {host["ip"]: host["bk_host_id"] for host in data["hosts"]}
        uwork_infos_map = HCMApi.check_host_has_uwork(list(host_ip__id_map.keys()))
        xwork_infos_map = XworkApi.check_xwork_list(host_ip__id_map)

        fault_host_infos = {
            bk_host_id: {"xwork": xwork_infos_map.get(bk_host_id, {}), "uwork": uwork_infos_map.get(bk_host_id, {})}
            for bk_host_id in host_ip__id_map.values()
        }
        return Response(fault_host_infos)

    @common_swagger_auto_schema(
        operation_summary=_("追加主机标签"),
        request_body=AppendHostLabelSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=AppendHostLabelSerializer)
    def append_labels(self, request):
        append_params = self.params_validate(self.get_serializer_class())
        # 修改主机属性和主机资源归属时添加操作记录
        if append_params.get("remark"):
            remark = append_params.pop("remark")
            bk_biz_id = append_params.pop("bk_biz_id")
            host_id_ip_map = append_params.pop("host_id_ip_map")
            remark_map, hosts = ResourceHandler.get_evnet_info(append_params["bk_host_ids"], remark, host_id_ip_map)
            if not remark_map:
                return Response(DBResourceApi.resource_append_labels(append_params))
            MachineEvent.create_machine_events(
                bk_biz_id, hosts, "resource_owner", None, request.user.username, None, "", remark_map
            )
        return Response(DBResourceApi.resource_append_labels(append_params))

    @common_swagger_auto_schema(
        operation_summary=_("计算资源池水位信息"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=CalcResourceWaterLevelSerializer)
    def calc_resource_water_level(self, request):
        params = self.params_validate(self.get_serializer_class())
        data = ResourceHandler.calc_resource_water_level(get_cache=params["cache"])
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("资源池导出"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=ResourceListSerializer)
    def resource_export(self, request):
        params = self.params_validate(self.get_serializer_class())
        return ResourceHandler.resource_export(params)
