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
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.mysql_partition.client import DBPartitionApi
from backend.db_meta.enums import ClusterType
from backend.db_services.partition.serializers import (
    PartitionBatchDryRunResponseSerializer,
    PartitionBatchDryRunSerializer,
    PartitionColumnVerifyResponseSerializer,
    PartitionColumnVerifySerializer,
    PartitionCreateSerializer,
    PartitionDeleteSerializer,
    PartitionDisableSerializer,
    PartitionDryRunResponseSerializer,
    PartitionDryRunSerializer,
    PartitionEnableSerializer,
    PartitionExecuteV2Serializer,
    PartitionExportImportFailedSerializer,
    PartitionExportResponseSerializer,
    PartitionExportSerializer,
    PartitionFieldTypeV2ResponseSerializer,
    PartitionFieldTypeV2Serializer,
    PartitionImportResultSerializer,
    PartitionImportSerializer,
    PartitionListResponseSerializer,
    PartitionListSerializer,
    PartitionLogResponseSerializer,
    PartitionLogSerializer,
    PartitionLogV2ResponseSerializer,
    PartitionLogV2Serializer,
    PartitionRunSerializer,
    PartitionUpdateSerializer,
    SaveAndExecuteV2ResponseSerializer,
    SaveAndExecuteV2Serializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

from ...db_meta.models import Cluster
from ...iam_app.dataclass import ResourceEnum
from ...iam_app.dataclass.actions import ActionEnum
from ...iam_app.handlers.drf_perm.cluster import PartitionManagePermission
from ...iam_app.handlers.permission import Permission
from ...ticket.constants import TicketStatus
from .constants import SWAGGER_TAG
from .handlers import PartitionHandler


class DBPartitionViewSet(viewsets.SystemViewSet):

    pagination_class = None
    serializer_class = None

    action_permission_map = {("list", "verify_partition_field"): [DBManagePermission()]}
    default_permission_class = [PartitionManagePermission()]

    @staticmethod
    def _update_log_status(log_list):
        # 更新分区日志的状态
        for info in log_list:
            info["status"] = info["status"].upper()
            info["status"] = info["status"] if info["status"] in TicketStatus.get_values() else TicketStatus.PENDING
        return log_list

    @common_swagger_auto_schema(
        operation_summary=_("获取分区v2策略列表"),
        query_serializer=PartitionListSerializer(),
        responses={status.HTTP_200_OK: PartitionListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["bk_biz_id"],
        action_filed=lambda d: [ActionEnum.TENDBCLUSTER_PARTITION_MANAGE]
        if d["cluster_type"] == ClusterType.TenDBCluster
        else [ActionEnum.MYSQL_PARTITION_MANAGE],
        resource_meta=ResourceEnum.BUSINESS,
    )
    def list(self, request, *args, **kwargs):
        """
        # 分区v2相关接口
        """
        validated_data = self.params_validate(PartitionListSerializer)
        # partition_data = PartitionHandler.query_conf_v2(query_params=validated_data)
        # partition_list = self._update_log_status_v2(partition_data["items"])

        return Response(PartitionHandler.query_conf_v2(query_params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("修改分区v2策略"),
        request_body=PartitionUpdateSerializer(),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        """
        # 分区v2相关接口
        """
        validated_data = self.params_validate(PartitionUpdateSerializer)
        validated_data.update(id=kwargs["pk"])
        return Response(DBPartitionApi.update_conf_v2(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("增加分区v2策略"),
        request_body=PartitionCreateSerializer(),
        responses={status.HTTP_200_OK: PartitionDryRunResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        """
        # 分区v2相关接口
        """
        validated_data = self.params_validate(PartitionCreateSerializer)
        return Response(PartitionHandler.create_and_run_partition_v2(request.user.username, validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("批量删除分区v2策略"),
        request_body=PartitionDeleteSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=PartitionDeleteSerializer)
    def batch_delete(self, request, *args, **kwargs):
        """
        # 分区v2相关接口
        """
        validated_data = self.params_validate(PartitionDeleteSerializer, representation=True)
        return Response(DBPartitionApi.del_conf_v2(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("禁用分区v2策略"),
        request_body=PartitionDisableSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionDisableSerializer)
    def disable(self, request, *args, **kwargs):
        """
        # 分区v2相关接口
        """
        validated_data = self.params_validate(PartitionDisableSerializer, representation=True)
        return Response(DBPartitionApi.disable_partition_v2(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("启用分区v2策略"),
        request_body=PartitionEnableSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionEnableSerializer)
    def enable(self, request, *args, **kwargs):
        """
        # 分区v2相关接口
        """
        validated_data = self.params_validate(PartitionEnableSerializer, representation=True)
        return Response(DBPartitionApi.enable_partition_v2(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询分区v1策略日志"),
        query_serializer=PartitionLogSerializer(),
        responses={status.HTTP_200_OK: PartitionLogResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=PartitionLogSerializer)
    def query_log(self, request, *args, **kwargs):
        """
        # 分区v1相关接口
        分区v1用于查询执行日志接口，v2弃用
        """
        validated_data = self.params_validate(PartitionLogSerializer, representation=True)
        partition_log_data = DBPartitionApi.query_log(params=validated_data)
        partition_log_list = self._update_log_status(partition_log_data["items"])
        return Response({"count": partition_log_data["count"], "results": partition_log_list})

    @common_swagger_auto_schema(
        operation_summary=_("分区v1策略前置执行"),
        request_body=PartitionDryRunSerializer(),
        responses={status.HTTP_200_OK: PartitionDryRunResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionDryRunSerializer)
    def dry_run(self, request, *args, **kwargs):
        """
        # 分区v1相关接口
        分区v1用于前置执行接口，v2弃用
        """
        validated_data = self.params_validate(PartitionDryRunSerializer, representation=True)
        cluster = Cluster.objects.get(id=validated_data["cluster_id"])
        validated_data.update(
            immute_domain=cluster.immute_domain,
            bk_cloud_id=cluster.bk_cloud_id,
            cluster_type=cluster.cluster_type,
            bk_biz_id=cluster.bk_biz_id,
        )
        dry_run_data = DBPartitionApi.dry_run(params=validated_data, raw=True)
        return Response(PartitionHandler.get_dry_run_data((validated_data, dry_run_data)))

    @common_swagger_auto_schema(
        operation_summary=_("分区v1策略前置执行-批量执行"),
        request_body=PartitionBatchDryRunSerializer(),
        responses={status.HTTP_200_OK: PartitionBatchDryRunResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionBatchDryRunSerializer)
    def batch_dry_run(self, request, *args, **kwargs):
        """
        # 分区v1相关接口
        分区v1用于批量前置执行接口，v2弃用
        """
        validated_data = self.params_validate(PartitionBatchDryRunSerializer, representation=True)
        partition_list = validated_data["partition_list"]
        batch_result = PartitionHandler.batch_dry_run(partition_list)
        return Response(batch_result)

    @common_swagger_auto_schema(
        operation_summary=_("分区v1策略执行"),
        request_body=PartitionRunSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionRunSerializer)
    def execute_partition(self, request, *args, **kwargs):
        """
        # 分区v1相关接口
        分区v1用于执行接口，v2弃用
        """
        validated_data = self.params_validate(PartitionRunSerializer, representation=True)
        return Response(PartitionHandler.execute_partition(user=request.user.username, **validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("分区v2策略字段校验"),
        request_body=PartitionColumnVerifySerializer(),
        responses={status.HTTP_500_INTERNAL_SERVER_ERROR: PartitionColumnVerifyResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionColumnVerifySerializer)
    def verify_partition_field(self, request, *args, **kwargs):
        """
        用于字段校验接口，v2可复用
        """
        validated_data = self.params_validate(PartitionColumnVerifySerializer, representation=True)
        cluster = Cluster.objects.get(id=validated_data["cluster_id"])
        validated_data.update(bk_biz_id=cluster.bk_biz_id)
        return Response(PartitionHandler.verify_partition_field(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("Excel导入分区v2策略"),
        request_body=PartitionImportSerializer(),
        responses={status.HTTP_200_OK: PartitionImportResultSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionImportSerializer)
    def import_from_excel(self, request, *args, **kwargs):
        """通过Excel文件导入分区v2策略"""
        # params_validate 不会合并 request.FILES，FileField 无法获取上传文件，
        # 因此手动构建序列化器，将 request.data 和 request.FILES 一起传入
        slz = PartitionImportSerializer(data=request.data, context={"request": request})
        slz.is_valid(raise_exception=True)
        excel_file = slz.validated_data["file"]
        # 调用导入处理逻辑
        import_result = PartitionHandler.import_from_excel(request.user.username, excel_file)
        return Response(import_result)

    @common_swagger_auto_schema(
        operation_summary=_("导出分区v2策略列表"),
        request_body=PartitionExportSerializer(),
        responses={status.HTTP_200_OK: PartitionExportResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionExportSerializer)
    def export_partitions(self, request, *args, **kwargs):
        """导出分区v2策略接口，支持导出所有策略和已选策略"""
        validated_data = self.params_validate(PartitionExportSerializer, representation=True)
        export_type = validated_data["export_type"]
        selected_ids = validated_data.get("selected_ids", [])
        cluster_type = validated_data.get("cluster_type")
        bk_biz_id = validated_data.get("bk_biz_id")
        # 调用导出处理逻辑
        return PartitionHandler.export_partitions(export_type, bk_biz_id, selected_ids, cluster_type)

    # 分区v2接口
    @common_swagger_auto_schema(
        operation_summary=_("执行分区v2策略"),
        request_body=PartitionExecuteV2Serializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionExecuteV2Serializer)
    def execute_partition_v2(self, request, *args, **kwargs):
        """
        执行分区v2策略
        @param request: 请求参数
        @param args: 位置参数
        @param kwargs: 关键字参数
        @return: 响应数据
        单独的执行接口，根据force标志来判断是否强制执行
        强制执行会触发重新初始化分区表，非强制执行会触发增量执行
        """
        validated_data = self.params_validate(PartitionExecuteV2Serializer, representation=True)
        return Response(PartitionHandler.execute_partition_v2(user=request.user.username, **validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("分区v2查询分区执行日志"),
        query_serializer=PartitionLogV2Serializer(),
        responses={status.HTTP_200_OK: PartitionLogV2ResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionLogV2Serializer)
    def query_log_v2(self, request, *args, **kwargs):
        """
        查询分区v2执行日志
        """
        validated_data = self.params_validate(PartitionLogV2Serializer, representation=True)
        return Response(PartitionHandler.query_log_v2(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("分区v2查询分区字段类型"),
        query_serializer=PartitionFieldTypeV2Serializer(),
        responses={status.HTTP_200_OK: PartitionFieldTypeV2ResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionFieldTypeV2Serializer)
    def query_field_type_v2(self, request, *args, **kwargs):
        """
        查询分区v2字段类型
        用于前端填写字段名后去实际查询该字段的类型，并校验是否符合分区字段类型
        """
        validated_data = self.params_validate(PartitionFieldTypeV2Serializer, representation=True)
        return Response(PartitionHandler.query_field_type_v2(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("分区v2查询分区字段类型"),
        query_serializer=SaveAndExecuteV2Serializer(),
        responses={status.HTTP_200_OK: SaveAndExecuteV2ResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SaveAndExecuteV2Serializer)
    def save_and_execute_v2(self, request, *args, **kwargs):
        """
        保存并执行分区v2策略：
        1. 先更新分区配置
        2. 再执行分区策略
        force 标志用于判断是否强制执行：
            - 强制执行：重新初始化分区表
            - 非强制执行：增量执行分区表
        """
        validated_data = self.params_validate(SaveAndExecuteV2Serializer)
        return Response(
            PartitionHandler.save_and_execute_v2(user=request.user.username, partition_object=validated_data)
        )

    # @common_swagger_auto_schema(
    #     operation_summary=_("根据执行状态过滤分区v2配置"),
    #     request_body=QueryConfByStatusSerializer(),
    #     responses={status.HTTP_200_OK: PartitionListResponseSerializer()},
    #     tags=[SWAGGER_TAG],
    # )
    # @action(methods=["POST"], detail=False, serializer_class=QueryConfByStatusSerializer)
    # def query_conf_by_status_v2(self, request, *args, **kwargs):
    #     validated_data = self.params_validate(QueryConfByStatusSerializer)
    #     return Response(PartitionHandler.query_conf_by_status_v2(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("下载分区导入失败详情"),
        request_body=PartitionExportImportFailedSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionExportImportFailedSerializer)
    def export_import_failed(self, request, *args, **kwargs):
        "将导入失败详情导出为 Excel 文件供用户下载"
        validated_data = self.params_validate(PartitionExportImportFailedSerializer)
        return PartitionHandler.export_import_failed(validated_data["failed_items"])
