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
import abc
import logging
from typing import Dict, List

import attr
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry, Machine
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("root")


@attr.s
class ResourceList:
    count = attr.ib(validator=attr.validators.instance_of(int))
    data = attr.ib(validator=attr.validators.instance_of(list))


class ListRetrieveResource(abc.ABC):
    fields = [{"name": _("业务"), "key": "bk_biz_name"}]

    @classmethod
    @abc.abstractmethod
    def _list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> ResourceList:
        """查询集群列表. 具体方法在子类中实现"""

    @classmethod
    def list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> ResourceList:
        """查询集群列表，补充公共字段"""
        resource_list = cls._list_clusters(bk_biz_id, query_params, limit, offset)
        return resource_list

    @classmethod
    @abc.abstractmethod
    def _retrieve_cluster(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """查询集群详情. 具体方法在子类中实现"""

    @classmethod
    def retrieve_cluster(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """查询集群详情，补充通用字段"""
        cluster_details = cls._retrieve_cluster(bk_biz_id, cluster_id)
        cluster_details["cluster_entry_details"] = cls.query_cluster_entry_details(cluster_details)
        return cluster_details

    @classmethod
    def query_cluster_entry_details(cls, cluster_details, **kwargs):
        """查询集群访问入口详情"""
        entries = ClusterEntry.objects.filter(cluster_id=cluster_details["id"], **kwargs)
        entry_details = []
        for entry in entries:
            if entry.cluster_entry_type == ClusterEntryType.DNS:
                target_details = DnsManage(
                    bk_biz_id=cluster_details["bk_biz_id"], bk_cloud_id=cluster_details["bk_cloud_id"]
                ).get_domain(entry.entry)
            else:
                target_details = entry.detail

            entry_details.append(
                {
                    "cluster_entry_type": entry.cluster_entry_type,
                    "role": entry.role,
                    "entry": entry.entry,
                    "target_details": target_details,
                }
            )
        return entry_details

    @classmethod
    @abc.abstractmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> ResourceList:
        """查询实例列表. 具体方法在子类中实现"""

    @classmethod
    def retrieve_instance(cls, bk_biz_id: int, cluster_id: int, ip: str, port: int) -> dict:
        """查询实例详情. 具体方法可在子类中自定义"""

        instances = cls.list_instances(bk_biz_id, {"ip": ip, "port": port}, limit=1, offset=0)
        instance = instances.data[0]
        return cls._fill_instance_info(instance, cluster_id)

    @classmethod
    def _fill_instance_info(cls, instance, cluster_id):
        """填充单个实例的相关信息"""

        host_detail = Machine.get_host_info_from_cmdb(instance["bk_host_id"])
        instance.update(host_detail)

        # influxdb 目前不支持集群
        cluster = Cluster.objects.filter(id=cluster_id).last()
        instance["db_version"] = getattr(cluster, "major_version", None)

        return instance

    @classmethod
    @abc.abstractmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """查询集群拓扑图. 具体方法在子类中实现"""

    @classmethod
    def get_fields(cls) -> List[Dict[str, str]]:
        return cls.fields
