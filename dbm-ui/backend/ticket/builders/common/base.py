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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import AccessLayer, ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.mysql.cluster.handlers import ClusterServiceHandler
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.ticket import builders
from backend.ticket.constants import TICKET_TYPE__CLUSTER_TYPE_MAP, TicketType


def fetch_cluster_ids(details: Dict[str, Any]) -> List[int]:
    def _find_cluster_id(_cluster_ids: List[int], _info: Dict):
        if "cluster_id" in _info:
            _cluster_ids.append(_info["cluster_id"])
        elif "cluster_ids" in _info:
            _cluster_ids.extend(_info["cluster_ids"])

    cluster_ids = []
    _find_cluster_id(cluster_ids, details)
    if isinstance(details.get("infos"), dict):
        _find_cluster_id(cluster_ids, details.get("infos"))
    elif isinstance(details.get("infos"), list):
        for info in details.get("infos"):
            _find_cluster_id(cluster_ids, info)

    return cluster_ids


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
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


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

    db_name_pattern = re.compile(r"^[a-z][a-zA-Z0-9_-]{0,39}$")

    @classmethod
    def validate_hosts_from_idle_pool(cls, bk_biz_id: int, host_list: List[int]) -> Set[int]:
        """获取所有不在空闲机池的主机"""

        idle_host_info_list = ResourceQueryHelper.search_cc_hosts(
            bk_biz_id=bk_biz_id, role_host_ids=host_list, module_filter=_("空闲机")
        )
        idle_host_list = [host["bk_host_id"] for host in idle_host_info_list]

        return set(host_list) - set(idle_host_list)

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
            for info in ClusterServiceHandler(bk_biz_id).get_intersected_machines_from_clusters(cluster_ids, role)
        ]
        return inst["bk_host_id"] in intersected_host_ids

    @classmethod
    def validate_db_name(cls, db_name: str) -> Tuple[bool, str]:
        """校验新db name是否合法"""
        # 1. [a-zA-z][a-zA-Z0-9_-]{0,39}
        # 2. 不以 dba_rollback 结尾
        # 3. 不以 stage_truncate 开头

        if not re.match(cls.db_name_pattern, db_name):
            message = _("新DB名字{}格式不合法，请保证数据库名以小写字母开头且只能包含字母、数字、连接符-和下划线_，并且长度在1到39字符之间").format(db_name)
            return False, message

        if db_name.startswith("stage_truncate"):
            return False, _("DB名{}不能以stage_truncate开头").format(db_name)

        if db_name.endswith("dba_rollback"):
            return False, _("DB名{}不能以dba_rollback结尾").format(db_name)

        return True, ""

    @classmethod
    def validate_duplicate_cluster_name(cls, bk_biz_id, ticket_type, cluster_name):
        cluster_type = TICKET_TYPE__CLUSTER_TYPE_MAP.get(ticket_type, ticket_type)
        if Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type, name=cluster_name).exists():
            raise serializers.ValidationError(
                _("业务{}下已经存在同类型: {}, 同名: {} 集群，请重新命名").format(bk_biz_id, cluster_type, cluster_name)
            )

    @classmethod
    def _validate_single_database_table_selector(
        cls,
        db_patterns: List,
        ignore_dbs: List,
        table_patterns: List,
        ignore_tables: List,
        cluster_id,
        dbs_in_cluster_map: Dict[int, List],
        is_only_db_operate: bool = False,
    ) -> Tuple[bool, str]:
        """校验库表选择器中的单个数据是否合法"""

        all_patterns_list = [db_patterns, ignore_dbs, table_patterns, ignore_tables]
        for patterns in all_patterns_list:
            for ele in patterns:
                if ele == "%" or ("*" in ele and len(ele) > 1):
                    return False, _("不允许%单独使用，不允许*组合使用")

                if (("%" in ele) or ("?" in ele) or ("*" in ele)) and len(patterns) != 1:
                    return False, _("包含通配符时，每一个输入框只能允许单一对象")

                if not ele.strip():
                    return False, _("字符不允许只包含空格")

        if not db_patterns:
            return False, _("DB选择框不允许为空")

        if not is_only_db_operate and not table_patterns:
            return False, _("table选择框不允许为空")

        if not is_only_db_operate and (bool(ignore_tables) ^ bool(ignore_dbs)):
            return False, _("忽略DB选择框和忽略table选择框要么同时为空，要么同时不为空")

        db_name_list = [*db_patterns, *ignore_dbs]
        for db_name in db_name_list:
            if ("%" in db_name) or ("?" in db_name) or ("*" in db_name):
                continue

            is_valid_db_name, message = cls.validate_db_name(db_name)
            if not is_valid_db_name:
                return False, message

            if db_name not in dbs_in_cluster_map.get(cluster_id, []):
                return False, _("数据库{}不在所属集群{}中，请重新查验").format(db_name, cluster_id)

        return True, ""

    @classmethod
    def validate_database_table_selector(
        cls, bk_biz_id: int, infos: Dict, is_only_db_operate_list: List[bool] = None
    ) -> Tuple[bool, str]:
        """校验库表选择器的数据是否合法"""

        cluster_ids = [info["cluster_id"] for info in infos]
        dbs_in_cluster = RemoteServiceHandler(bk_biz_id).show_databases(cluster_ids)
        dbs_in_cluster_map = {db["cluster_id"]: db["databases"] for db in dbs_in_cluster}
        if not is_only_db_operate_list:
            is_only_db_operate_list = [False] * len(infos)

        for index, info in enumerate(infos):
            is_valid, message = CommonValidate._validate_single_database_table_selector(
                db_patterns=info["db_patterns"],
                ignore_dbs=info["ignore_dbs"],
                table_patterns=info["table_patterns"],
                ignore_tables=info["ignore_tables"],
                cluster_id=info["cluster_id"],
                dbs_in_cluster_map=dbs_in_cluster_map,
                is_only_db_operate=is_only_db_operate_list[index],
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
        from backend.ticket.builders.mysql.base import MySQLBaseOperateDetailSerializer

        details = self.ticket.details
        cluster_ids = fetch_cluster_ids(details)

        self.ticket.update_details(
            clusters={cluster.id: cluster.to_dict() for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        )

        # TODO: 补充实例信息


class InfluxdbTicketFlowBuilderPatchMixin(object):
    @classmethod
    def get_instances(cls, _ticket_type, _details) -> list:
        if _ticket_type == TicketType.INFLUXDB_REPLACE:
            instance_list = _details.get("old_nodes", {}).get("influxdb", [])
        else:
            instance_list = _details.get("instance_list")
        return list(map(lambda x: x["ip"], instance_list))

    def patch_ticket_detail(self):
        """补充单据详情，用于重复单据去重判断"""
        if self.ticket.ticket_type == TicketType.INFLUXDB_APPLY:
            return

        self.ticket.update_details(instances=self.get_instances(self.ticket.ticket_type, self.ticket.details))


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
