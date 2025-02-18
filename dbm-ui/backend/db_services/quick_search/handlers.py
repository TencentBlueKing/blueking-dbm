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
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Concat
from django.forms import model_to_dict

from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, ProxyInstance, StorageInstance
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.db_services.quick_search import constants
from backend.db_services.quick_search.constants import FilterType, ResourceType
from backend.flow.models import FlowTree
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.string import split_str_to_list


class QSearchHandler(object):
    def __init__(self, bk_biz_ids=None, db_types=None, resource_types=None, filter_type=None, limit=None):
        self.bk_biz_ids = bk_biz_ids
        self.db_types = db_types
        self.resource_types = resource_types
        self.filter_type = filter_type
        self.limit = limit or constants.DEFAULT_LIMIT

        # db_type -> cluster_type
        self.cluster_types = []
        if self.db_types:
            for db_type in self.db_types:
                self.cluster_types.extend(ClusterType.db_type_to_cluster_types(db_type))

    def search(self, keyword: str):
        result = {}
        target_resource_types = self.resource_types or ResourceType.get_values()
        keyword_list = split_str_to_list(keyword)
        # 当搜索关键字数量大于一定数量时，只允许精确搜索（模糊搜索查询效率太差）
        if len(keyword_list) > constants.CONTAINS_SEARCH_MAX_SIZE:
            self.filter_type = FilterType.EXACT.value

        for target_resource_type in target_resource_types:
            filter_func = getattr(self, f"filter_{target_resource_type}", None)
            if callable(filter_func):
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

    def generate_filter_for_domain(self, filter_key, keyword_list):
        """
        为域名类型生成过滤函数
        """
        qs = Q()
        domains = []
        for keyword in keyword_list:
            try:
                domain, _ = keyword.split(":")
            except ValueError:
                domain, _ = keyword, None

            if self.filter_type == FilterType.EXACT.value:
                domains.append(domain)
            else:
                qs |= Q(**{f"{filter_key}__icontains": domain})

        if self.filter_type == FilterType.EXACT.value:
            qs = Q(**{f"{filter_key}__in": domains})
        return qs

    def generate_filter_for_ip_port(self, filter_key, keyword_list):
        """
        为ip:port实例生成过滤函数
        """
        qs = Q()
        ip_list = []
        ports = []
        for keyword in keyword_list:
            try:
                ip, port = keyword.split(":")
                ports.append(port)
            except ValueError:
                ip, port = keyword, None
            ip_list.append(ip)

            ip_filter_key = filter_key
            port_filter_key = "port"
            if port:
                qs |= Q(**{ip_filter_key: ip, port_filter_key: port})
                if self.filter_type == FilterType.CONTAINS.value:
                    qs |= Q(**{"ip_port__contains": keyword})
                else:
                    qs |= Q(**{ip_filter_key: ip, port_filter_key: port})
            else:
                if self.filter_type == FilterType.CONTAINS.value:
                    qs |= Q(**{f"{filter_key}__contains": ip})

        # 精确搜索时，不用 Q | Q 的方式，查询效率较差
        if not ports and self.filter_type == FilterType.EXACT.value:
            qs = Q(**{f"{filter_key}__in": ip_list})

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

    def supplementary_fields(self, objects_list: list):
        """补充 主dba和db类型字段"""
        for object in objects_list:
            # 将 db_type 补充到对象中
            object["db_type"] = ClusterType.cluster_type_to_db_type(object["cluster_type"])

            # 获取dba人员  # DBA 人员获取优先级： 业务 > 平台 > 默认空值
            dba_list = DBAdministrator.list_biz_admins(bk_biz_id=object["bk_biz_id"])
            dba_content = next((dba for dba in dba_list if dba["db_type"] == object["db_type"]))
            object["dba"] = dba_content["users"][0] if dba_content["users"] else None
            object["is_show_dba"] = dba_content["is_show"]
        return objects_list

    def filter_cluster_name(self, keyword_list: list):
        """过滤集群名"""
        qs = self.generate_filter_for_str("name", keyword_list)
        objs = Cluster.objects.filter(qs)
        return self.common_filter(objs)

    def filter_entry(self, keyword_list: list):
        """过滤集群访问入口"""
        qs = self.generate_filter_for_domain("entry", keyword_list)

        if self.bk_biz_ids:
            qs = Q(bk_biz_id__in=self.bk_biz_ids) & qs

        if self.db_types:
            qs = Q(cluster_type__in=self.cluster_types) & qs

        common_fields = {
            "cluster_type": F("cluster__cluster_type"),
            "immute_domain": F("cluster__immute_domain"),
            "bk_biz_id": F("cluster__bk_biz_id"),
            "cluster_status": F("cluster__status"),
            "region": F("cluster__region"),
            "disaster_tolerance_level": F("cluster__disaster_tolerance_level"),
            "major_version": F("cluster__major_version"),
        }
        fields = [
            "id",
            "cluster_entry_type",
            "entry",
            "cluster_id",
            "role",
            *common_fields.keys(),
        ]
        objs = (
            ClusterEntry.objects.filter(qs)
            .select_related("cluster")
            .annotate(**common_fields)
            .values(*fields)[: self.limit]
        )
        return self.supplementary_fields(list(objs))

    def filter_instance(self, keyword_list: list):
        """过滤实例"""
        qs = self.generate_filter_for_ip_port("machine__ip", keyword_list)
        if self.bk_biz_ids:
            qs = Q(bk_biz_id__in=self.bk_biz_ids) & qs

        if self.db_types:
            qs = Q(cluster_type__in=self.cluster_types) & qs

        common_fields = {
            "cluster_id": F("cluster__id"),
            "cluster_domain": F("cluster__immute_domain"),
            "cluster_name": F("cluster__name"),
            "cluster_alias": F("cluster__alias"),
            "major_version": F("cluster__major_version"),
            "ip": F("machine__ip"),
            "bk_host_id": F("machine__bk_host_id"),
            "bk_cloud_id": F("machine__bk_cloud_id"),
            "bk_idc_area": F("machine__bk_idc_area"),
            "bk_idc_name": F("machine__bk_idc_name"),
            "bk_sub_zone": F("machine__bk_sub_zone"),
            "bk_os_name": F("machine__bk_os_name"),
            "bk_rack_id": F("machine__bk_rack_id"),
            "bk_svr_device_cls_name": F("machine__bk_svr_device_cls_name"),
            "ip_port": Concat("machine__ip", Value(":"), "port", output_field=CharField()),
        }
        fields = [
            "id",
            "name",
            "bk_biz_id",
            "cluster_type",
            "role",
            "port",
            "machine_type",
            "machine_id",
            "status",
            "phase",
            *common_fields.keys(),
        ]
        storage_objs = (
            StorageInstance.objects.prefetch_related("cluster", "machine")
            .annotate(role=F("instance_role"), **common_fields)
            .filter(qs)
            .values(*fields)[: self.limit]
        )
        proxy_objs = (
            ProxyInstance.objects.prefetch_related("cluster", "machine")
            .annotate(role=F("access_layer"), **common_fields)
            .filter(qs)
            .values(*fields)[: self.limit]
        )

        return self.supplementary_fields(list(storage_objs) + list(proxy_objs))

    def filter_task(self, keyword_list: list):
        """过滤任务"""
        objs = FlowTree.objects.filter(root_id__in=keyword_list)

        if self.bk_biz_ids:
            objs = objs.filter(bk_biz_id__in=self.bk_biz_ids)

        results = list(
            objs[: self.limit].values(
                "uid", "bk_biz_id", "ticket_type", "root_id", "status", "created_by", "created_at"
            )
        )
        # 补充 ticket_type_display
        for ticket in results:
            ticket["ticket_type_display"] = TicketType.get_choice_label(ticket["ticket_type"])
        return results

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
                        cluster_info = {"cluster_id": cluster.id, "cluster_domain": cluster.immute_domain}

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
        tickets = Ticket.objects.filter(qs).order_by("id")
        results = list(
            tickets[: self.limit].values(
                "id", "creator", "create_at", "bk_biz_id", "ticket_type", "group", "status", "is_reviewed"
            )
        )
        # 补充 ticket_type_display
        for ticket in results:
            ticket["ticket_type_display"] = TicketType.get_choice_label(ticket["ticket_type"])
        return results

    def filter_resource_pool(self, keyword_list: list):
        return ResourceHandler().resource_list({"hosts": keyword_list, "limit": self.limit, "offset": 0})["results"]
