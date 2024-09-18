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
import traceback
from typing import Any

from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, ClusterEntry, DBModule
from backend.db_services.mysql.toolbox.handlers import ToolboxHandler
from backend.db_services.mysql.toolbox.serializers import (
    QueryPkgListByCompareVersionSerializer,
    TendbhaAddSlaveDomainSerializer,
    TendbhaTransferToOtherBizSerializer,
)
from backend.flow.utils.dns_manage import DnsManage
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


SWAGGER_TAG = "db_services/mysql/toolbox"


class ToolboxViewSet(viewsets.SystemViewSet):
    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询 MySQL 可以用的升级包"),
        request_body=QueryPkgListByCompareVersionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryPkgListByCompareVersionSerializer)
    def query_higher_version_pkg_list(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id, higher_major_version = data["cluster_id"], data["higher_major_version"]
        return Response(ToolboxHandler().query_higher_version_pkg_list(cluster_id, higher_major_version))


class TendbHaSlaveInstanceAddDomainSet(viewsets.SystemViewSet):
    """
    给从库添加域名
    """

    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("给从库添加域名"),
        request_body=TendbhaAddSlaveDomainSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TendbhaAddSlaveDomainSerializer)
    def slave_ins_add_domain(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id = data["cluster_id"]
        domain = data["domain_name"]
        slave_ip = data["slave_ip"]
        slave_port = data["slave_port"]
        if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=domain).exists():
            return Response({"result": False, "message": _("{}域名已经存在".format(domain))})
        cluster_obj = Cluster.objects.get(id=cluster_id)
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster_obj,
            cluster_entry_type=ClusterEntryType.DNS.value,
            entry=domain,
            role=ClusterEntryRole.SLAVE_ENTRY.value,
        )
        dns_manage = DnsManage(bk_biz_id=cluster_obj.bk_biz_id, bk_cloud_id=cluster_obj.bk_cloud_id)
        slave_ins = cluster_obj.storageinstance_set.filter(
            instance_inner_role=InstanceInnerRole.SLAVE.value, machine__ip=slave_ip, port=slave_port
        )
        cluster_entry.storageinstance_set.add(*slave_ins)
        try:
            dns_manage.create_domain(instance_list=["{}#{}".format(slave_ip, str(slave_port))], add_domain_name=domain)
        except Exception as e:
            logger.error(traceback.format_exc())
            return Response({"result": False, "message": _("添加dns记录失败{}".format(e))})
        return Response({"result": True, "message": _("success")})


class TendbhaTransferToOtherBizViewSet(viewsets.SystemViewSet):
    """
    转移tendbha 集群到其他业务
    """

    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("TenDBHA 集群转移到其他业务"),
        request_body=TendbhaTransferToOtherBizSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=TendbhaTransferToOtherBizSerializer)
    def transfer_tendbha_to_other_biz(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        logger.info("request data: {}".format(data))
        db_module_id = data["db_module_id"]
        target_biz_id = data["target_biz_id"]
        bk_biz_id = data["bk_biz_id"]
        cluster_domain_list = data["cluster_domain_list"]

        result = DBModule.objects.filter(db_module_id=db_module_id, bk_biz_id=target_biz_id)
        if not result.exists():
            return Response({"result": False, "message": _("目标业务的db模块不存在")})
        if target_biz_id == bk_biz_id:
            return Response({"result": False, "message": _("目标业务不能是自己")})

        clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain__in=cluster_domain_list).all()
        source_db_module_ids = []
        cluster_types = []
        for cluster in clusters:
            source_db_module_ids.append(cluster.db_module_id)
            cluster_types.append(cluster.cluster_type)

        uniq_cluster_types = list(set(cluster_types))
        if len(uniq_cluster_types) != 1:
            return Response({"result": False, "message": _("迁移的集群必须在同一个类型")})

        cluster_type = uniq_cluster_types[0]
        if cluster_type not in [ClusterType.TenDBHA.value, ClusterType.TenDBSingle.value]:
            return Response({"result": False, "message": _("目前只能转移 TenDBHA 和 TenDBSingle 集群")})

        target_module_db_version, target_module_charset = self.__get_version_and_charset(
            target_biz_id, db_module_id, cluster_type
        )

        for src_db_module_id in list(set(source_db_module_ids)):
            src_module_db_version, src_module_charset = self.__get_version_and_charset(
                bk_biz_id, src_db_module_id, cluster_type
            )
            if src_module_db_version != target_module_db_version or src_module_charset != target_module_charset:
                return Response({"result": False, "message": _("源模块和目标模块的版本或字符集不一致,请检查一下")})

        TendbhaTransferToOtherBizSerializer(data=data).is_valid(raise_exception=True)
        Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_HA_TRANSFER_TO_OTHER_BIZ,
            creator=request.user.username,
            bk_biz_id=data["bk_biz_id"],
            remark=self.transfer_tendbha_to_other_biz.__name__,
            details=data,
        )
        return Response(data)

    def __get_version_and_charset(self, bk_biz_id, db_module_id, cluster_type) -> Any:
        """获取版本号和字符集信息"""
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.MODULE,
                "level_value": str(db_module_id),
                "conf_file": "deploy_info",
                "conf_type": "deploy",
                "namespace": cluster_type,
                "format": FormatType.MAP,
            }
        )["content"]
        return data["charset"], data["db_version"]
