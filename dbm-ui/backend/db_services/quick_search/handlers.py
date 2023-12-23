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
from django.db.models import F, Q
from django.forms import model_to_dict

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_services.quick_search.constants import FilterType, ResourceType
from backend.flow.models import FlowTree
from backend.ticket.models import Ticket
from backend.utils.string import split_str_to_list


class QSearchHandler(object):
    def __init__(self, bk_biz_ids=None, db_types=None, resource_types=None, filter_type=None, limit=None):
        self.bk_biz_ids = bk_biz_ids
        self.db_types = db_types
        self.resource_types = resource_types
        self.filter_type = filter_type
        self.limit = limit or 10

        # db_type -> cluster_type
        self.cluster_types = []
        if self.db_types:
            for db_type in self.db_types:
                self.cluster_types.extend(ClusterType.db_type_to_cluster_type(db_type))

    def search(self, keyword: str):
        result = {}
        target_resource_types = self.resource_types or ResourceType.get_values()
        for target_resource_type in target_resource_types:
            filter_func = getattr(self, f"filter_{target_resource_type}", None)
            if callable(filter_func):
                keyword_list = split_str_to_list(keyword)
                result[target_resource_type] = filter_func(keyword_list)

        return result

    def generate_filter_for_str(self, filter_key, keyword_list):
        """
        为字符串类型生成过滤函数
        """
        if self.filter_type == FilterType.EXACT.value:
            qs = Q(**{f"{filter_key}__in": keyword_list})
        else:
            qs = Q()
            for keyword in keyword_list:
                qs |= Q(**{f"{filter_key}__icontains": keyword})
        return qs

    def common_filter(self, objs, return_type="list", fields=None, limit=None):
        """
        return_type: list | objects
        """
        if self.bk_biz_ids:
            objs = objs.filter(bk_biz_id__in=self.bk_biz_ids)
        if self.db_types:
            objs = objs.filter(cluster_type__in=self.cluster_types)

        if return_type == "objects":
            return objs

        fields = fields or []
        limit = limit or self.limit
        return list(objs[:limit].values(*fields))

    def filter_cluster_name(self, keyword_list: list):
        """过滤集群名"""
        qs = self.generate_filter_for_str("name", keyword_list)
        objs = Cluster.objects.filter(qs)
        return self.common_filter(objs)

    def filter_cluster_domain(self, keyword_list: list):
        """过滤集群域名"""
        qs = self.generate_filter_for_str("immute_domain", keyword_list)
        objs = Cluster.objects.filter(qs)
        return self.common_filter(objs)

    def filter_instance(self, keyword_list: list):
        """过滤实例"""
        qs = self.generate_filter_for_str("machine__ip", keyword_list)
        if self.bk_biz_ids:
            qs = Q(bk_biz_id__in=self.bk_biz_ids) & qs

        if self.db_types:
            qs = Q(cluster_type__in=self.cluster_types) & qs

        storage_objs = (
            StorageInstance.objects.prefetch_related("cluster", "machine")
            .filter(qs)
            .annotate(
                role=F("instance_role"),
                cluster_id=F("cluster__id"),
                cluster_domain=F("cluster__immute_domain"),
                ip=F("machine__ip"),
            )
        )
        proxy_objs = ProxyInstance.objects.prefetch_related("cluster", "machine").annotate(
            role=F("access_layer"),
            cluster_id=F("cluster__id"),
            cluster_domain=F("cluster__immute_domain"),
            ip=F("machine__ip"),
        )
        fields = [
            "id",
            "name",
            "bk_biz_id",
            "cluster_id",
            "cluster_domain",
            "cluster_type",
            "role",
            "ip",
            "port",
            "machine_type",
            "machine_id",
            "status",
            "phase",
        ]
        return list(storage_objs[: self.limit].values(*fields)) + list(proxy_objs[: self.limit].values(*fields))

    def filter_task(self, keyword_list: list):
        """过滤任务"""
        qs = self.generate_filter_for_str("root_id", keyword_list)
        objs = FlowTree.objects.filter(qs)

        if self.bk_biz_ids:
            objs = objs.filter(bk_biz_id__in=self.bk_biz_ids)

        # TODO: db类型任务的过滤
        return list(objs[: self.limit].values("uid", "bk_biz_id", "ticket_type", "root_id", "status", "created_by"))

    def filter_machine(self, keyword_list: list):
        """过滤主机"""
        bk_host_ids = [int(keyword) for keyword in keyword_list if isinstance(keyword, int) or keyword.isdigit()]
        if self.filter_type == FilterType.EXACT.value:
            qs = Q(ip__in=keyword_list)
            if bk_host_ids:
                qs = qs | Q(bk_host_id__in=bk_host_ids)
        else:
            qs = Q()
            for keyword in keyword_list:
                qs |= Q(ip__contains=keyword)

        if self.bk_biz_ids:
            qs = qs & Q(bk_biz_id__in=self.bk_biz_ids)

        if self.db_types:
            qs = qs & Q(cluster_type__in=self.cluster_types)

        objs = Machine.objects.filter(qs).prefetch_related(
            "storageinstance_set", "storageinstance_set__cluster", "proxyinstance_set", "proxyinstance_set__cluster"
        )

        # 解析cluster
        machines = []
        for obj in objs[: self.limit]:
            machine = model_to_dict(
                obj, ["bk_biz_id", "bk_host_id", "ip", "cluster_type", "spec_id", "bk_cloud_id", "bk_city"]
            )

            # 兼容实例未绑定集群的情况
            cluster_info = None
            for instances in [obj.storageinstance_set.all(), obj.proxyinstance_set.all()]:
                if cluster_info:
                    break
                for inst in instances:
                    if cluster_info:
                        break
                    for cluster in inst.cluster.all():
                        cluster_info = {"cluster_id": cluster.id, "cluster_dresultomain": cluster.immute_domain}

            if cluster_info is None:
                cluster_info = {"cluster_id": None, "cluster_domain": None}
            machine.update(cluster_info)
            machines.append(machine)

        return machines

    def filter_ticket(self, keyword_list: list):
        """过滤单据，单号为递增数字，采用startswith过滤"""
        ticket_ids = [int(keyword) for keyword in keyword_list if isinstance(keyword, int) or keyword.isdigit()]
        if not ticket_ids:
            return []

        if self.filter_type == FilterType.EXACT.value:
            qs = Q(id__in=ticket_ids)
        else:
            qs = Q()
            for ticket_id in ticket_ids:
                qs = qs | Q(id__startswith=ticket_id)

        if self.bk_biz_ids:
            qs = qs & Q(bk_biz_id__in=self.bk_biz_ids)
        objs = Ticket.objects.filter(qs).order_by("id")
        return list(
            objs[: self.limit].values(
                "id", "creator", "create_at", "bk_biz_id", "ticket_type", "group", "status", "is_reviewed"
            )
        )
