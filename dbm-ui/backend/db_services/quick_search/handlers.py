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
import re

from django.db.models import CharField, F, Prefetch, Q, Value
from django.db.models.functions import Concat

from backend.configuration.models import DBAdministrator
from backend.constants import DOMAIN_PATTERN
from backend.db_dirty.models import DirtyMachine
from backend.db_dirty.serializers import ListMachinePoolSerializer
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import AppCache, Cluster, ClusterEntry, DBModule, ProxyInstance, Spec, StorageInstance
from backend.db_meta.models.city_map import BKSubzone
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.quick_search import constants
from backend.db_services.quick_search.constants import FilterType, ResourceType
from backend.flow.models import FlowTree
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.permission import Permission
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord, Ticket
from backend.utils.string import split_str_to_list


class QSearchHandler(object):
    def __init__(self, bk_biz_ids=None, db_types=None, resource_types=None, filter_type=None, limit=None, user=None):
        self.db_types = db_types
        self.resource_types = resource_types
        self.filter_type = filter_type
        self.limit = limit or constants.DEFAULT_LIMIT
        self.user = user

        # db_type -> cluster_type
        self.cluster_types = []
        if self.db_types:
            for db_type in self.db_types:
                self.cluster_types.extend(ClusterType.db_type_to_cluster_types(db_type))

        self.bk_biz_ids, self.permission = self.get_permission_biz_ids(bk_biz_ids, self.filter_type)

    def search(self, keyword: str):
        result = {}
        target_resource_types = self.resource_types or ResourceType.get_values()
        keyword_list = split_str_to_list(keyword)
        # 当搜索关键字数量大于一定数量时，只允许精确搜索（模糊搜索查询效率太差）
        if len(keyword_list) > constants.CONTAINS_SEARCH_MAX_SIZE:
            self.filter_type = FilterType.EXACT.value

        for target_resource_type in target_resource_types:
            filter_func = getattr(self, f"filter_{target_resource_type}", None)
            if not self.permission and target_resource_type != ResourceType.MACHINE.value:
                result[target_resource_type] = []
            elif callable(filter_func):
                result[target_resource_type] = filter_func(keyword_list)

        return result

    def get_permission_biz_ids(self, bk_biz_ids, filter_type):
        """获取有权限的业务id"""
        bk_biz_ids = bk_biz_ids or []
        all_bk_biz_ids = AppCache.objects.all().values_list("bk_biz_id", flat=True)
        permission = Permission(username=self.user, request={}).policy_query(
            action=ActionEnum.DB_MANAGE, obj_list=all_bk_biz_ids
        )
        if filter_type == FilterType.EXACT.value:
            return bk_biz_ids or all_bk_biz_ids, all_bk_biz_ids
        if len(permission) != len(all_bk_biz_ids):
            bk_biz_ids = (
                list(set(bk_biz_ids) & set(permission)) if bk_biz_ids and permission else bk_biz_ids or permission
            )
        return bk_biz_ids, permission

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

            # 如果不是有效的域名，则直接将整个字符串作为域名
            if not re.compile(DOMAIN_PATTERN).match(domain):
                domain = keyword

            if self.filter_type == FilterType.EXACT.value:
                domains.append(domain)
            else:
                qs |= Q(**{f"{filter_key}__icontains": domain})

        if self.filter_type == FilterType.EXACT.value:
            qs = Q(**{f"{filter_key}__in": domains})
        return qs

    def generate_filter_for_ip_port(self, filter_key, keyword_list, not_port=False):
        """
        为ip:port实例生成过滤函数
        """
        qs = Q()
        ip_list = []
        ports = []
        for keyword in keyword_list:
            try:
                ip, port = keyword.split(":")
                # 端口必须是数字，否则视为无效的 ip:port 格式
                if port and not port.isdigit():
                    ip, port = keyword, None
            except ValueError:
                ip, port = keyword, None
            ip_list.append(ip)

            ip_filter_key = filter_key
            port_filter_key = "port"
            if port:
                ports.append(port)
                query_filter = {ip_filter_key: ip}
                if not not_port:
                    query_filter[port_filter_key] = int(port)
                qs |= Q(**query_filter)
                if self.filter_type == FilterType.CONTAINS.value and not not_port:
                    qs |= Q(**{"ip_port__contains": keyword})

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

        limit = limit or self.limit

        if return_type == "objects":
            return objs[:limit]

        fields = fields or []
        return list(objs[:limit].values(*fields))

    def supplementary_fields(self, objects_list: list):
        """补充 主dba和db类型字段"""
        for object in objects_list:
            # 将 db_type 补充到对象中
            object["db_type"] = ClusterType.cluster_type_to_db_type(object["cluster_type"])

            # 获取dba人员  # DBA 人员获取优先级： 业务 > 平台 > 默认空值
            dba_list = DBAdministrator.list_biz_admins(bk_biz_id=object["bk_biz_id"])
            dba_content = next(
                (dba for dba in dba_list if dba["db_type"] == object["db_type"]), {"users": [], "is_show": True}
            )
            object["dba"] = dba_content["users"][0] if dba_content["users"] else None
            object["is_show_dba"] = dba_content["is_show"]
        return objects_list

    def filter_cluster_name(self, keyword_list: list):
        """过滤集群名"""
        qs = self.generate_filter_for_str("name", keyword_list)
        objs = Cluster.objects.filter(qs)
        return self.common_filter(objs)

    def filter_cluster(self, keyword_list: list):
        """过滤集群，支持通过域名或 标签键 / 标签:标签值 格式过滤"""
        domain_qs = Q()
        tag_qs = Q()

        for keyword in keyword_list:
            # 判断是否为 "键:值" 格式（包含冒号）
            is_key_value_format = ":" in keyword

            if is_key_value_format:
                # 尝试按 标签:标签值 格式解析
                tag_key, _, tag_value = keyword.partition(":")
                if tag_key and tag_value:
                    # 包含冒号时，无论模糊/精确模式，都按"键:值"精确匹配
                    tag_qs |= Q(tags__key=tag_key, tags__value=tag_value)
                    continue

            # 不包含冒号的关键字，或冒号解析失败，按正常逻辑处理
            # 标签键 / 标签值过滤
            if self.filter_type == FilterType.EXACT.value:
                tag_qs |= Q(tags__key=keyword) | Q(tags__value=keyword)
            else:
                tag_qs |= Q(tags__key__icontains=keyword) | Q(tags__value__icontains=keyword)

            # 域名过滤
            try:
                domain, _ = keyword.split(":")
            except ValueError:
                domain, _ = keyword, None

            # 如果不是有效的域名，则直接将整个字符串作为域名
            if not re.compile(DOMAIN_PATTERN).match(domain):
                domain = keyword

            if self.filter_type == FilterType.EXACT.value:
                domain_qs |= Q(immute_domain=domain)
            else:
                domain_qs |= Q(immute_domain__icontains=domain)

        qs = domain_qs | tag_qs
        objs = Cluster.objects.filter(qs).distinct()
        # 使用objects模式获取QuerySet，再手动预取关联数据并序列化
        clusters = self.common_filter(
            objs.prefetch_related(
                Prefetch(
                    "clusterentry_set",
                    queryset=ClusterEntry.objects.select_related("forward_to"),
                    to_attr="entries",
                ),
                "tags",
            ),
            return_type="objects",
        )
        return self._serialize_clusters(clusters)

    def _serialize_clusters(self, clusters):
        """序列化集群对象，包含cluster_entry和tags"""
        if not clusters:
            return []

        cluster_ids = [c.id for c in clusters]
        cluster_types = list({c.cluster_type for c in clusters})
        bk_biz_ids = list({c.bk_biz_id for c in clusters})

        # 批量预取关联数据
        cluster_entry_map = ClusterEntry.get_entries_map(
            ClusterEntry.objects.filter(cluster_id__in=cluster_ids).select_related("cluster")
        )
        db_module_names_map = {
            m["db_module_id"]: m["alias_name"]
            for m in DBModule.objects.filter(cluster_type__in=cluster_types).values("db_module_id", "alias_name")
        }
        cluster_operate_records_map = ClusterOperateRecord.get_cluster_records_map(cluster_ids)
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        cluster_zone_map = BKSubzone.get_subzone_map(get_cache=True)
        biz_info_map = {biz.bk_biz_id: biz for biz in AppCache.objects.filter(bk_biz_id__in=bk_biz_ids)}

        # 预取集群规格信息
        db_types = set(ClusterType.cluster_type_to_db_type(ct) for ct in cluster_types)
        remote_spec_map = {s.spec_id: s for s in Spec.objects.filter(spec_cluster_type__in=db_types)}

        result = []
        for cluster in clusters:
            # 处理 cluster_entry 和 dns_to_clb
            cluster_entry = []
            dns_to_clb = False
            for entry in getattr(cluster, "entries", []):
                cluster_entry.append(
                    {"cluster_entry_type": entry.cluster_entry_type, "entry": entry.entry, "role": entry.role}
                )
                if (
                    not dns_to_clb
                    and entry.cluster_entry_type == ClusterEntryType.DNS.value
                    and entry.entry == cluster.immute_domain
                    and entry.forward_to is not None
                    and entry.forward_to.cluster_entry_type == ClusterEntryType.CLB.value
                ):
                    dns_to_clb = True

            # 补充集群规格信息
            cluster_spec = None
            storage = cluster.storageinstance_set.first()
            if storage:
                cluster_spec_id = storage.machine.spec_id
                cluster_spec = remote_spec_map.get(cluster_spec_id)

            biz_info = biz_info_map.get(cluster.bk_biz_id)
            bk_cloud_name = cloud_info.get(str(cluster.bk_cloud_id), {}).get("bk_cloud_name", "")
            cluster_entry_map_value = cluster_entry_map.get(cluster.id, {})
            cluster_zone_list = cluster.zone_list or []

            cluster_data = {
                "id": cluster.id,
                "db_type": ClusterType.cluster_type_to_db_type(cluster.cluster_type),
                "phase": cluster.phase,
                "phase_name": cluster.get_phase_display(),
                "status": cluster.status,
                "operations": cluster_operate_records_map.get(cluster.id, []),
                "dns_to_clb": dns_to_clb,
                "cluster_time_zone": cluster.time_zone,
                "cluster_name": cluster.name,
                "cluster_alias": cluster.alias,
                "cluster_access_port": cluster.access_port,
                "cluster_stats": {},
                "cluster_type": cluster.cluster_type,
                "cluster_type_name": str(ClusterType.get_choice_label(cluster.cluster_type)),
                "cluster_subzones": [cluster_zone_map.get(str(zone), "") for zone in cluster_zone_list],
                "cluster_subzone_ids": cluster_zone_list,
                "disaster_tolerance_level": cluster.disaster_tolerance_level,
                "master_domain": cluster_entry_map_value.get("master_domain", ""),
                "slave_domain": cluster_entry_map_value.get("slave_domain", ""),
                "cluster_entry": cluster_entry,
                "bk_biz_id": cluster.bk_biz_id,
                "bk_biz_name": biz_info.bk_biz_name if biz_info else "",
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_cloud_name": bk_cloud_name,
                "major_version": cluster.major_version,
                "region": cluster.region,
                "city": cluster.region,
                "db_module_name": db_module_names_map.get(cluster.db_module_id, ""),
                "db_module_id": cluster.db_module_id,
                "creator": cluster.creator,
                "updater": cluster.updater,
                "create_at": cluster.create_at,
                "update_at": cluster.update_at,
                "cluster_spec": cluster_spec.to_dict() if cluster_spec else None,
                "tags": [tag.desc for tag in cluster.tags.all()],
                "zone_list": cluster.zone_list,
            }
            result.append(cluster_data)
        return self.supplementary_fields(result)

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
        qs = self.generate_filter_for_ip_port("ip", keyword_list, not_port=True)
        objs = DirtyMachine.objects.filter(qs)[: self.limit]
        machine_data = ListMachinePoolSerializer(objs, many=True).data
        # 补充主机agent状态
        ResourceQueryHelper.fill_agent_status(machine_data, fill_key="agent_status")

        return machine_data

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
