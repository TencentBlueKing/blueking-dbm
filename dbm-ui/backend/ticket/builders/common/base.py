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
import itertools
import logging
import operator
import re
from collections import defaultdict
from functools import reduce
from typing import Any, Dict, List, Set, Tuple, Union

from django.db.models import F, Q
from django.forms.models import model_to_dict
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import MASTER_DOMAIN_INITIAL_VALUE, PLAT_BIZ_ID, AffinityEnum
from backend.constants import DOMAIN_PATTERN
from backend.db_meta.enums import AccessLayer, ClusterPhase, ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.enums.comm import SystemTagEnum
from backend.db_meta.models import Cluster, ExtraProcessInstance, Machine, ProxyInstance, Spec, StorageInstance
from backend.db_services.dbbase.constants import IpDest
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.mysql.cluster.handlers import ClusterServiceHandler
from backend.db_services.mysql.dumper.handlers import DumperHandler
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.db_services.sqlserver.handlers import RemoteSqlserverServiceHandler
from backend.flow.utils.mysql.db_table_filter import DbTableFilter
from backend.flow.utils.mysql.db_table_filter.tools import contain_glob
from backend.ticket import builders
from backend.ticket.builders.common.constants import MAX_DOMAIN_LEN_LIMIT
from backend.ticket.constants import TicketType
from backend.ticket.exceptions import TicketParamsVerifyException
from backend.utils.basic import get_target_items_from_details

logger = logging.getLogger("app")


def get_filtered_items(details: Dict[str, Any], match_keys: List[str], valid_types: Union[type, tuple]) -> List:
    targets = get_target_items_from_details(obj=details, match_keys=match_keys)
    return [item for item in targets if isinstance(item, valid_types) and item]


def fetch_cluster_ids(details: Dict[str, Any]) -> List[int]:
    cluster_keys = [
        "cluster_id",
        "cluster_ids",
        "source_cluster_id",
        "target_cluster_id",
        "src_cluster",
        "dst_cluster",
        "dst_cluster_list",
        "source_cluster",
        "source_clusters",
        "target_cluster",
        "target_clusters",
    ]
    return get_filtered_items(details, cluster_keys, int)


def fetch_instance_ids(details: Dict[str, Any]) -> List[Union[int, str]]:
    instance_id_keys = ["instance_id", "instance_ids"]
    return get_filtered_items(details, instance_id_keys, (int, str))


def fetch_host_ids(details: Dict[str, Any]) -> List[int]:
    host_keys = ["host_id", "bk_host_id", "bk_host_ids"]
    return get_filtered_items(details, host_keys, int)


def fetch_machine_ids(details: Dict[str, Any]) -> List[Union[int, str]]:
    machine_keys = ["ip"]
    return get_filtered_items(details, machine_keys, (int, str))


def fetch_apply_hosts(details: Dict[str, Any]) -> List[Dict]:
    role_hosts = get_target_items_from_details(details, match_keys=["nodes"])
    hosts = list(itertools.chain(*[h for hosts in role_hosts for h in hosts.values()]))
    # 适配backend_group分组
    master_slave_hosts = get_target_items_from_details(hosts, match_keys=["master", "slave"])
    apply_hosts = [host for host in hosts if "master" not in host] + master_slave_hosts
    return apply_hosts


def fetch_recycle_hosts(details: Dict[str, Any]) -> List[Dict]:
    role_hosts = get_target_items_from_details(details, match_keys=["old_nodes"])
    hosts = list(itertools.chain(*[h for hosts in role_hosts for h in hosts.values()]))
    return hosts


def remove_useless_spec(attrs: Dict[str, Any]) -> Dict[str, Any]:
    # 只保存有意义的规格资源申请
    real_resource_spec = {}
    if "resource_spec" not in attrs:
        return attrs

    for role, spec in attrs["resource_spec"].items():
        if spec and spec.get("count"):
            real_resource_spec[role] = spec

    attrs["resource_spec"] = real_resource_spec
    return attrs


def format_bigdata_resource_spec(attrs: Dict[str, Any]) -> Dict[str, Any]:
    if "resource_spec" not in attrs:
        return
    # 移除无用的资源角色申请
    remove_useless_spec(attrs)
    # 获取集群所在的城市
    cluster_location_spec = {}
    if "cluster_id" in attrs:
        cluster = Cluster.objects.get(id=attrs["cluster_id"])
        cluster_location_spec = {"city": cluster.region, "sub_zone_ids": []}
    # 格式化资源规格的亲和性和城市
    for role, resource_spec in attrs["resource_spec"].items():
        # 大数据亲和性固定为MAX_EACH_ZONE_EQUAL
        resource_spec["affinity"] = AffinityEnum.MAX_EACH_ZONE_EQUAL
        # 城市优先以传递的为准，然后以集群为准
        resource_spec["location_spec"] = resource_spec.get("location_spec") or cluster_location_spec


class HostInfoSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    ip = serializers.CharField(help_text=_("IP地址"))
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    port = serializers.IntegerField(help_text=_("端口号"), required=False)


class DisplayInfoSerializer(serializers.Serializer):
    """
    前端展示使用的字段，由前端与产品定义即可，无需后端调整
    """

    display_info = serializers.DictField(help_text=_("展示字段"), required=False)


class InstanceInfoSerializer(HostInfoSerializer):
    port = serializers.IntegerField(help_text=_("端口号"))


class HostRecycleSerializer(serializers.Serializer):
    """主机回收信息"""

    DEFAULT = {"for_biz": PLAT_BIZ_ID, "ip_dest": IpDest.Resource.value}
    FAULT_DEFAULT = {"for_biz": PLAT_BIZ_ID, "ip_dest": IpDest.Fault.value}

    for_biz = serializers.IntegerField(help_text=_("目标业务"), required=False, default=PLAT_BIZ_ID)
    ip_dest = serializers.ChoiceField(help_text=_("机器流向"), choices=IpDest.get_choices(), default=IpDest.Fault)


class SkipToRepresentationMixin(object):
    """
    跳过序列化器的校验，直接输出原始的instance
    一般用于在单据流程中为ticket注入了额外的detail信息
    """

    def to_representation(self, instance):
        return instance


class ParamValidateSerializerMixin(object):
    """所有单据的公共校校验入口"""

    validator = None

    def validated_params(self, attrs):
        ticket_type = self.context["ticket_type"]
        ticket_flow_builder = builders.BuilderFactory.registry[ticket_type]
        if hasattr(ticket_flow_builder.inner_flow_builder, "validator"):
            self.validator = ticket_flow_builder.inner_flow_builder.validator

        if not self.validator:
            logger.info(_("单据类型 {} 没有配置验证器，跳过参数验证").format(ticket_type))
            return attrs

        logger.info(_("开始执行单据类型 {} 的参数验证").format(ticket_type))
        logger.debug(
            _("验证器: {}，待验证参数: {}").format(
                self.validator.__name__ if hasattr(self.validator, "__name__") else str(self.validator), attrs
            )
        )

        errors = self.validator(attrs)

        if errors:
            logger.error(_("单据类型 {} 参数验证失败，错误信息: {}").format(ticket_type, errors))
            raise TicketParamsVerifyException(errors=errors, ticket_type=self.context["ticket_type"])

        logger.info(_("单据类型 {} 参数验证成功").format(ticket_type))
        return attrs


class CommonValidate(object):
    """存放单据的公共校验逻辑"""

    domain_pattern = re.compile(DOMAIN_PATTERN)

    @classmethod
    def validate_destroy_temporary_cluster_ids(cls, cluster_ids):
        clusters = Cluster.objects.filter(id__in=cluster_ids, tags__key=SystemTagEnum.TEMPORARY.value)
        if clusters.count() != len(cluster_ids):
            raise serializers.ValidationError(_("此单据只用于临时集群的销毁，请不要用于其他正常集群"))

        running_clusters = [cluster.id for cluster in clusters if cluster.phase == ClusterPhase.ONLINE]
        if len(running_clusters) != len(cluster_ids):
            raise serializers.ValidationError(_("存在临时集群已禁用，请在集群页面进行销毁"))

    @classmethod
    def validate_hosts_from_idle_pool(cls, bk_biz_id: int, host_list: List[int]) -> Set[int]:
        """获取所有不在空闲机池的主机"""

        idle_host_info_list = ResourceQueryHelper.search_cc_hosts(
            bk_biz_id=bk_biz_id, role_host_ids=host_list, module_filter=_("空闲机")
        )
        idle_host_list = [host["bk_host_id"] for host in idle_host_info_list]

        host_not_in_idle = set(host_list) - set(idle_host_list)
        if host_not_in_idle:
            raise serializers.ValidationError(_("主机{}不在空闲机池，请保证所选的主机均来自空闲机").format(host_not_in_idle))

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
    def validated_cluster_type(cls, cluster_ids: List[int], cluster_type: ClusterType):
        """校验集群的类型"""

        check_cluster_type = list(Cluster.objects.filter(id__in=cluster_ids).values_list("cluster_type", flat=True))
        if set(check_cluster_type) != {cluster_type.value}:
            raise serializers.ValidationError(
                _("请保证所选集群{}都是{}集群").format(cluster_ids, ClusterType.get_choice_label(cluster_type))
            )

    @classmethod
    def validate_instance_role(cls, inst_list: List[Dict], role: Union[AccessLayer, InstanceInnerRole]):
        """校验实例角色类型"""

        inst_filters = reduce(operator.or_, [Q(machine__ip=inst["ip"]) for inst in inst_list])
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
    def validate_duplicate_cluster_name(cls, bk_biz_id, ticket_type, cluster_name, db_module_id=0):
        """校验是否存在重复集群名"""
        cluster_types = TicketType.get_cluster_type_by_ticket(ticket_type)
        if Cluster.objects.filter(
            bk_biz_id=bk_biz_id, cluster_type__in=cluster_types, name=cluster_name, db_module_id=db_module_id
        ).exists():
            raise serializers.ValidationError(
                _("业务{}下已经存在同类型: {}, 同名: {} 集群，请重新命名").format(bk_biz_id, cluster_types, cluster_name)
            )

    @classmethod
    def _validate_domain_valid(cls, domain):
        if not cls.domain_pattern.match(domain):
            raise serializers.ValidationError(_("[{}]集群无法通过正则性校验{}").format(domain, cls.domain_pattern))

        if len(domain) > MAX_DOMAIN_LEN_LIMIT:
            raise serializers.ValidationError(_("[{}]集群域名长度过长，请不要让域名长度超过{}").format(domain, MAX_DOMAIN_LEN_LIMIT))
        if Cluster.objects.filter(immute_domain=domain).exists():
            raise serializers.ValidationError(_("该域名已被其他集群使用, 请重新设置域名"))

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
        is_ignore_case: bool = False,
    ) -> Tuple[bool, str]:
        """校验库表选择器中的单个数据是否合法"""

        # 库表选择器校验
        DbTableFilter(db_patterns, table_patterns, ignore_dbs, ignore_tables)
        # 数据库存在性校验
        db_name_list = [*db_patterns, *ignore_dbs]
        for db_name in db_name_list:
            if ("%" in db_name) or ("?" in db_name) or ("*" in db_name):
                continue

            if is_ignore_case:
                # 不区分大小写对比
                if db_name.lower() not in [i.lower() for i in dbs_in_cluster_map.get(cluster_id, [])]:
                    return False, _("数据库{}不在所属集群{}中，请重新查验[不区分大小写]").format(db_name, cluster_id)

            else:
                # 区分大小写对比
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

    @classmethod
    def validate_sqlserver_table_selector(cls, bk_biz_id: int, infos: Dict, role_key: None) -> Tuple[bool, str]:
        """校验sqlserver库表选择器的数据是否合法"""

        cluster_ids = [info["cluster_id"] for info in infos]
        # 如果想验证特定角色的库表，则传入集群ID与角色映射表
        cluster_id__role_map = {}
        if role_key:
            cluster_id__role_map = {info["cluster_id"]: info[role_key] for info in infos}

        dbs_in_cluster = RemoteSqlserverServiceHandler(bk_biz_id).show_databases(cluster_ids, cluster_id__role_map)
        dbs_in_cluster_map = {db["cluster_id"]: db["databases"] for db in dbs_in_cluster}

        # sqlserver 备份只有库正则、忽略库正则（db_list，ignore_db_list）
        for index, info in enumerate(infos):
            ignore_dbs = (
                info.get("clean_ignore_dbs_patterns", [])
                if "clean_ignore_dbs_patterns" in info
                else info.get("ignore_db_list", [])
            )
            db_patterns = (
                info.get("clean_dbs_patterns", []) if "clean_dbs_patterns" in info else info.get("db_list", [])
            )
            ignore_tables = (
                info.get("ignore_clean_tables", [""]) if ignore_dbs else info.get("ignore_clean_tables", [])
            )
            is_valid, message = CommonValidate._validate_single_database_table_selector(
                db_patterns=db_patterns,
                ignore_dbs=ignore_dbs,
                table_patterns=info.get("clean_tables", ["*"]),
                ignore_tables=ignore_tables,
                cluster_id=info["cluster_id"],
                dbs_in_cluster_map=dbs_in_cluster_map,
                is_ignore_case=True,
            )
            if not is_valid:
                return is_valid, f"line {index}: {message}"

        return True, ""

    @classmethod
    def validate_mysql_db_rename(
        cls, infos: Dict, cluster__databases: Dict[int, List[str]], is_ignore_case: bool = False
    ):
        """
        校验mysql db重命名逻辑
        1. 不允许包含通配符
        2. 校验校验源DB是否存在于数据库
        3. 校验在同一个集群内，源DB名必须唯一，新DB名必须唯一，且源DB名不能出现在新DB名中
        4. 系统库不允许重命名
        5. 在一个单据中，同一个集群修改的时候 源库和目标库不允许重复，即不能出现： A 重命名为 B，然后A 又重命名为 C的情况
        6. 源DB必须在集群中，新DB必须不在集群中
        @param infos: 重命名信息 [{"cluster_id": 1, "from_database": "abc", "to_database": "cde"}]
        @param cluster__databases: 集群与业务库的映射
        @param is_ignore_case: 是否区分大小写比较，默认不区分
        """
        cluster__db_name_map: Dict[int, Dict[str, List]] = defaultdict(
            lambda: {"from_database": [], "to_database": []}
        )

        for db_info in infos:
            cluster__db_name_map[db_info["cluster_id"]]["from_database"].append(db_info["from_database"])
            cluster__db_name_map[db_info["cluster_id"]]["to_database"].append(db_info["to_database"])

            # 校验源dbname和新db那么不包含通配符
            if contain_glob(db_info["to_database"]) or contain_glob(db_info["from_database"]):
                raise serializers.ValidationError(_("源DB名和新DB名不允许包含通配符"))

        # 校验在同一个集群内，源DB名必须唯一，新DB名必须唯一，且源DB名不能出现在新DB名中
        for cluster_id, name_info in cluster__db_name_map.items():
            check_dbs = (
                [i.lower() for i in cluster__databases[cluster_id]]
                if is_ignore_case
                else cluster__databases[cluster_id]
            )
            from_database_list = (
                [i.lower() for i in name_info["from_database"]] if is_ignore_case else name_info["from_database"]
            )
            to_database_list = (
                [i.lower() for i in name_info["to_database"]] if is_ignore_case else name_info["to_database"]
            )

            for db_name in from_database_list:
                if db_name not in check_dbs:
                    raise serializers.ValidationError(_("数据库[{}]不存在于集群{}中").format(db_name, cluster_id))

            for db_name in to_database_list:
                if db_name in check_dbs:
                    raise serializers.ValidationError(_("重命名数据库[{}]已存在于集群{}中").format(db_name, cluster_id))

            if len(set(from_database_list)) != len(from_database_list):
                raise serializers.ValidationError(_("请保证集群{}中源数据库名{}的名字唯一").format(cluster_id, from_database_list))

            if len(set(to_database_list)) != len(to_database_list):
                raise serializers.ValidationError(_("请保证集群{}中新数据库名{}的名字唯一").format(cluster_id, to_database_list))

            intersected_db_names = set(from_database_list).intersection(set(to_database_list))
            if intersected_db_names:
                raise serializers.ValidationError(_("请保证源数据库名{}不要出现在新数据库名列表中").format(intersected_db_names))

    @classmethod
    def validate_slave_is_stand_by(cls, slave_insts: List[str]):
        """校验slave实例的is_stand_by为true，并且处于正常状态，用于校验主从互切是否合法"""
        # 注意：这里的slave_insts是一个ip列表
        slaves = StorageInstance.find_storage_instance_by_ip(slave_insts)
        normal_slaves = slaves.filter(
            instance_inner_role=InstanceInnerRole.SLAVE, is_stand_by=True, status=InstanceStatus.RUNNING
        ).values("machine__ip")
        normal_slaves = [f"{slave['machine__ip']}" for slave in normal_slaves]

        bad_slaves = set(slave_insts) - set(normal_slaves)
        if bad_slaves:
            raise serializers.ValidationError(_("slave: {}的is_stand_by不为true，或者处于异常状态").format(bad_slaves))


class BaseTicketFlowBuilderPatchMixin(object):
    need_patch_cluster_details: bool = True
    need_patch_spec_details: bool = True
    need_patch_instance_details: bool = False
    need_patch_recycle_host_details: bool = False
    need_patch_recycle_cluster_details: bool = False
    need_patch_machine_details: bool = False

    def patch_cluster_details(self):
        """补充集群信息"""
        cluster_ids = fetch_cluster_ids(self.ticket.details)
        if not cluster_ids:
            return
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        clusters = {
            cluster.id: {
                **cluster.to_dict(),
                "bk_cloud_name": cloud_info.get(str(cluster.bk_cloud_id), {}).get("bk_cloud_name", ""),
            }
            for cluster in Cluster.objects.filter(id__in=cluster_ids)
        }
        self.ticket.details["clusters"] = clusters

    def patch_spec_details(self):
        """补充规格信息"""
        spec_ids = get_target_items_from_details(self.ticket.details, match_keys=["spec_id"])
        # 过滤掉非合法类型和重复的spec_id
        spec_ids = set([int(spec_id) for spec_id in spec_ids if isinstance(spec_id, (int, str))])
        if not spec_ids:
            return
        specs = {
            spec.spec_id: {**spec.get_spec_info(), "capacity": spec.capacity}
            for spec in Spec.objects.filter(spec_id__in=spec_ids)
        }
        self.ticket.details["specs"] = specs

    def patch_instance_details(self):
        """补充实例信息-目前仅考虑大数据"""
        instance_ids = fetch_instance_ids(self.ticket.details)
        if not instance_ids:
            return
        instances = {inst.id: inst.simple_desc for inst in StorageInstance.objects.filter(id__in=instance_ids)}
        self.ticket.details["instances"] = instances

    def patch_recycle_host_details(self):
        """补充回收主机信息，在回收类单据一定调用此方法"""
        recycle_hosts = fetch_recycle_hosts(self.ticket.details)
        if not recycle_hosts:
            return
        self.ticket.details["recycle_hosts"] = ResourceHandler.standardized_resource_host(recycle_hosts)

    def patch_recycle_cluster_details(self, role=None):
        """补充集群下架后回收主机信息，在下架类单据一定调用此方法"""
        recycle_hosts = Cluster.get_cluster_related_machines(fetch_cluster_ids(self.ticket.details), role)
        recycle_hosts = [{"bk_host_id": host.bk_host_id} for host in recycle_hosts]
        self.ticket.details["recycle_hosts"] = ResourceHandler.standardized_resource_host(recycle_hosts)

    def _collect_machine_details(self, machines):
        machine_infos = defaultdict(dict)

        for machine in machines:
            storage_instances = list(machine.storageinstance_set.all())
            proxy_instances = list(machine.proxyinstance_set.all())
            all_instances = storage_instances + proxy_instances

            # Determine instance role
            if storage_instances:
                machine_infos[machine.ip]["instance_role"] = storage_instances[0].instance_role
            elif proxy_instances:
                machine_infos[machine.ip]["instance_role"] = proxy_instances[0].access_layer

            # Collect related instances
            machine_infos[machine.ip]["related_instances"] = [inst.simple_desc for inst in all_instances]

            # Collect related clusters
            related_clusters = {inst.cluster.first().id for inst in all_instances if inst.cluster.first()}
            if related_clusters:
                machine_infos[machine.ip]["related_clusters"] = list(related_clusters)

            # Add spec config
            machine_infos[machine.ip]["spec_config"] = machine.spec_config

        return machine_infos

    def patch_machine_details(self):
        """补充主机信息"""
        machine_ips = [ip for info in self.ticket.details["infos"] for ip in fetch_machine_ids(info["old_nodes"])]

        if not machine_ips:
            return

        master_machines = Machine.objects.filter(ip__in=machine_ips).prefetch_related(
            "storageinstance_set__cluster", "proxyinstance_set__cluster"
        )

        machine_infos = self._collect_machine_details(master_machines)
        self.ticket.details["machine_infos"] = machine_infos

    def patch_ticket_detail(self):
        if self.need_patch_cluster_details:
            self.patch_cluster_details()
        if self.need_patch_spec_details:
            self.patch_spec_details()
        if self.need_patch_instance_details:
            self.patch_instance_details()
        if self.need_patch_recycle_host_details:
            self.patch_recycle_host_details()
        if self.need_patch_recycle_cluster_details:
            self.patch_recycle_cluster_details()
        if self.need_patch_machine_details:
            self.patch_machine_details()
        self.ticket.save(update_fields=["details", "update_at", "remark"])


class RedisTicketFlowBuilderPatchMixin(BaseTicketFlowBuilderPatchMixin):
    pass


class BigDataTicketFlowBuilderPatchMixin(BaseTicketFlowBuilderPatchMixin):
    need_patch_instance_details = True


class MySQLTicketFlowBuilderPatchMixin(BaseTicketFlowBuilderPatchMixin):
    pass


class SQLServerTicketFlowBuilderPatchMixin(BaseTicketFlowBuilderPatchMixin):
    pass


class DumperTicketFlowBuilderPatchMixin(MySQLTicketFlowBuilderPatchMixin):
    def patch_ticket_detail(self):
        """补充Dumper的实例信息"""
        # 补充集群和规格信息
        super().patch_ticket_detail()
        # 补充dumper信息
        dumper_ids = get_target_items_from_details(self.ticket.details, match_keys=["dumper_instance_ids"])
        dumper_infos = [model_to_dict(dumper) for dumper in ExtraProcessInstance.objects.filter(id__in=dumper_ids)]
        DumperHandler.patch_dumper_list_info(dumper_infos)
        self.ticket.update_details(dumpers={dumper["id"]: dumper for dumper in dumper_infos})


class InfluxdbTicketFlowBuilderPatchMixin(BigDataTicketFlowBuilderPatchMixin):
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
        super().patch_ticket_detail()


class MongoDBTicketFlowBuilderPatchMixin(BaseTicketFlowBuilderPatchMixin):
    pass


class BaseOperateResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def format(self):
        # 忽略没有infos的单据
        if "infos" not in self.ticket_data:
            return
        # 对每个info补充云区域ID和业务ID
        cluster_ids = fetch_cluster_ids(self.ticket_data)
        id__clusters = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data.get("infos", []):
            # 如果已经存在则跳过
            if info.get("bk_cloud_id") and info.get("bk_biz_id"):
                continue

            # 默认从集群中获取云区域ID和业务ID
            cluster_id = info.get("cluster_id") or info.get("src_cluster") or info.get("cluster_ids")[0]
            bk_cloud_id = id__clusters[cluster_id].bk_cloud_id
            info.update(bk_cloud_id=bk_cloud_id, bk_biz_id=self.ticket.bk_biz_id)

    def post_callback(self):
        pass
