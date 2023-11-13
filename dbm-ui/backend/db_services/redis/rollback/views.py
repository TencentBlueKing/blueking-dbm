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
import time

from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import ReadOnlyAuditedModelViewSet
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterType, DestroyedStatus
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.exceptions import AppBaseException
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigTypeEnum

from . import constants
from .handlers import DataStructureHandler
from .models import TbTendisRollbackTasks
from .serializers import CheckTimeSerializer, RollbackSerializer


class RollbackListFilter(filters.FilterSet):
    prod_cluster = filters.CharFilter(field_name="prod_cluster", lookup_expr="icontains", label=_("集群域名"))
    related_rollback_bill_id = filters.CharFilter(
        field_name="related_rollback_bill_id", lookup_expr="exact", label=_("单据id")
    )

    class Meta:
        model = TbTendisRollbackTasks
        fields = ["prod_cluster_id", "prod_cluster", "related_rollback_bill_id", "temp_cluster_proxy"]


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
class RollbackViewSet(ReadOnlyAuditedModelViewSet):
    """实例构造管理"""

    queryset = TbTendisRollbackTasks.objects.exclude(destroyed_status=DestroyedStatus.DESTROYED).order_by(
        "destroyed_status", "-create_at"
    )
    serializer_class = RollbackSerializer
    filter_class = RollbackListFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        bk_biz_id = self.kwargs.get("bk_biz_id")
        if self.action == "list" and bk_biz_id:
            queryset = queryset.filter(bk_biz_id=bk_biz_id)

        return queryset

    @common_swagger_auto_schema(
        operation_summary=_("构造时间合法性检查"),
        request_body=CheckTimeSerializer(),
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=CheckTimeSerializer)
    def check_time(self, request, bk_biz_id, **kwargs):
        cluster_id = self.validated_data["cluster_id"]
        rollback_time = self.validated_data["rollback_time"]

        master_instances = self.validated_data["master_instances"]
        for master_instance in master_instances:
            ip, port = master_instance.split(":")

            storage_pair = StorageInstanceTuple.objects.filter(ejector__machine__ip=ip, ejector__port=port).first()
            slave_ip, slave_port = storage_pair.receiver.machine.ip, storage_pair.receiver.port

            cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
            rollback_handler = DataStructureHandler(cluster.id)

            try:
                backup_info = rollback_handler.query_latest_backup_log(rollback_time, slave_ip, slave_port)
            except AppBaseException:
                return Response({"exist": False, "msg": f"[{master_instance}] query backup info exception failed"})

            # 全备份的开始时间
            backup_time = time.strptime(backup_info["file_last_mtime"], "%Y-%m-%d %H:%M:%S")
            if cluster.cluster_type in [ClusterType.TendisplusInstance.value, ClusterType.TendisSSDInstance.value]:
                try:
                    kvstore_count = None
                    if cluster.cluster_type == ClusterType.TendisplusInstance.value:
                        kvstore_count = DBConfigApi.query_conf_item(
                            params={
                                "bk_biz_id": str(self.data["bk_biz_id"]),
                                "level_name": LevelName.CLUSTER,
                                "level_value": cluster.immute_domain,
                                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                                "conf_file": cluster.major_version,
                                "conf_type": ConfigTypeEnum.DBConf,
                                "namespace": cluster.cluster_type,
                                "format": FormatType.MAP,
                            }
                        )["content"]["kvstorecount"]

                    backup_binlog = rollback_handler.query_binlog_from_bklog(
                        start_time=backup_time,
                        end_time=rollback_time,
                        minute_range=120,
                        host_ip=slave_ip,
                        port=slave_port,
                        kvstorecount=kvstore_count,
                        tendis_type=cluster.cluster_type,
                    )
                except AppBaseException:
                    return Response({"exist": False, "msg": f"[{master_instance}] query binlog info exception failed"})

                if backup_binlog is None:
                    return Response({"exist": False, "msg": f"[{master_instance}] query binlog info failed"})

            return Response({"exist": True, "msg": "success"})
