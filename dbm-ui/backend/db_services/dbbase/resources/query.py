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
from typing import Dict, List, Union

import attr
from django.db.models import Q
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, ProxyInstance, StorageInstance
from backend.flow.utils.dns_manage import DnsManage
from backend.utils.excel import ExcelHandler


@attr.s
class ResourceList:
    count = attr.ib(validator=attr.validators.instance_of(int))
    data = attr.ib(validator=attr.validators.instance_of(list))


class ListRetrieveResource(abc.ABC):
    fields = [{"name": _("业务"), "key": "bk_biz_name"}]
    cluster_types = []

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

    @classmethod
    def export_cluster(cls, bk_biz_id: int, cluster_ids: list) -> HttpResponse:
        # 获取所有符合条件的集群对象
        clusters = Cluster.objects.prefetch_related(
            "storageinstance_set", "proxyinstance_set", "storageinstance_set__machine", "proxyinstance_set__machine"
        ).filter(bk_biz_id=bk_biz_id, cluster_type__in=cls.cluster_types)
        if cluster_ids:
            clusters = clusters.filter(id__in=cluster_ids)

        # 初始化用于存储Excel数据的字典列表
        headers = [
            {"id": "cluster_id", "name": _("集群 ID")},
            {"id": "cluster_name", "name": _("集群名称")},
            {"id": "cluster_alias", "name": _("集群别名")},
            {"id": "cluster_type", "name": _("集群类型")},
            {"id": "master_domain", "name": _("主域名")},
            {"id": "major_version", "name": _("主版本")},
            {"id": "region", "name": _("地域")},
            {"id": "disaster_tolerance_level", "name": _("容灾级别")},
        ]

        def fill_instances_to_cluster_info(
            _cluster_info: Dict, instances: List[Union[StorageInstance, ProxyInstance]]
        ):
            """
            把实例信息填充到集群信息中
            """
            for ins in instances:
                # 获取存储实例所属角色
                role = ins.instance_role

                # 如果该角色已经存在于集群信息字典中，则添加新的IP和端口；否则，更新字典的值
                if role in cluster_info:
                    cluster_info[role] += f"\n{ins.machine.ip}#{ins.port}"
                else:
                    if role not in headers:
                        headers.append({"id": role, "name": role})
                    cluster_info[role] = f"{ins.machine.ip}#{ins.port}"

        # 遍历所有的集群对象
        data_list = []
        for cluster in clusters:
            # 创建一个空字典来保存当前集群的信息
            cluster_info = {
                "cluster_id": cluster.id,
                "cluster_name": cluster.name,
                "cluster_alias": cluster.alias,
                "cluster_type": cluster.cluster_type,
                "master_domain": cluster.immute_domain,
                "major_version": cluster.major_version,
                "region": cluster.region,
                "disaster_tolerance_level": cluster.get_disaster_tolerance_level_display(),
            }
            fill_instances_to_cluster_info(cluster_info, cluster.storageinstance_set.all())
            fill_instances_to_cluster_info(cluster_info, cluster.proxyinstance_set.all())

            # 将当前集群的信息追加到data_list列表中
            data_list.append(cluster_info)

        wb = ExcelHandler.serialize(data_list, headers=headers, match_header=True)
        return ExcelHandler.response(wb, f"biz_{bk_biz_id}_instances.xlsx")

    @classmethod
    def export_instance(cls, bk_biz_id: int, bk_host_ids: list) -> HttpResponse:
        # 查询实例
        query_condition = Q(bk_biz_id=bk_biz_id)
        if bk_host_ids:
            query_condition = query_condition & Q(machine__bk_host_id__in=bk_host_ids)
        storages = StorageInstance.objects.prefetch_related("machine", "machine__bk_city", "cluster").filter(
            query_condition
        )
        proxies = ProxyInstance.objects.prefetch_related("machine", "machine__bk_city", "cluster").filter(
            query_condition
        )
        headers = [
            {"id": "bk_host_id", "name": _("主机 ID")},
            {"id": "bk_cloud_id", "name": _("云区域 ID")},
            {"id": "ip", "name": _("IP")},
            {"id": "ip_port", "name": _("IP 端口")},
            {"id": "instance_role", "name": _("实例角色")},
            {"id": "bk_idc_city_name", "name": _("城市")},
            {"id": "bk_idc_name", "name": _("机房")},
            {"id": "cluster_id", "name": _("集群 ID")},
            {"id": "cluster_name", "name": _("集群名称")},
            {"id": "cluster_alias", "name": _("集群别名")},
            {"id": "cluster_type", "name": _("集群类型")},
            {"id": "master_domain", "name": _("主域名")},
            {"id": "major_version", "name": _("主版本")},
        ]
        # 插入数据
        data_list = []
        for instances in [storages, proxies]:
            for ins in instances:
                for cluster in ins.cluster.all():
                    data_list.append(
                        {
                            "bk_host_id": ins.machine.bk_host_id,
                            "bk_cloud_id": ins.machine.bk_cloud_id,
                            "ip": ins.machine.ip,
                            "ip_port": ins.ip_port,
                            "instance_role": ins.instance_role,
                            "bk_idc_city_name": ins.machine.bk_city.bk_idc_city_name,
                            "bk_idc_name": ins.machine.bk_idc_name,
                            "cluster_id": cluster.id,
                            "cluster_name": cluster.name,
                            "cluster_alias": cluster.alias,
                            "cluster_type": cluster.cluster_type,
                            "master_domain": cluster.immute_domain,
                            "major_version": cluster.major_version,
                        }
                    )

        wb = ExcelHandler.serialize(data_list, headers=headers, match_header=True)
        return ExcelHandler.response(wb, f"biz_{bk_biz_id}_instances.xlsx")
