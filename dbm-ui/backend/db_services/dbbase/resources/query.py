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
import operator
from functools import reduce
from typing import Any, Callable, Dict, List, Tuple, Union

import attr
from django.db.models import F, Prefetch, Q, QuerySet
from django.http import HttpResponse
from django.utils.http import urlquote
from django.utils.translation import gettext_lazy as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.enums.comm import SystemTagEnum
from backend.db_meta.models import AppCache, Cluster, ClusterEntry, DBModule, Machine, ProxyInstance, StorageInstance
from backend.db_services.dbbase.instances.handlers import InstanceHandler
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.utils.dns_manage import DnsManage
from backend.ticket.models import ClusterOperateRecord
from backend.utils.excel import ExcelHandler
from backend.utils.time import datetime2str


@attr.s
class ResourceList:
    count = attr.ib(validator=attr.validators.instance_of(int))
    data = attr.ib(validator=attr.validators.instance_of(list))


class CommonQueryResourceMixin(abc.ABC):
    """集群通用的查询方法封装类"""

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

    @staticmethod
    def common_query_cluster(bk_biz_id: int, cluster_types: list, cluster_ids: list) -> Tuple[List[Dict], List[Dict]]:
        """集群的通用属性查询"""
        # 获取所有符合条件的集群对象
        clusters = Cluster.objects.prefetch_related(
            "storageinstance_set", "proxyinstance_set", "storageinstance_set__machine", "proxyinstance_set__machine"
        ).filter(bk_biz_id=bk_biz_id, cluster_type__in=cluster_types)
        if cluster_ids:
            clusters = clusters.filter(id__in=cluster_ids)

        cluster_entry_map = ClusterEntry.get_cluster_entry_map(cluster_ids=list(clusters.values_list("id", flat=True)))

        # 初始化用于存储Excel数据的字典列表
        headers = [
            {"id": "cluster_id", "name": _("集群 ID")},
            {"id": "cluster_name", "name": _("集群名称")},
            {"id": "cluster_alias", "name": _("集群别名")},
            {"id": "cluster_type", "name": _("集群类型")},
            {"id": "master_domain", "name": _("主域名")},
            {"id": "slave_domain", "name": _("从域名")},
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
                    role_header = {"id": role, "name": role}
                    if role_header not in headers:
                        headers.append(role_header)
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
                "slave_domain": cluster_entry_map[cluster.id].get("slave_domain", ""),
                "major_version": cluster.major_version,
                "region": cluster.region,
                "disaster_tolerance_level": cluster.get_disaster_tolerance_level_display(),
            }
            fill_instances_to_cluster_info(cluster_info, cluster.storageinstance_set.all())
            fill_instances_to_cluster_info(cluster_info, cluster.proxyinstance_set.all())

            # 将当前集群的信息追加到data_list列表中
            data_list.append(cluster_info)

        return headers, data_list

    @staticmethod
    def common_query_instance(bk_biz_id: int, cluster_types: list, bk_host_ids: list) -> Tuple[List[Dict], List[Dict]]:
        """实例通用属性查询"""
        query_condition = Q(bk_biz_id=bk_biz_id, cluster_type__in=cluster_types)
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

        return headers, data_list

    @classmethod
    def export_cluster(cls, bk_biz_id: int, cluster_ids: list) -> HttpResponse:
        """集群通用属性导出"""
        headers, data_list = cls.common_query_cluster(bk_biz_id, cls.cluster_types, cluster_ids)

        biz_name = AppCache.get_biz_name(bk_biz_id)
        db_type = ClusterType.cluster_type_to_db_type(cls.cluster_types[0])
        wb = ExcelHandler.serialize(data_list, headers=headers, match_header=True)

        return ExcelHandler.response(
            wb, urlquote(_("{export_prefix}集群列表.xlsx").format(export_prefix=f"{biz_name}[{bk_biz_id}]{db_type}"))
        )

    @classmethod
    def export_instance(cls, bk_biz_id: int, bk_host_ids: list) -> HttpResponse:
        """实例通用属性导出"""
        headers, data_list = cls.common_query_instance(bk_biz_id, cls.cluster_types, bk_host_ids)

        biz_name = AppCache.get_biz_name(bk_biz_id)
        db_type = ClusterType.cluster_type_to_db_type(cls.cluster_types[0])
        wb = ExcelHandler.serialize(data_list, headers=headers, match_header=True)

        return ExcelHandler.response(
            wb, urlquote(_("{export_prefix}实例列表.xlsx").format(export_prefix=f"{biz_name}[{bk_biz_id}]{db_type}"))
        )

    @classmethod
    def get_temporary_cluster_info(cls, cluster, ticket_type):
        """如果当前集群是临时集群，则补充临时集群相关信息。注: 会存在N+1问题，不过临时集群较少先忽略"""
        if not cluster.tag_set.filter(name=SystemTagEnum.TEMPORARY.value).exists():
            return {}
        record = ClusterOperateRecord.objects.filter(cluster_id=cluster.id, ticket__ticket_type=ticket_type).first()
        # 临时集群名称的构造规则是: {cluster_name}_{20201212}_{ticket_id}
        source_cluster_name = cluster.name.rsplit("-", 2)[0]
        # 获取回档源集群信息，如果源集群已被卸载，则忽略
        try:
            source_cluster = Cluster.objects.get(
                bk_biz_id=cluster.bk_biz_id, cluster_type=cluster.cluster_type, name=source_cluster_name
            )
            domain = source_cluster.immute_domain
        except Cluster.DoesNotExist:
            domain = ""

        temporary_info = {"source_cluster": domain, "ticket_id": record.ticket.id}
        return temporary_info


class BaseListRetrieveResource(CommonQueryResourceMixin):
    """集群基础视图接口的封装类框架"""

    fields = [{"name": _("业务"), "key": "bk_biz_name"}]
    cluster_types = []

    @classmethod
    @abc.abstractmethod
    def _list_clusters(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        filter_func_map: Dict[str, Callable] = None,
        **kwargs,
    ) -> ResourceList:
        """查询集群列表. 具体方法在子类中实现"""
        raise NotImplementedError

    @classmethod
    def list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> ResourceList:
        """查询集群列表，补充公共字段"""
        resource_list = cls._list_clusters(bk_biz_id, query_params, limit, offset)
        return resource_list

    @classmethod
    def _retrieve_cluster(cls, cluster_details: dict, cluster_id: int) -> dict:
        """补充集群详情信息，子类可继承实现"""
        cluster_details["cluster_entry_details"] = cls.query_cluster_entry_details(cluster_details)
        return cluster_details

    @classmethod
    def retrieve_cluster(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """查询集群详情"""
        cluster_details = cls.list_clusters(bk_biz_id, {"id": cluster_id}, limit=1, offset=0).data[0]
        return cls._retrieve_cluster(cluster_details, cluster_id)

    @classmethod
    @abc.abstractmethod
    def _list_instances(
        cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int, filter_params_map: dict = None, **kwargs
    ) -> ResourceList:
        """查询实例列表. 具体方法在子类中实现"""
        raise NotImplementedError

    @classmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> ResourceList:
        """查询实例列表，补充公共字段"""
        resource_list = cls._list_instances(bk_biz_id, query_params, limit, offset)
        return resource_list

    @classmethod
    def retrieve_instance(cls, bk_biz_id: int, cluster_id: int, ip: str, port: int) -> dict:
        """查询实例详情. 具体方法可在子类中自定义"""
        instance_details = cls.list_instances(bk_biz_id, {"ip": ip, "port": port}, limit=1, offset=0).data[0]
        return cls._retrieve_instance(instance_details, cluster_id)

    @classmethod
    def _retrieve_instance(cls, instance, cluster_id):
        """填充单个实例的相关信息"""
        host_detail = Machine.get_host_info_from_cmdb(instance["bk_host_id"])
        instance.update(host_detail)
        # influxdb 目前不支持集群
        cluster = Cluster.objects.filter(id=cluster_id).last()
        instance["db_version"] = getattr(cluster, "major_version", None)
        return instance

    @classmethod
    def list_machines(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> ResourceList:
        """查询机器列表"""
        resource_list = cls._list_machines(bk_biz_id, query_params, limit, offset)
        return resource_list

    @classmethod
    @abc.abstractmethod
    def _list_machines(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        **kwargs,
    ) -> ResourceList:
        """查询机器列表. 具体方法在子类中实现"""
        raise NotImplementedError

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """查询集群拓扑图. 具体方法在子类中实现"""
        return {}

    @classmethod
    def get_fields(cls) -> List[Dict[str, str]]:
        return cls.fields


class ListRetrieveResource(BaseListRetrieveResource):
    """集群基础视图接口的封装类实现，组件的相关视图接口一般继承此类实现"""

    @classmethod
    def _list_clusters(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        filter_func_map: Dict[str, Callable] = None,
        **kwargs,
    ) -> ResourceList:
        """
        查询集群信息
        @param bk_biz_id: 业务 ID
        @param query_params: 查询条件. 通过 .serializers.ListResourceSLZ 完成数据校验
        @param limit: 分页查询, 每页展示的数目
        @param offset: 分页查询, 当前页的偏移数
        @param filter_params_map: 过滤参数map
        @param filter_func_map: 过滤函数map，每个函数必须接受query_params和cluster、proxy、storage三个query参数
        """
        query_filters = Q(bk_biz_id=bk_biz_id, cluster_type__in=cls.cluster_types)
        proxy_queryset = ProxyInstance.objects.filter(query_filters)
        storage_queryset = StorageInstance.objects.filter(query_filters)

        # 定义内置的过滤参数map
        filter_params_map = filter_params_map or {}
        inner_filter_params_map = {
            "id": Q(id=query_params.get("id")),
            "name": (
                Q(name__in=query_params.get("name", "").split(","))
                | Q(alias__in=query_params.get("name", "").split(","))
            ),
            # 版本
            "major_version": Q(major_version__in=query_params.get("major_version", "").split(",")),
            # 地域
            "region": Q(region__in=query_params.get("region", "").split(",")),
            "cluster_ids": Q(id__in=query_params.get("cluster_ids")),
            "creator": Q(creator__icontains=query_params.get("creator")),
            # 所属DB模块
            "db_module_id": Q(db_module_id__in=query_params.get("db_module_id", "").split(",")),
            # 管控区域
            "bk_cloud_id": Q(bk_cloud_id__in=query_params.get("bk_cloud_id", "").split(",")),
            # 状态
            "status": Q(status__in=query_params.get("status", "").split(",")),
            # 时区
            "time_zone": Q(time_zone=query_params.get("time_zone", "").split(",")),
            # 域名精确查询，主要用于工具箱手动填入域名查询
            "exact_domain": Q(immute_domain=query_params.get("exact_domain")),
            # 域名
            "domain": Q(
                clusterentry__cluster_entry_type=ClusterEntryType.DNS.value,
                clusterentry__entry__in=query_params.get("domain", "").split(","),
            ),
        }
        filter_params_map.update(inner_filter_params_map)

        # 通过基础过滤参数进行cluster过滤
        for param in filter_params_map:
            if query_params.get(param):
                query_filters &= filter_params_map[param]
        cluster_queryset = Cluster.objects.filter(query_filters).order_by("create_at")

        #  部署时间表头排序
        if query_params.get("ordering"):
            cluster_queryset = cluster_queryset.order_by(query_params.get("ordering"))

        def filter_inst_queryset(_cluster_queryset, _proxy_queryset, _storage_queryset, _filters):
            # 注意这里用新的变量获取过滤后的queryset，不要用原queryset过滤，会影响后续集群关联实例的获取
            _proxy_filter_queryset = _proxy_queryset.filter(_filters)
            _storage_filter_queryset = _storage_queryset.filter(_filters)
            # 这里如果不用distinct，会查询出重复记录。TODO: 排查查询重复记录的原因
            _cluster_queryset = _cluster_queryset.filter(
                Q(proxyinstance__in=_proxy_filter_queryset) | Q(storageinstance__in=_storage_filter_queryset)
            ).distinct()
            return _cluster_queryset

        # ip筛选
        def filter_ip_func(_query_params, _cluster_queryset, _proxy_queryset, _storage_queryset):
            """实例过滤ip"""
            filter_ip = Q(machine__ip__in=_query_params.get("ip").split(","))
            _cluster_queryset = filter_inst_queryset(_cluster_queryset, _proxy_queryset, _storage_queryset, filter_ip)
            return _cluster_queryset

        # 实例筛选
        def filter_instance_func(_query_params, _cluster_queryset, _proxy_queryset, _storage_queryset):
            """实例过滤ip:port"""
            insts = _query_params.get("instance").split(",")
            filter_inst = reduce(
                operator.or_, [Q(machine__ip=inst.split(":")[0], port=inst.split(":")[1]) for inst in insts]
            )
            _cluster_queryset = filter_inst_queryset(
                _cluster_queryset, _proxy_queryset, _storage_queryset, filter_inst
            )
            return _cluster_queryset

        filter_func_map = filter_func_map or {}
        filter_func_map = {
            "ip": filter_ip_func,
            "instance": filter_instance_func,
            **filter_func_map,
        }
        # 通过基础过滤函数进行cluster过滤
        for params in filter_func_map:
            if params in query_params:
                cluster_queryset = filter_func_map[params](
                    query_params, cluster_queryset, proxy_queryset, storage_queryset
                )

        cluster_infos = cls._filter_cluster_hook(
            bk_biz_id, cluster_queryset, proxy_queryset, storage_queryset, limit, offset, **kwargs
        )
        return cluster_infos

    @classmethod
    def _filter_cluster_hook(
        cls,
        bk_biz_id,
        cluster_queryset: QuerySet,
        proxy_queryset: QuerySet,
        storage_queryset: QuerySet,
        limit: int,
        offset: int,
        **kwargs,
    ) -> ResourceList:
        """
        为查询的集群填充额外信息, 子类可继承此方法实现其他回调
        @param bk_biz_id: 业务ID
        @param cluster_queryset: 过滤集群查询集
        @param proxy_queryset: 过滤的proxy查询集
        @param storage_queryset: 过滤的storage查询集
        @param limit: 分页限制
        @param offset: 分页起始
        """

        count = cluster_queryset.count()
        limit = count if limit == -1 else limit
        if count == 0:
            return ResourceList(count=0, data=[])

        # 预取proxy_queryset，storage_queryset，加块查询效率
        cluster_queryset = cluster_queryset[offset : limit + offset].prefetch_related(
            Prefetch("proxyinstance_set", queryset=proxy_queryset.select_related("machine"), to_attr="proxies"),
            Prefetch("storageinstance_set", queryset=storage_queryset.select_related("machine"), to_attr="storages"),
            "tag_set",
        )
        cluster_ids = list(cluster_queryset.values_list("id", flat=True))

        # 获取集群与访问入口的映射
        cluster_entry_map = ClusterEntry.get_cluster_entry_map([cluster.id for cluster in cluster_queryset])

        # 获取DB模块的映射信息
        db_module_names_map = {
            module.db_module_id: module.db_module_name
            for module in DBModule.objects.filter(bk_biz_id=bk_biz_id, cluster_type__in=cls.cluster_types)
        }

        # 获取集群操作记录的映射关系
        cluster_operate_records_map = ClusterOperateRecord.get_cluster_records_map(cluster_ids)

        # 将集群的查询结果序列化为集群字典信息
        clusters: List[Dict[str, Any]] = []
        for cluster in cluster_queryset:
            clusters.append(
                cls._to_cluster_representation(
                    cluster, db_module_names_map, cluster_entry_map, cluster_operate_records_map, **kwargs
                )
            )

        return ResourceList(count=count, data=clusters)

    @classmethod
    def _to_cluster_representation(
        cls,
        cluster: Cluster,
        db_module_names_map: Dict[int, str],
        cluster_entry_map: Dict[int, Dict[str, str]],
        cluster_operate_records_map: Dict[int, List],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        将集群对象转为可序列化的 dict 结构
        @param cluster: model Cluster 对象, 增加了 storages 和 proxies 属性
        @param db_module_names_map: key 是 db_module_id, value 是 db_module_name
        @param cluster_entry_map: key 是 cluster.id, value 是当前集群对应的 entry 映射
        @param cluster_operate_records_map: key 是 cluster.id, value 是当前集群对应的 操作记录 映射
        """
        cluster_entry = cluster_entry_map.get(cluster.id, {})
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        bk_cloud_name = cloud_info.get(str(cluster.bk_cloud_id), {}).get("bk_cloud_name", "")
        return {
            "id": cluster.id,
            "phase": cluster.phase,
            "phase_name": cluster.get_phase_display(),
            "status": cluster.status,
            "operations": cluster_operate_records_map.get(cluster.id, []),
            "cluster_time_zone": cluster.time_zone,
            "cluster_name": cluster.name,
            "cluster_alias": cluster.alias,
            "cluster_access_port": cluster.access_port,
            "cluster_type": cluster.cluster_type,
            "cluster_type_name": ClusterType.get_choice_label(cluster.cluster_type),
            "master_domain": cluster_entry.get("master_domain", ""),
            "slave_domain": cluster_entry.get("slave_domain", ""),
            "bk_biz_id": cluster.bk_biz_id,
            "bk_biz_name": AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).bk_biz_name,
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_cloud_name": bk_cloud_name,
            "major_version": cluster.major_version,
            "region": cluster.region,
            "db_module_name": db_module_names_map.get(cluster.db_module_id, ""),
            "db_module_id": cluster.db_module_id,
            "creator": cluster.creator,
            "updater": cluster.updater,
            "create_at": datetime2str(cluster.create_at),
            "update_at": datetime2str(cluster.update_at),
        }

    @classmethod
    def _list_instances(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        **kwargs,
    ) -> ResourceList:
        """
        查询实例信息
        @param bk_biz_id: 业务 ID
        @param query_params: 查询条件. 通过 .serializers.ListResourceSLZ 完成数据校验
        @param limit: 分页查询, 每页展示的数目
        @param offset: 分页查询, 当前页的偏移数
        @param filter_params_map: 过滤参数map
        """
        query_filters = Q(bk_biz_id=bk_biz_id, cluster_type__in=cls.cluster_types)

        # 定义内置的过滤参数map
        inner_filter_params_map = {
            "ip": Q(machine__ip__in=query_params.get("ip", "").split(",")),
            "port": Q(port__in=query_params.get("port", "").split(",")),
            "status": Q(status__in=query_params.get("status", "").split(",")),
            "cluster_id": Q(cluster__id=query_params.get("cluster_id")),
            "region": Q(region=query_params.get("region")),
            "role": Q(role__in=query_params.get("role", "").split(",")),
            "name": Q(cluster__name__in=query_params.get("name", "").split(",")),
            "domain": Q(
                cluster__clusterentry__cluster_entry_type=ClusterEntryType.DNS.value,
                cluster__clusterentry__entry__in=query_params.get("domain", "").split(","),
            ),
        }

        def join_instance_by_q(instances: str) -> Q:
            insts = instances.split(",")
            filter_inst = reduce(
                operator.or_, [Q(machine__ip=inst.split(":")[0], port=inst.split(":")[1]) for inst in insts]
            )
            return filter_inst

        # 判断是否需要实例过滤
        if query_params.get("instance"):
            filter_params_map.update({"instance": join_instance_by_q(query_params.get("instance"))})

        filter_params_map = filter_params_map or {}
        filter_params_map.update(inner_filter_params_map)
        # 通过基础过滤参数进行instance过滤
        for param in filter_params_map:
            if query_params.get(param):
                query_filters &= filter_params_map[param]
        instance_queryset = cls._filter_instance_qs(query_filters, query_params)

        # 将实例的查询结果序列化为实例字典信息
        paginated_instances = cls._filter_instance_hook(
            bk_biz_id, query_params, instance_queryset[offset : offset + limit], **kwargs
        )
        return ResourceList(count=instance_queryset.count(), data=paginated_instances)

    @classmethod
    def _filter_instance_hook(cls, bk_biz_id, query_params, instances, **kwargs):
        # 查询访问入口
        cluster_ids = [instance["cluster__id"] for instance in instances]
        cluster_entry_map = ClusterEntry.get_cluster_entry_map(cluster_ids)
        # 将实例的查询结果序列化为实例字典信息
        instance_infos = [cls._to_instance_representation(inst, cluster_entry_map, **kwargs) for inst in instances]
        # 特例：如果有extra参数，则补充额外实例信息
        if query_params.get("extra"):
            cls._fill_instance_extra_info(bk_biz_id, instance_infos)

        return instance_infos

    @classmethod
    def _fill_instance_extra_info(cls, bk_biz_id: int, instance_infos: List[Dict]):
        """
        补充实例的额外信息，这里的一个实现是补充主机和关联集群信息
        @param bk_biz_id: 业务ID
        @param instance_infos: 实例字典信息
        """
        instances_extra_info = InstanceHandler(bk_biz_id).check_instances(query_instances=instance_infos)
        address__instance_extra_info = {inst["instance_address"]: inst for inst in instances_extra_info}
        for inst in instance_infos:
            extra_info = address__instance_extra_info[inst["instance_address"]]
            inst.update(host_info=extra_info["host_info"], related_clusters=extra_info["related_clusters"])

    @classmethod
    def _filter_instance_qs(cls, query_filters: Q, query_params: Dict[str, str]) -> QuerySet:
        """
        获取过滤的实例queryset，子类可继承或覆写该方法以实现更复杂的查询
        @param query_filters: 实例的过滤Q查询
        @param query_params: 原始的查询条件map
        """
        inst_fields = [
            "id",
            "role",
            "port",
            "status",
            "create_at",
            "cluster__id",
            "cluster__major_version",
            "cluster__cluster_type",
            "cluster__db_module_id",
            "cluster__name",
            "machine__ip",
            "machine__bk_cloud_id",
            "machine__bk_host_id",
            "machine__spec_config",
            "machine__machine_type",
        ]
        # 获取storage实例的查询集
        storage_queryset = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .annotate(role=F("instance_role"))
            .filter(query_filters)
        )
        # 获取proxy实例的查询集
        proxy_queryset = (
            ProxyInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .annotate(role=F("access_layer"))
            .filter(query_filters)
        )
        return cls._filter_instance_qs_hook(storage_queryset, proxy_queryset, inst_fields, query_filters, query_params)

    @classmethod
    def _filter_instance_qs_hook(cls, storage_queryset, proxy_queryset, inst_fields, query_filters, query_params):
        instance_queryset = storage_queryset.union(proxy_queryset).values(*inst_fields).order_by("create_at")
        #  部署时间表头排序
        if query_params.get("ordering"):
            instance_queryset = instance_queryset.order_by(query_params.get("ordering"))
        return instance_queryset

    @classmethod
    def _to_instance_representation(cls, instance: dict, cluster_entry_map: dict, **kwargs) -> Dict[str, Any]:
        """
        将实例对象转为可序列化的 dict 结构
        @param instance: 实例信息
        @param cluster_entry_map: key 是 cluster.id, value 是当前集群对应的 entry 映射
        """
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        bk_cloud_name = cloud_info.get(str(instance["machine__bk_cloud_id"]), {}).get("bk_cloud_name", "")
        return {
            "id": instance["id"],
            "cluster_id": instance["cluster__id"],
            "cluster_type": instance["cluster__cluster_type"],
            "cluster_name": instance["cluster__name"],
            "version": instance["cluster__major_version"],
            "db_module_id": instance["cluster__db_module_id"],
            "bk_cloud_id": instance["machine__bk_cloud_id"],
            "bk_cloud_name": bk_cloud_name,
            "ip": instance["machine__ip"],
            "port": instance["port"],
            "instance_address": f"{instance['machine__ip']}{IP_PORT_DIVIDER}{instance['port']}",
            "bk_host_id": instance["machine__bk_host_id"],
            "machine_type": instance["machine__machine_type"],
            "role": instance["role"],
            "master_domain": cluster_entry_map.get(instance["cluster__id"], {}).get("master_domain", ""),
            "slave_domain": cluster_entry_map.get(instance["cluster__id"], {}).get("slave_domain", ""),
            "status": instance["status"],
            "create_at": datetime2str(instance["create_at"]),
            "spec_config": instance["machine__spec_config"],
        }

    @classmethod
    def _list_machines(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        **kwargs,
    ) -> ResourceList:
        """
        查询机器信息
        @param bk_biz_id: 业务 ID
        @param query_params: 查询条件. 通过 .serializers.ListResourceSLZ 完成数据校验
        @param limit: 分页查询, 每页展示的数目
        @param offset: 分页查询, 当前页的偏移数
        @param filter_params_map: 过滤参数map
        """
        query_filters = Q(bk_biz_id=bk_biz_id, cluster_type__in=cls.cluster_types)
        # 定义内置的过滤参数map
        filter_params_map = filter_params_map or {}
        inner_filter_params_map = {
            "bk_host_id": Q(bk_host_id=query_params.get("bk_host_id")),
            "ip": Q(ip__in=query_params.get("ip", "").split(",")),
            "machine_type": Q(machine_type=query_params.get("machine_type")),
            "bk_os_name": Q(bk_os_name=query_params.get("bk_os_name")),
            "bk_cloud_id": Q(bk_cloud_id=query_params.get("bk_cloud_id")),
            "bk_agent_id": Q(bk_agent_id=query_params.get("bk_agent_id")),
            "instance_role": (
                Q(storageinstance__instance_role=query_params.get("instance_role"))
                | Q(proxyinstance__access_layer=query_params.get("instance_role"))
            ),
            "creator": Q(creator__icontains=query_params.get("creator")),
        }
        filter_params_map = {**inner_filter_params_map, **filter_params_map}

        # 通过基础过滤参数进行cluster过滤
        for param in filter_params_map:
            if query_params.get(param):
                query_filters &= filter_params_map[param]

        machine_queryset = Machine.objects.filter(query_filters).distinct()
        machine_infos = cls._filter_machine_hook(bk_biz_id, machine_queryset, limit, offset, **kwargs)
        return machine_infos

    @classmethod
    def _filter_machine_hook(
        cls,
        bk_biz_id,
        machine_queryset: QuerySet,
        limit: int,
        offset: int,
        **kwargs,
    ) -> ResourceList:
        """
        为查询的集群填充额外信息, 子类可继承此方法实现其他回调
        @param bk_biz_id: 业务ID
        @param machine_queryset: 过滤机器查询集
        @param limit: 分页限制
        @param offset: 分页起始
        """

        count = machine_queryset.count()
        limit = count if limit == -1 else limit
        if count == 0:
            return ResourceList(count=0, data=[])

        # 预取proxy_queryset，storage_queryset，加块查询效率
        machine_queryset = machine_queryset.order_by("-create_at")[offset : limit + offset].prefetch_related(
            "storageinstance_set__cluster", "proxyinstance_set__cluster"
        )

        # 预取host的cc信息
        bk_host_ids = list(machine_queryset.values_list("bk_host_id", flat=True))
        host_infos = HostHandler.check([{"bk_biz_id": bk_biz_id, "scope_type": "biz"}], [], [], bk_host_ids)
        host_id_info_map = {host_info["host_id"]: host_info for host_info in host_infos}

        # 将集群的查询结果序列化为集群字典信息
        machine_infos: List[Dict[str, Any]] = []
        for machine in machine_queryset:
            machine_infos.append(cls._to_machine_representation(machine, host_id_info_map, **kwargs))

        return ResourceList(count=count, data=machine_infos)

    @classmethod
    def _to_machine_representation(
        cls,
        machine: Machine,
        host_id_info_map: Dict[int, Dict],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        将机器对象转为可序列化的 dict 结构
        @param machine: model Machine 对象, 增加了 storages 和 proxies 属性
        @param host_id_info_map: key 是 bk_host_id, value 是 机器在cc的信息
        """
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        bk_cloud_name = cloud_info.get(str(machine.bk_cloud_id), {}).get("bk_cloud_name", "")
        machine_info = {
            "bk_host_id": machine.bk_host_id,
            "ip": machine.ip,
            "bk_cloud_id": machine.bk_cloud_id,
            "bk_cloud_name": bk_cloud_name,
            "cluster_type": machine.cluster_type,
            "machine_type": machine.machine_type,
            "create_at": machine.create_at,
            "spec_id": machine.spec_id,
            "spec_config": machine.spec_config,
            "host_info": host_id_info_map.get(machine.bk_host_id, {}),
        }
        machine_info.update(cls._get_machine_extra_info(machine))
        return machine_info

    @classmethod
    def _get_machine_extra_info(cls, machine: Machine) -> dict:
        """
        获取机器上关联集群/实例的额外信息
        @param machine: Machine 对象
        """
        # 获取machine关联的实例角色
        instance_role: str = ""
        instances: list = []
        if machine.storageinstance_set.count():
            instance_role = machine.storageinstance_set.first().instance_role
            instances = [inst.simple_desc for inst in machine.storageinstance_set.all()]
        if machine.proxyinstance_set.count():
            instance_role = machine.proxyinstance_set.first().access_layer
            instances = [inst.simple_desc for inst in machine.proxyinstance_set.all()]

        # 获取machine关联的集群信息，目前一个实例只关联一个集群
        related_clusters_map: Dict[int, List[Dict]] = {}
        for inst in [*list(machine.storageinstance_set.all()), *list(machine.proxyinstance_set.all())]:
            cluster = inst.cluster.first()
            related_clusters_map[cluster.id] = cluster.to_dict()

        return {
            "instance_role": instance_role,
            "related_instances": instances,
            "related_clusters": related_clusters_map.values(),
        }
