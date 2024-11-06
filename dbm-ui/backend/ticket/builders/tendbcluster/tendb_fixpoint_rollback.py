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

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.components import DBConfigApi
from backend.components.dbconfig import constants as dbconf_const
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.comm import SystemTagEnum, TagType
from backend.db_meta.models import AppCache, Cluster, Tag
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.common.constants import FixpointRollbackType, RollbackBuildClusterType
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.mysql.base import DBTableField
from backend.ticket.builders.mysql.mysql_fixpoint_rollback import MySQLFixPointRollbackDetailSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import ClusterOperateRecord, Flow
from backend.utils.time import date2str


class TendbFixPointRollbackDetailSerializer(TendbBaseOperateDetailSerializer):
    class RollbackInfoSerializer(serializers.Serializer):
        class RollbackHostSerializer(serializers.Serializer):
            spider_host = HostInfoSerializer(help_text=_("spider新机器"))
            remote_hosts = serializers.ListSerializer(help_text=_("remote新机器"), child=HostInfoSerializer())

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        target_cluster_id = serializers.IntegerField(help_text=_("回档集群ID"), default=False)
        rollback_host = RollbackHostSerializer(help_text=_("备份新机器"), default=False)
        rollback_type = serializers.ChoiceField(help_text=_("回档类型"), choices=FixpointRollbackType.get_choices())
        rollback_time = DBTimezoneField(
            help_text=_("回档时间"), required=False, allow_blank=True, allow_null=True, default=""
        )
        backupinfo = serializers.DictField(
            help_text=_("备份文件信息"), required=False, allow_null=True, allow_empty=True, default={}
        )
        databases = serializers.ListField(help_text=_("目标库列表"), child=DBTableField(db_field=True))
        databases_ignore = serializers.ListField(
            help_text=_("忽略库列表"), child=DBTableField(db_field=True), required=False
        )
        tables = serializers.ListField(help_text=_("目标table列表"), child=DBTableField())
        tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField(), required=False)

    rollback_cluster_type = serializers.ChoiceField(
        help_text=_("回档集群类型"), choices=RollbackBuildClusterType.get_choices()
    )
    infos = serializers.ListSerializer(help_text=_("回档信息"), child=RollbackInfoSerializer())
    ignore_check_db = serializers.BooleanField(help_text=_("是否忽略业务库"), required=False, default=False)

    def validate(self, attrs):
        # 校验集群是否可用
        super().validate_cluster_can_access(attrs)

        # 校验回档信息
        now = datetime.datetime.now(timezone.utc)
        for info in attrs["infos"]:
            MySQLFixPointRollbackDetailSerializer.validate_rollback_info(attrs["rollback_cluster_type"], info, now)

        return attrs


class TendbFixPointRollbackFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendb_cluster_rollback_data

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["source_cluster_id"] = info.pop("cluster_id")

    def pre_callback(self):
        if self.ticket_data["rollback_cluster_type"] != RollbackBuildClusterType.BUILD_INTO_NEW_CLUSTER:
            return

        rollback_flow = self.ticket.current_flow()
        # 新部署集群的回档，infos只会有一个元素
        ticket_data = rollback_flow.details["ticket_data"]
        info = ticket_data["infos"][0]
        # 为定点构造的flow填充临时集群信息
        source_cluster_id = info["source_cluster_id"]
        # 对同一个集群同一天回档26^4才有可能重名, 暂时无需担心
        target_cluster = Cluster.objects.get(name=ticket_data["apply_details"]["cluster_name"])
        info.update(source_cluster_id=source_cluster_id, target_cluster_id=target_cluster.id)
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
    controller = SpiderController.spider_cluster_apply_no_slave

    def format_ticket_data(self):
        self.ticket_data = self.ticket_data["apply_details"]
        # 填充common参数
        super().add_common_params()
        # 修改单据类型为部署类型
        self.ticket_data["ticket_type"] = TicketType.TENDBCLUSTER_APPLY


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_ROLLBACK_CLUSTER, is_apply=True)
class TendbFixPointRollbackFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbFixPointRollbackDetailSerializer

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

        # 获取remote的部署规格和机器组数
        remote_machine_data = []
        for storage_set in cluster.tendbclusterstorageset_set.all():
            master_machine = storage_set.storage_instance_tuple.ejector.machine
            remote_machine_data.append(
                {"machine__bk_host_id": master_machine.bk_host_id, "machine__spec_id": master_machine.spec_id}
            )

        rollback_host = self.ticket.details["infos"][0]["rollback_host"]
        remote_machine_count = len(rollback_host["remote_hosts"])

        details.update(
            cluster_shard_num=cluster_shard_num,
            remote_shard_num=int(cluster_shard_num / remote_machine_count),
            spider_ip_list=[rollback_host["spider_host"]],
            remote_group=[{"master": host, "slave": {}} for host in rollback_host["remote_hosts"]],
        )

    def patch_apply_ticket_detail(self):
        if self.ticket.details["rollback_cluster_type"] != RollbackBuildClusterType.BUILD_INTO_NEW_CLUSTER:
            return

        cluster = Cluster.objects.get(id=self.ticket.details["infos"][0]["cluster_id"])
        cluster_name = f"{cluster.name}-tmp{date2str(datetime.date.today(), '%Y%m%d')}-{self.ticket.id}"
        db_app_abbr = AppCache.get_app_attr(cluster.bk_biz_id)

        # 集群部署的基本信息
        apply_details = {
            "bk_cloud_id": cluster.bk_cloud_id,
            "db_app_abbr": db_app_abbr,
            "cluster_name": cluster_name,
            "city": cluster.region,
            "module": cluster.db_module_id,
            "disaster_tolerance_level": cluster.disaster_tolerance_level,
            "immutable_domain": f"spider.{cluster_name}.{db_app_abbr}.db",
            "ip_source": IpSource.RESOURCE_POOL,
            "spider_port": cluster.proxyinstance_set.first().port,
        }
        # 填充配置信息
        self.get_cluster_config(cluster, apply_details)
        # 填充集群部署规格信息
        self.get_cluster_apply_spec(cluster, apply_details)

        self.ticket.update_details(apply_details=apply_details)

    def patch_ticket_detail(self):
        self.patch_apply_ticket_detail()
        super().patch_ticket_detail()

    def custom_ticket_flows(self):
        flows = []

        if self.ticket.details["rollback_cluster_type"] == RollbackBuildClusterType.BUILD_INTO_NEW_CLUSTER:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=TendbApplyTemporaryFlowParamBuilder(self.ticket).get_params(),
                    flow_alias=_("回档临时集群部署"),
                    retry_type=FlowRetryType.MANUAL_RETRY.value,
                )
            )

        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbFixPointRollbackFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("TenDBCluster 回档执行"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            )
        )

        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([_("回档临时集群部署"), _("TenDBCluster 回档执行")])
        return flow_desc
