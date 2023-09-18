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
from typing import Dict

from django.db.models import F, Q, Value
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Machine
from backend.db_meta.models.group import Group, GroupInstance
from backend.db_meta.models.instance import StorageInstance
from backend.db_services.bigdata.resources.query import BigDataBaseListRetrieveResource
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER
from backend.db_services.dbbase.resources import query
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.ticket.constants import InstanceType, TicketType
from backend.ticket.models import InstanceOperateRecord
from backend.utils.time import datetime2str


class InfluxDBListRetrieveResource(BigDataBaseListRetrieveResource):
    instance_roles = []
    fields = [
        {"name": _("版本"), "key": "major_version"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建时间"), "key": "create_at"},
        {"name": _("更新人"), "key": "updater"},
        {"name": _("更新时间"), "key": "update_at"},
    ]

    # 因为influxdb不涉及集群概念，因此需要重新覆写list_instances和retrieve_instance方法，而涉及集群的方法则被全部舍弃

    @classmethod
    def retrieve_instance(cls, bk_biz_id: int, cluster_id: int, ip: str, port: int) -> dict:
        instances = cls.list_instances(bk_biz_id, {"ip": ip, "port": port}, limit=1, offset=0)
        if not instances.count:
            return {}
        instance = instances.data[0]

        host_detail = Machine.get_host_info_from_cmdb(instance["bk_host_id"])
        instance.update(host_detail)

        return instance

    @classmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        instance_filter = Q(bk_biz_id=bk_biz_id, instance_role=InstanceRole.INFLUXDB)

        if query_params.get("ip"):
            instance_filter = instance_filter & Q(machine__ip=query_params["ip"])

        if query_params.get("port"):
            instance_filter = instance_filter & Q(port=query_params["port"])

        if query_params.get("status"):
            instance_filter = instance_filter & Q(status=query_params["status"])

        if query_params.get("group_id"):
            group_id = query_params.get("group_id")
            inst_ids = list(GroupInstance.objects.filter(group_id=group_id).values_list("instance_id", flat=True))
            instance_filter = instance_filter & Q(id__in=inst_ids)

        # 此处的实例视图仅涉及 storage instance
        storage_instances_queryset = StorageInstance.objects.annotate(
            role=F("instance_role"), type=Value(InstanceType.STORAGE.value)
        ).filter(instance_filter)

        instances_queryset = storage_instances_queryset.values(
            "role",
            "port",
            "status",
            "phase",
            "creator",
            "update_at",
            "create_at",
            "name",
            "type",
            "version",
            "id",
            "machine__ip",
            "machine__bk_host_id",
            "machine__bk_cloud_id",
        ).order_by("-create_at")

        instances = instances_queryset[offset : limit + offset]
        instance_ids = [instance["id"] for instance in instances]
        bk_host_ids = [instance["machine__bk_host_id"] for instance in instances]

        # TODO: 页面上所有涉及到补充主机信息的地方需要调整bk_biz_id为dba业务（因为主机最终别转移到了dba业务）
        host_infos = ResourceQueryHelper.search_cc_hosts(bk_biz_id=env.DBA_APP_BK_BIZ_ID, role_host_ids=bk_host_ids)
        host_id__host_map = {host["bk_host_id"]: host for host in host_infos}

        # fill restart info
        restart_records = InstanceOperateRecord.objects.filter(
            instance_id__in=instance_ids,
            ticket__ticket_type=TicketType.INFLUXDB_REBOOT,
        ).order_by("create_at")
        restart_map = {record.instance_id: record.create_at for record in restart_records}

        # fill group info
        group_instances = GroupInstance.objects.filter(instance_id__in=instance_ids)
        group_ids = group_instances.values_list("group_id", flat=True)
        group_id_map = dict(group_instances.values_list("instance_id", "group_id"))
        group_name_map = dict(Group.objects.filter(id__in=group_ids).values_list("id", "name"))
        instances = [
            cls._to_instance(instance, restart_map, group_id_map, group_name_map, host_id__host_map)
            for instance in instances
        ]

        return query.ResourceList(count=instances_queryset.count(), data=instances)

    @classmethod
    def _to_instance(
        cls, instance: dict, restart_map: dict, group_id_map: dict, group_name_map: dict, host_id__host_map: dict
    ) -> dict:
        """实例序列化"""

        instance_id = instance["id"]
        restart_at = restart_map.get(instance_id, "")
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        group_id = group_id_map.get(instance_id)
        group_name = group_name_map.get(group_id)
        host_info = host_id__host_map.get(instance["machine__bk_host_id"], {})

        return {
            "id": instance_id,
            "instance_address": f"{instance['machine__ip']}{IP_PORT_DIVIDER}{instance['port']}",
            "instance_name": instance["name"],
            "bk_host_id": instance["machine__bk_host_id"],
            "mem": host_info.get("bk_mem", ""),
            "cpu": host_info.get("bk_cpu", ""),
            "disk": host_info.get("bk_disk", ""),
            "bk_cloud_id": instance["machine__bk_cloud_id"],
            "bk_cloud_name": cloud_info[str(instance["machine__bk_cloud_id"])]["bk_cloud_name"],
            "role": instance["role"],
            "status": instance["status"],
            "version": instance["version"],
            "phase": instance["phase"],
            "creator": instance["creator"],
            "group_id": group_id,
            "group_name": group_name,
            "create_at": datetime2str(instance["create_at"]),
            "update_at": datetime2str(instance["update_at"]),
            "restart_at": datetime2str(restart_at) if restart_at else restart_at,
            "operations": InstanceOperateRecord.objects.get_locking_operations(instance["id"]),
        }
