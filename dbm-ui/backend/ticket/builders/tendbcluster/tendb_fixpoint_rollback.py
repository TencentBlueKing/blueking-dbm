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

from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.components import DBConfigApi
from backend.components.dbconfig import constants as dbconf_const
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.enums.comm import SystemTagEnum, TagType
from backend.db_meta.models import AppCache, Cluster, Tag
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.constants import FixpointRollbackType
from backend.ticket.builders.mysql.base import DBTableField
from backend.ticket.builders.mysql.mysql_fixpoint_rollback import MySQLFixPointRollbackDetailSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.builders.tendbcluster.tendb_apply import TenDBClusterApplyResourceParamBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import ClusterOperateRecord, Flow
from backend.utils.time import date2str


class TendbFixPointRollbackDetailSerializer(TendbBaseOperateDetailSerializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    rollback_type = serializers.ChoiceField(help_text=_("回档类型"), choices=FixpointRollbackType.get_choices())
    rollback_time = serializers.CharField(
        help_text=_("回档时间"), required=False, allow_blank=True, allow_null=True, default=""
    )
    backupinfo = serializers.DictField(
        help_text=_("备份文件信息"), required=False, allow_null=True, allow_empty=True, default={}
    )
    databases = serializers.ListField(help_text=_("目标库列表"), child=DBTableField(db_field=True))
    databases_ignore = serializers.ListField(help_text=_("忽略库列表"), child=DBTableField(db_field=True), required=False)
    tables = serializers.ListField(help_text=_("目标table列表"), child=DBTableField())
    tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField(), required=False)

    def validate(self, attrs):
        # 校验集群是否可用
        super().validate_cluster_can_access(attrs)

        # 校验回档信息
        MySQLFixPointRollbackDetailSerializer.validate_rollback_info(attrs, datetime.datetime.now())

        return attrs


class TendbFixPointRollbackFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendb_cluster_rollback_data

    def format_ticket_data(self):
        pass

    def pre_callback(self):
        rollback_flow = self.ticket.current_flow()
        ticket_data = rollback_flow.details["ticket_data"]

        # 为定点构造的flow填充临时集群信息
        source_cluster_id = ticket_data.pop("cluster_id")
        # 对同一个集群同一天回档26^4才有可能重名, 暂时无需担心
        target_cluster = Cluster.objects.get(name=ticket_data["apply_details"]["cluster_name"])
        ticket_data.update(source_cluster_id=source_cluster_id, target_cluster_id=target_cluster.id)
        rollback_flow.save(update_fields=["details"])

        # 对临时集群记录变更
        temporary_tag, _ = Tag.objects.get_or_create(
            bk_biz_id=self.ticket.bk_biz_id, name=SystemTagEnum.TEMPORARY.value, type=TagType.SYSTEM.value
        )
        target_cluster.tag_set.add(temporary_tag)
        ClusterOperateRecord.objects.get_or_create(
            cluster_id=target_cluster.id, ticket=self.ticket, flow=rollback_flow
        )


class TendbApplyTemporaryFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_cluster_apply_scene

    def format_ticket_data(self):
        self.ticket_data = self.ticket_data["apply_details"]
        # 填充common参数
        super().add_common_params()
        # 修改单据类型为部署类型
        self.ticket_data["ticket_type"] = TicketType.TENDBCLUSTER_APPLY


class TenDBClusterApplyCopyResourceParamBuilder(TenDBClusterApplyResourceParamBuilder):
    def format(self):
        self.ticket_data = self.ticket_data["apply_details"]

    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_ROLLBACK_CLUSTER, is_apply=True)
class TendbFixPointRollbackFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbFixPointRollbackDetailSerializer

    def get_machine_spec(self, machine_infos):
        # 获取机器的数量和规格，默认认为同一角色的规格是相同的
        machine_count = len(set([data["machine__bk_host_id"] for data in machine_infos]))
        spec_id = machine_infos[0]["machine__spec_id"]
        return machine_count, spec_id

    def get_cluster_config(self, cluster, details):
        db_config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": dbconf_const.LevelName.MODULE,
                "level_value": str(cluster.db_module_id),
                "conf_file": dbconf_const.DEPLOY_FILE_NAME,
                "conf_type": dbconf_const.ConfType.DEPLOY,
                "namespace": ClusterType.TenDBCluster,
                "format": dbconf_const.FormatType.MAP,
            }
        )["content"]
        details.update(
            charset=db_config.get("charset"),
            db_version=db_config.get("db_version"),
            spider_version=db_config.get("spider_version"),
        )

    def get_cluster_apply_spec(self, cluster, details):
        # 获取集群分片数
        cluster_shard_num = cluster.tendbclusterstorageset_set.count()
        # 获取spider的部署规格和机器数
        spider_machine_data = list(
            cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value
            ).values("machine__bk_host_id", "machine__spec_id")
        )
        spider_machine_count, spider_spec_id = self.get_machine_spec(spider_machine_data)
        # 获取remote的部署规格和机器组数
        remote_machine_data = []
        for storage_set in cluster.tendbclusterstorageset_set.all():
            master_machine = storage_set.storage_instance_tuple.ejector.machine
            remote_machine_data.append(
                {"machine__bk_host_id": master_machine.bk_host_id, "machine__spec_id": master_machine.spec_id}
            )

        remote_machine_count, remote_spec_id = self.get_machine_spec(remote_machine_data)
        # 填充资源池规格信息和分片信息
        resource_spec = {
            "spider": {"spec_id": spider_spec_id, "count": spider_machine_count},
            "backend_group": {"spec_id": remote_spec_id, "count": remote_machine_count},
        }
        details.update(
            resource_spec=resource_spec,
            cluster_shard_num=cluster_shard_num,
            remote_shard_num=int(cluster_shard_num / remote_machine_count),
        )

    def patch_ticket_detail(self):
        cluster = Cluster.objects.get(id=self.ticket.details["cluster_id"])
        cluster_name = f"{cluster.name}-tmp{get_random_string(4).lower()}{date2str(datetime.date.today(), '%Y%m%d')}"
        db_app_abbr = AppCache.get_app_attr(cluster.bk_biz_id)

        # 集群部署的基本信息
        apply_details = {
            "bk_cloud_id": cluster.bk_cloud_id,
            "db_app_abbr": db_app_abbr,
            "cluster_name": cluster_name,
            "city": cluster.region,
            "module": cluster.db_module_id,
            "immutable_domain": f"spider.{cluster_name}.{db_app_abbr}.db",
            "ip_source": IpSource.RESOURCE_POOL,
            "spider_port": cluster.proxyinstance_set.first().port,
        }
        # 填充配置信息
        self.get_cluster_config(cluster, apply_details)
        # 填充集群部署规格信息
        self.get_cluster_apply_spec(cluster, apply_details)

        self.ticket.update_details(apply_details=apply_details)
        super().patch_ticket_detail()

    def custom_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.RESOURCE_APPLY,
                details=TenDBClusterApplyCopyResourceParamBuilder(self.ticket).get_params(),
                flow_alias=_("资源申请"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbApplyTemporaryFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("回档临时集群部署"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbFixPointRollbackFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("TenDBCluster 回档执行"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.RESOURCE_DELIVERY,
                flow_alias=_("资源确认"),
            ),
        ]
        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([_("资源申请"), _("回档临时集群部署"), _("TenDBCluster 回档执行"), _("资源确认")])
        return flow_desc
