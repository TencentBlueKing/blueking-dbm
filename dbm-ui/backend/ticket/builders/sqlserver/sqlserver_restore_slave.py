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
import itertools

from django.db.models import F, Prefetch
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.flow.utils.sqlserver.sqlserver_bk_config import get_module_infos
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.sqlserver.base import (
    BaseSQLServerHATicketFlowBuilder,
    SQLServerBaseOperateDetailSerializer,
    SQLServerBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType
from backend.ticket.exceptions import TicketParamsVerifyException
from backend.utils.basic import get_target_items_from_details


class SQLServerRestoreSlaveDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class SlaveInfoSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群列表"), child=serializers.IntegerField())
        resource_spec = serializers.JSONField(help_text=_("资源池规格"), required=False)
        old_slave_host = HostInfoSerializer(help_text=_("旧slave机器信息"))
        new_slave_host = HostInfoSerializer(help_text=_("新slave机器信息"), required=False)

    infos = serializers.ListField(help_text=_("重建从库列表"), child=SlaveInfoSerializer())
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())

    def validate(self, attrs):
        # 校验实例的角色为slave
        # super(MysqlRestoreLocalSlaveDetailSerializer, self).validate_instance_role(
        #     attrs, instance_key=["slave"], role=InstanceInnerRole.SLAVE
        # )
        # 校验集群是否可用，集群类型为高可用
        super(SQLServerRestoreSlaveDetailSerializer, self).validate_cluster_can_access(attrs)
        super(SQLServerRestoreSlaveDetailSerializer, self).validated_cluster_type(attrs, ClusterType.SqlserverHA)

        super().validate(attrs)
        return attrs


class SQLServerRestoreSlaveFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.slave_rebuild_in_new_slave_scene

    def format_ticket_data(self):
        pass
        # for info in self.ticket_data["infos"]:
        #     info["slave_host"] = info.pop("slave")
        #     info["port"] = info["slave_host"].pop("port")


class SQLServerRestoreSlaveResourceParamBuilder(SQLServerBaseOperateResourceParamBuilder):
    def format(self):
        slave_hosts = get_target_items_from_details(self.ticket.details, match_keys=["bk_host_id"])
        # 根据从库host_id获取对应主库的host_id
        slave_master_mapping = (
            Machine.objects.prefetch_related(
                "storageinstance_set",
                Prefetch("storageinstance_set__as_ejector"),
                Prefetch("storageinstance_set__as_receiver"),
            )
            .filter(storageinstance__as_ejector__receiver__machine__bk_host_id__in=slave_hosts)
            .values(
                slave_host_id=F("storageinstance__as_ejector__receiver__machine__bk_host_id"),
                master_host_id=F("bk_host_id"),
            )
            .distinct()
        )

        # 提取master
        master_hosts = [entry["master_host_id"] for entry in slave_master_mapping]
        # 处理映射 {slave_host_id:master_host_id}
        formatted_dict = {item["slave_host_id"]: item["master_host_id"] for item in slave_master_mapping}

        id__machine = {
            machine.bk_host_id: machine
            for machine in Machine.objects.prefetch_related("bk_city__logical_city").filter(
                bk_host_id__in=master_hosts
            )
        }
        cluster_ids = list(itertools.chain(*[infos["cluster_ids"] for infos in self.ticket.details["infos"]]))
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}

        for info in self.ticket_data["infos"]:
            cluster = id__cluster[info["cluster_ids"][0]]
            # 申请新的slave, 需要和当前集群中的master处于不同机房;
            master_machine = id__machine[formatted_dict[info["old_slave_host"]["bk_host_id"]]]
            info.update(bk_cloud_id=master_machine.bk_cloud_id)
            # TODO: 还有补充操作系统
            info["resource_spec"]["sqlserver_ha"]["location_spec"] = {
                "city": master_machine.bk_city.logical_city.name,
                "sub_zone_ids": [],
            }
            info["resource_spec"]["sqlserver_ha"].update(affinity=cluster.disaster_tolerance_level)
            if cluster.disaster_tolerance_level == AffinityEnum.CROS_SUBZONE:
                info["resource_spec"]["sqlserver_ha"]["location_spec"].update(
                    sub_zone_ids=[master_machine.bk_sub_zone_id], include_or_exclue=False
                )

            elif cluster.disaster_tolerance_level in [
                AffinityEnum.SAME_SUBZONE,
                AffinityEnum.SAME_SUBZONE_CROSS_SWTICH,
            ]:
                info["resource_spec"]["sqlserver_ha"]["location_spec"].update(
                    sub_zone_ids=[master_machine.bk_sub_zone_id], include_or_exclue=True
                )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            info["new_slave_host"] = info["sqlserver_ha"][0]
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.SQLSERVER_RESTORE_SLAVE)
class SQLServerRestoreSlaveFlowBuilder(BaseSQLServerHATicketFlowBuilder):
    serializer = SQLServerRestoreSlaveDetailSerializer
    resource_batch_apply_builder = SQLServerRestoreSlaveResourceParamBuilder
    inner_flow_builder = SQLServerRestoreSlaveFlowParamBuilder
    inner_flow_name = _("SQLServer Slave重建执行")

    def patch_ticket_detail(self):
        # 补充数据库版本和字符集

        cluster_ids = [cluster_id for info in self.ticket.details["infos"] for cluster_id in info["cluster_ids"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket.details["infos"]:
            db_config = get_module_infos(
                bk_biz_id=self.ticket.bk_biz_id,
                db_module_id=id__cluster[info["cluster_ids"][0]].db_module_id,
                cluster_type=id__cluster[info["cluster_ids"][0]].cluster_type,
            )
            # 校验配置是否存在
            if not db_config.get("db_version") or not db_config.get("charset") or not db_config.get("sync_type"):
                raise TicketParamsVerifyException(_("获取数据库字符集或版本失败，请检查获取参数, db_config: {}").format(db_config))

            info["system_version"] = db_config["system_version"].split(",")

        # 添加集群信息
        super().patch_ticket_detail()
