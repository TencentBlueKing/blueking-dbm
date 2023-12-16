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
import operator
import re
from functools import reduce
from typing import Any, Dict, List, Set, Tuple, Union

from django.db.models import F, Q
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import MASTER_DOMAIN_INITIAL_VALUE
from backend.db_meta.enums import AccessLayer, ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, ExtraProcessInstance, Machine, ProxyInstance, StorageInstance
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.mysql.cluster.handlers import ClusterServiceHandler
from backend.db_services.mysql.dumper.handlers import DumperHandler
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.flow.utils.mysql.db_table_filter import DbTableFilter
from backend.ticket import builders
from backend.ticket.builders.common.constants import MAX_DOMAIN_LEN_LIMIT
from backend.ticket.constants import TicketType
from backend.utils.basic import get_target_items_from_details


def fetch_cluster_ids(details: Dict[str, Any]) -> List[int]:
    return [
        item
        for item in get_target_items_from_details(obj=details, match_keys=["cluster_id", "cluster_ids", "src_cluster"])
        if isinstance(item, int)
    ]


def fetch_instance_ids(details: Dict[str, Any]) -> List[int]:
    return [
        item
        for item in get_target_items_from_details(obj=details, match_keys=["instance_id", "instance_ids"])
        if isinstance(item, int)
    ]


def remove_useless_spec(attrs: Dict[str, Any]) -> Dict[str, Any]:
    # 只保存有意义的规格资源申请
    real_resource_spec = {}
    if "resource_spec" not in attrs:
        return

    for role, spec in attrs["resource_spec"].items():
        if spec and spec["count"]:
            real_resource_spec[role] = spec

    attrs["resource_spec"] = real_resource_spec
    return attrs


class HostInfoSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    ip = serializers.CharField(help_text=_("IP地址"))
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)


class InstanceInfoSerializer(HostInfoSerializer):
    port = serializers.IntegerField(help_text=_("端口号"))


class MultiInstanceHostInfoSerializer(HostInfoSerializer):
    instance_num = serializers.IntegerField


class SkipToRepresentationMixin(object):
    """
    跳过序列化器的校验，直接输出原始的instance
    一般用于在单据流程中为ticket注入了额外的detail信息
    """

    def to_representation(self, instance):
        return instance


class CommonValidate(object):
    """存放单据的公共校验逻辑"""

    domain_pattern = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62}){2,8}\.*(#(\d+))?$")

    @classmethod
    def validate_hosts_from_idle_pool(cls, bk_biz_id: int, host_list: List[int]) -> Set[int]:
        """获取所有不在空闲机池的主机"""

        idle_host_info_list = ResourceQueryHelper.search_cc_hosts(
            bk_biz_id=bk_biz_id, role_host_ids=host_list, module_filter=_("空闲机")
        )
        idle_host_list = [host["bk_host_id"] for host in idle_host_info_list]

        return set(host_list) - set(idle_host_list)

    @classmethod
    def validate_hosts_not_in_db_meta(cls, host_infos: List[Dict]):
        """校验主机不存在当前db_meta中"""
        host_ids = [node["bk_host_id"] for node in host_infos if node.get("bk_host_id")]
        exist_host_ids = Machine.objects.filter(bk_host_id__in=host_ids)
        if exist_host_ids.exists():
            host_ips = list(exist_host_ids.values_list("ip", flat=True))
            raise serializers.ValidationError(_("所选主机存在已经被使用，请重新选择主机。主机信息: {}").format(host_ips))

    @classmethod
    def validate_hosts_clusters_in_same_cloud_area(cls, host_infos: List[Dict], cluster_ids: List[int]) -> bool:
        """校验新主机和集群处于同一云区域下"""

        try:
            host_cloud_area = set([host["bk_cloud_id"] for host in host_infos])
        except KeyError:
            raise serializers.ValidationError(_("请输入主机的云区域信息"))

        if len(host_cloud_area) > 1:
            return False

        cluster_cloud_area = set([cluster.bk_cloud_id for cluster in Cluster.objects.filter(id__in=cluster_ids)])
        if len(cluster_cloud_area) > 1 or cluster_cloud_area != host_cloud_area:
            return False

        return True

    @classmethod
    def validate_cluster_type(cls, cluster_ids: List[int], cluster_type: ClusterType) -> bool:
        """校验集群的类型"""

        check_cluster_type = list(Cluster.objects.filter(id__in=cluster_ids).values_list("cluster_type", flat=True))
        if set(check_cluster_type) != {cluster_type.value}:
            return False

        return True

    @classmethod
    def validate_instance_role(cls, inst_list: List[Dict], role: Union[AccessLayer, InstanceInnerRole]):
        """校验实例角色类型"""

        inst_filters = reduce(operator.or_, [Q(machine__ip=inst["ip"], port=inst["port"]) for inst in inst_list])
        check_role_info = list(
            StorageInstance.objects.annotate(role=F("instance_inner_role"))
            .filter(inst_filters)
            .union(ProxyInstance.objects.annotate(role=F("access_layer")).filter(inst_filters))
            # 注意：这里的values一定得包含二者union的公共字段，比如id，
            # 不能只包含F表达式转换后的role。否则sql语句会解析为select * 导致union失败
            .values("role", "id")
        )
        check_roles = [info["role"] for info in check_role_info]
        if set(check_roles) != {role.value}:
            return False

        return True

    @classmethod
    def validate_instance_related_clusters(
        cls, inst: Dict, cluster_ids: List[int], role: Union[AccessLayer, InstanceInnerRole]
    ):
        """校验实例的关联集群"""

        bk_biz_id = inst["bk_biz_id"]
        intersected_host_ids = [
            info["bk_host_id"]
            for info in ClusterServiceHandler(bk_biz_id).get_intersected_machines_from_clusters(
                cluster_ids, role, False
            )
        ]
        return inst["bk_host_id"] in intersected_host_ids

    @classmethod
    def validate_duplicate_cluster_name(cls, bk_biz_id, ticket_type, cluster_name):
        from backend.ticket.builders import BuilderFactory

        cluster_type = BuilderFactory.ticket_type__cluster_type.get(ticket_type, ticket_type)
        if Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type, name=cluster_name).exists():
            raise serializers.ValidationError(
                _("业务{}下已经存在同类型: {}, 同名: {} 集群，请重新命名").format(bk_biz_id, cluster_type, cluster_name)
            )

    @classmethod
    def _validate_domain_valid(cls, domain):
        if not cls.domain_pattern.match(domain):
            raise serializers.ValidationError(_("[{}]集群无法通过正则性校验{}").format(domain, cls.domain_pattern))

        if len(domain) > MAX_DOMAIN_LEN_LIMIT:
            raise serializers.ValidationError(_("[{}]集群域名长度过长，请不要让域名长度超过{}").format(domain, MAX_DOMAIN_LEN_LIMIT))

    @classmethod
    def validate_generate_domain(cls, cluster_domain_prefix, cluster_name, db_app_abbr):
        """校验域名是否合法，仅适用于{cluster_domain_prefix}.{cluster_name}.{db_app_abbr}.db"""
        domain = f"{cluster_domain_prefix}.{cluster_name}.{db_app_abbr}.db"
        cls._validate_domain_valid(domain)

    @classmethod
    def validate_mysql_domain(cls, db_module_name, db_app_abbr, cluster_name):
        mysql_domain = MASTER_DOMAIN_INITIAL_VALUE.format(
            db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=cluster_name
        )
        cls._validate_domain_valid(mysql_domain)

    @classmethod
    def _validate_single_database_table_selector(
        cls,
        db_patterns: List,
        ignore_dbs: List,
        table_patterns: List,
        ignore_tables: List,
        cluster_id,
        dbs_in_cluster_map: Dict[int, List],
    ) -> Tuple[bool, str]:
        """校验库表选择器中的单个数据是否合法"""

        # 库表选择器校验
        DbTableFilter(db_patterns, table_patterns, ignore_dbs, ignore_tables)
        # 数据库存在性校验
        db_name_list = [*db_patterns, *ignore_dbs]
        for db_name in db_name_list:
            if ("%" in db_name) or ("?" in db_name) or ("*" in db_name):
                continue

            if db_name not in dbs_in_cluster_map.get(cluster_id, []):
                return False, _("数据库{}不在所属集群{}中，请重新查验").format(db_name, cluster_id)

        return True, ""

    @classmethod
    def validate_database_table_selector(cls, bk_biz_id: int, infos: Dict, role_key: None) -> Tuple[bool, str]:
        """校验库表选择器的数据是否合法"""

        cluster_ids = [info["cluster_id"] for info in infos]
        # 如果想验证特定角色的库表，则传入集群ID与角色映射表
        cluster_id__role_map = {}
        if role_key:
            cluster_id__role_map = {info["cluster_id"]: info[role_key] for info in infos}

        dbs_in_cluster = RemoteServiceHandler(bk_biz_id).show_databases(cluster_ids, cluster_id__role_map)
        dbs_in_cluster_map = {db["cluster_id"]: db["databases"] for db in dbs_in_cluster}

        for index, info in enumerate(infos):
            is_valid, message = CommonValidate._validate_single_database_table_selector(
                db_patterns=info["db_patterns"],
                ignore_dbs=info["ignore_dbs"],
                table_patterns=info["table_patterns"],
                ignore_tables=info["ignore_tables"],
                cluster_id=info["cluster_id"],
                dbs_in_cluster_map=dbs_in_cluster_map,
            )
            if not is_valid:
                return is_valid, f"line {index}: {message}"

        return True, ""


class RedisTicketFlowBuilderPatchMixin(object):
    def patch_ticket_detail(self):
        """补充单据详情，考虑到集群下架和实例下架后，无法根据id获取到详情，提前补充到单据"""

        details = self.ticket.details

        if "cluster_id" in details:
            cluster_ids = [details["cluster_id"]]
        elif "rules" in details:
            cluster_ids = [r["cluster_id"] for r in details["rules"]]
        else:
            cluster_ids = []

        self.ticket.update_details(
            clusters={cluster.id: cluster.to_dict() for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        )


class BigDataTicketFlowBuilderPatchMixin(object):
    def patch_ticket_detail(self):
        """补充大数据的集群信息和实例信息"""

        details = self.ticket.details
        cluster_ids = []

        # 补充集群信息。TODO: 暂时只考虑单个集群，目前大数据还没有对集群批量进行操作的要求
        if "cluster_id" in details:
            cluster_ids = [details["cluster_id"]]

        self.ticket.update_details(
            clusters={cluster.id: cluster.to_dict() for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        )

        # 补充实例信息。TODO: 考虑后续集群可能合并的原因，暂时忽略实例信息补充的情况


class MySQLTicketFlowBuilderPatchMixin(object):
    def patch_ticket_detail(self):
        """补充MySQL的集群信息和实例信息"""
        details = self.ticket.details
        cluster_ids = fetch_cluster_ids(details)

        self.ticket.update_details(
            clusters={cluster.id: cluster.to_dict() for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        )

        # TODO: 补充实例信息


class DumperTicketFlowBuilderPatchMixin(MySQLTicketFlowBuilderPatchMixin):
    def patch_ticket_detail(self):
        """补充Dumper的实例信息"""
        # 补充集群信息
        super().patch_ticket_detail()
        # 补充dumper信息
        dumper_ids = get_target_items_from_details(self.ticket.details, match_keys=["dumper_instance_ids"])
        dumper_infos = [model_to_dict(dumper) for dumper in ExtraProcessInstance.objects.filter(id__in=dumper_ids)]
        DumperHandler.patch_dumper_list_info(dumper_infos)
        self.ticket.update_details(dumpers={dumper["id"]: dumper for dumper in dumper_infos})


class InfluxdbTicketFlowBuilderPatchMixin(object):
    @classmethod
    def get_instances(cls, _ticket_type, _details) -> list:
        if _ticket_type == TicketType.INFLUXDB_REPLACE:
            instance_list = _details.get("old_nodes", {}).get("influxdb", [])
        else:
            instance_list = _details.get("instance_list")

        if not instance_list[0].get("instance_id"):
            return list(map(lambda x: x["ip"], instance_list))

        # 通过instance_id来更新instance信息
        instance_ids = [instance.get("instance_id") for instance in instance_list]
        id__instance = {s.id: s for s in StorageInstance.objects.filter(id__in=instance_ids)}
        for instance in instance_list:
            instance.update(id__instance[instance["instance_id"]].simple_desc)

        return list(map(lambda x: x["ip"], instance_list))

    def patch_ticket_detail(self):
        """补充单据详情，用于重复单据去重判断"""
        if self.ticket.ticket_type == TicketType.INFLUXDB_APPLY:
            return

        self.ticket.update_details(instances=self.get_instances(self.ticket.ticket_type, self.ticket.details))


class MongoDBTicketFlowBuilderPatchMixin(object):
    def patch_ticket_detail(self):
        """补充MongoDB的集群信息和实例信息"""
        details = self.ticket.details
        cluster_ids = fetch_cluster_ids(details)

        self.ticket.update_details(
            clusters={cluster.id: cluster.to_dict() for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        )

        # TODO: 补充实例信息


class BaseOperateResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def format(self):
        # 对每个info补充云区域ID和业务ID
        cluster_ids = fetch_cluster_ids(self.ticket_data)
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        for info in self.ticket_data["infos"]:
            # 如果已经存在则跳过
            if info.get("bk_cloud_id") and info.get("bk_biz_id"):
                continue

            # 默认从集群中获取云区域ID和业务ID
            cluster_id = info.get("cluster_id") or info.get("cluster_ids")[0]
            bk_cloud_id = clusters.get(id=cluster_id).bk_cloud_id
            info.update(bk_cloud_id=bk_cloud_id, bk_biz_id=self.ticket.bk_biz_id)

    def post_callback(self):
        pass
