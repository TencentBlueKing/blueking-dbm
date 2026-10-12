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
from rest_framework import serializers

from backend.db_meta.models import AppCache, Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import get_mongodb_cluster_tolerance
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoShardedTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


def iter_replace_groups(hosts: list):
    """按反亲和组 + 规格分组。同组一次申请 count=台数，资源池才能一起做反亲和。"""
    buckets = {}
    for host in hosts:
        if not host.get("ip") or not host.get("spec_id"):
            continue
        spec_id = int(host["spec_id"])
        group = host.get("affinity_group") or "host"
        buckets.setdefault((group, spec_id), []).append(host)
    for (group, spec_id), members in buckets.items():
        members.sort(key=lambda item: item["ip"])
        safe = group.replace("_", "-")
        yield f"replace-{spec_id}-{safe}", members


def _tolerance_role(affinity_group: str) -> str:
    if affinity_group.startswith("mongos:"):
        return "mongos"
    if affinity_group.startswith("config:"):
        return "mongo_config"
    return "mongodb"


def assign_applied_hosts(info: dict) -> None:
    """把同组申请到的机器按 IP 写回，流程仍用 info[故障IP][0] 取新机器。"""
    hosts = list(info.get("mongos_list") or []) + list(info.get("mongod_list") or [])
    for key, members in iter_replace_groups(hosts):
        applied = info.get(key) or []
        for member, one in zip(members, applied):
            ip = member.get("ip")
            if ip and one:
                info[ip] = [one]


class MongoDBAutofixDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class AutofixDetailSerializer(serializers.Serializer):
        class HostInfoSerializer(serializers.Serializer):
            ip = serializers.IPAddressField(help_text=_("IP地址"))
            spec_id = serializers.IntegerField(help_text=_("规格ID"))

        immute_domain = serializers.CharField(help_text=_("主域名"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云ID"))
        bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
        cluster_ids = serializers.ListField(help_text=_("集群ID"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        cluster_type = serializers.CharField(help_text=_("集群类型"))
        mongos_list = serializers.ListSerializer(help_text=_("故障mongos列表"), child=HostInfoSerializer())
        mongod_list = serializers.ListSerializer(help_text=_("故障mongod列表"), child=HostInfoSerializer())

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("mongo自愈申请信息"), child=AutofixDetailSerializer())


class MongoDBAutofixFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.mongo_autofix

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBAutofixResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 同反亲和组、同规格合成一个 resource group，count=故障台数。
        self.patch_replace_affinity()
        super().format()

    def patch_replace_affinity(self):
        """补充 affinity / tolerance / current_hosts。不再把新机器钉死在故障机原园区。"""
        from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import survivor_current_hosts
        from backend.ticket.builders.common.base import fetch_cluster_ids

        infos = self.ticket_data.get("infos") or []
        cluster_ids = fetch_cluster_ids(infos)
        cluster_id_map = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in infos:
            ids = fetch_cluster_ids(info)
            if not ids or ids[0] not in cluster_id_map:
                continue
            cluster = cluster_id_map[ids[0]]
            info.update(bk_cloud_id=cluster.bk_cloud_id, bk_biz_id=self.ticket.bk_biz_id)
            hosts = list(info.get("mongos_list") or []) + list(info.get("mongod_list") or [])
            fault_host_ids = {host.get("bk_host_id") for host in hosts if host.get("bk_host_id")}
            prior = list(info.get("prior_current_hosts") or [])
            resource_spec = {}
            for key, members in iter_replace_groups(hosts):
                group = members[0].get("affinity_group") or ""
                current = survivor_current_hosts(cluster, group, fault_host_ids)
                seen = {item.get("bk_host_id") for item in current}
                for item in prior:
                    host_id = item.get("bk_host_id")
                    if host_id and host_id not in seen and host_id not in fault_host_ids:
                        current.append(item)
                        seen.add(host_id)
                sample = members[0]
                resource_spec[key] = {
                    "spec_id": int(sample["spec_id"]),
                    "count": len(members),
                    "spec_config": sample.get("spec_config"),
                    "labels": sample.get("labels") or [],
                    "label_names": sample.get("label_names") or [],
                    "affinity": cluster.disaster_tolerance_level,
                    "tolerance": get_mongodb_cluster_tolerance(
                        cluster.disaster_tolerance_level, _tolerance_role(group)
                    ),
                    "location_spec": {"city": cluster.region, "sub_zone_ids": list(cluster.zone_list or [])},
                    "current_hosts": current,
                }
            info["resource_spec"] = resource_spec

    def post_callback(self):
        """
        同组申请结果在 info[replace-规格-组] 上。拆回 info[故障IP]，供 shard_get_data / rs_get_data 使用。
        """
        with self.next_flow_manager() as next_flow:
            for info in next_flow.details["ticket_data"]["infos"]:
                assign_applied_hosts(info)


@builders.BuilderFactory.register(TicketType.MONGODB_AUTOFIX, is_apply=True, iam=ActionEnum.MONGODB_MANAGE)
class MongoDBAutofixFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoDBAutofixDetailSerializer
    inner_flow_builder = MongoDBAutofixFlowParamBuilder
    inner_flow_name = _("MongoDB 故障自愈")
    resource_batch_apply_builder = MongoDBAutofixResourceParamBuilder
    default_need_itsm = False
    default_need_manual_confirm = False
