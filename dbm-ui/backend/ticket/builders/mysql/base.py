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
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterDBHAStatusFlags, ClusterType, InstanceInnerRole
from backend.db_meta.models.cluster import Cluster, ClusterPhase
from backend.flow.consts import SYSTEM_DBS
from backend.flow.utils.mysql.db_table_filter.exception import DbTableFilterValidateException
from backend.flow.utils.mysql.db_table_filter.tools import glob_check
from backend.ticket import builders
from backend.ticket.builders import BuilderFactory, TicketFlowBuilder
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    CommonValidate,
    MySQLTicketFlowBuilderPatchMixin,
    SkipToRepresentationMixin,
    fetch_cluster_ids,
)
from backend.ticket.constants import TicketType


class BaseMySQLTicketFlowBuilder(MySQLTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.MySQL.value


class MySQLBasePauseParamBuilder(builders.PauseParamBuilder):
    pass


class MySQLBaseOperateDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """
    mysql操作的基类，主要功能:
    1. 屏蔽序列化的to_representation
    2. 存放mysql操作的各种校验逻辑
    """

    # 实例不可用时，还能正常提单类型的白名单
    SLAVE_UNAVAILABLE_WHITELIST = [
        TicketType.MYSQL_IMPORT_SQLFILE.value,
        TicketType.MYSQL_CLIENT_CLONE_RULES.value,
        TicketType.MYSQL_ROLLBACK_CLUSTER.value,
        TicketType.MYSQL_HA_RENAME_DATABASE.value,
        TicketType.MYSQL_ADD_SLAVE.value,
        TicketType.MYSQL_RESTORE_LOCAL_SLAVE.value,
        TicketType.MYSQL_RESTORE_SLAVE.value,
        TicketType.MYSQL_HA_TRUNCATE_DATA.value,
        TicketType.MYSQL_PARTITION.value,
    ]
    MASTER_UNAVAILABLE_WHITELIST = [
        TicketType.MYSQL_MASTER_FAIL_OVER.value,
        TicketType.MYSQL_MASTER_SLAVE_SWITCH.value,
    ]
    PROXY_UNAVAILABLE_WHITELIST = TicketType.get_values()
    # 集群的flag状态与白名单的映射表
    unavailable_whitelist__status_flag = {
        ClusterDBHAStatusFlags.ProxyUnavailable: PROXY_UNAVAILABLE_WHITELIST,
        ClusterDBHAStatusFlags.BackendSlaveUnavailable: SLAVE_UNAVAILABLE_WHITELIST,
        ClusterDBHAStatusFlags.BackendMasterUnavailable: MASTER_UNAVAILABLE_WHITELIST,
    }

    @classmethod
    def fetch_obj_by_keys(cls, obj_dict: Dict, keys: List[str]):
        """从给定的字典中提取key值"""
        objs: List[Any] = []
        for key in keys:
            if key not in obj_dict:
                continue

            if isinstance(obj_dict[key], list):
                objs.extend(obj_dict[key])
            else:
                objs.append(obj_dict[key])

        return objs

    def validate_cluster_can_access(self, attrs):
        """校验集群状态是否可以提单"""
        clusters = Cluster.objects.filter(id__in=fetch_cluster_ids(details=attrs))
        ticket_type = self.context["ticket_type"]

        for cluster in clusters:
            if cluster.cluster_type == ClusterType.TenDBSingle:
                # 如果单节点异常，则直接报错
                if cluster.status_flag:
                    raise serializers.ValidationError(_("单节点实例状态异常，暂时无法执行该单据类型：{}").format(ticket_type))
                continue

            for status_flag, whitelist in self.unavailable_whitelist__status_flag.items():
                if cluster.status_flag & status_flag and ticket_type not in whitelist:
                    raise serializers.ValidationError(
                        _("集群实例状态异常:{}，暂时无法执行该单据类型：{}").format(status_flag.flag_text(), ticket_type)
                    )

        return attrs

    def validate_hosts_clusters_in_same_cloud_area(self, attrs, host_key: List[str], cluster_key: List[str]):
        """校验新增机器和集群是否在同一云区域下"""
        for info in attrs["infos"]:
            host_infos = self.fetch_obj_by_keys(info, host_key)
            cluster_ids = self.fetch_obj_by_keys(info, cluster_key)
            if not CommonValidate.validate_hosts_clusters_in_same_cloud_area(host_infos, cluster_ids):
                raise serializers.ValidationError(_("请保证所选集群{}与新增机器{}在同一云区域下").format(cluster_ids, host_infos))

    def validate_instance_role(self, attrs, instance_key: List[str], role: Union[AccessLayer, InstanceInnerRole]):
        """校验实例的角色类型是否一致"""
        inst_list: List[Dict] = []
        for info in attrs["infos"]:
            inst_list.extend(self.fetch_obj_by_keys(info, instance_key))

        if not CommonValidate.validate_instance_role(inst_list, role):
            raise serializers.ValidationError(_("请保证实例f{}的角色类型为{}").format(inst_list, role))

    def validated_cluster_type(self, attrs, cluster_type: ClusterType):
        """校验集群类型为高可用"""
        cluster_ids = fetch_cluster_ids(attrs)
        CommonValidate.validated_cluster_type(cluster_ids, cluster_type)

    def validate_instance_related_clusters(
        self, attrs, instance_key: List[str], cluster_key: List[str], role: Union[AccessLayer, InstanceInnerRole]
    ):
        """校验实例的关联集群是否一致"""
        # TODO: 貌似这里只能循环校验，数据量大可能会带来性能问题
        for info in attrs["infos"]:
            inst = self.fetch_obj_by_keys(info, instance_key)[0]
            cluster_ids = self.fetch_obj_by_keys(info, cluster_key)
            if not CommonValidate.validate_instance_related_clusters(inst, cluster_ids, role):
                raise serializers.ValidationError(_("请保证所选实例{}的关联集群为{}").format(inst, cluster_ids))

    def validate_database_table_selector(self, attrs, role_key=None):
        """校验库表选择器的数据是否合法"""
        is_valid, message = CommonValidate.validate_database_table_selector(
            bk_biz_id=self.context["bk_biz_id"], infos=attrs["infos"], role_key=role_key
        )
        if not is_valid:
            raise serializers.ValidationError(message)

    def validate_slave_is_stand_by(self, attrs):
        """校验从库的is_stand_by标志必须为true"""
        slave_insts = [f"{info['slave_ip']['ip']}" for info in attrs["infos"]]
        CommonValidate.validate_slave_is_stand_by(slave_insts)

    def validate(self, attrs):
        # 默认全局校验只需要校验集群的状态
        self.validate_cluster_can_access(attrs)
        return attrs


class MySQLClustersTakeDownDetailsSerializer(SkipToRepresentationMixin, serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID"), child=serializers.IntegerField())
    force = serializers.BooleanField(help_text=_("是否强制下架"), required=False, default=False)

    @classmethod
    def clusters_status_transfer_valid(cls, cluster_ids: List[int], ticket_type: str):
        cluster_list = Cluster.objects.filter(id__in=cluster_ids)
        for cluster in cluster_list:
            ticket_cluster_phase = BuilderFactory.ticket_type__cluster_phase.get(ticket_type)
            if not ClusterPhase.cluster_status_transfer_valid(cluster.phase, ticket_cluster_phase):
                raise ValidationError(
                    _("集群{}状态转移不合法：{}--->{} is invalid").format(cluster.name, cluster.phase, ticket_cluster_phase)
                )

    def validate_cluster_ids(self, value):
        self.clusters_status_transfer_valid(cluster_ids=value, ticket_type=self.context["ticket_type"])
        return value


class MySQLBaseOperateResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        super().format()

    def post_callback(self):
        super().post_callback()


class DBTableField(serializers.CharField):
    """
    库表备份的专属字段
    """

    # 库表匹配正则
    db_tb_pattern = re.compile("^[-_a-zA-Z0-9\*\?%]{0,35}$")  # noqa: W605
    # 是否为库
    db_field = False

    def __init__(self, **kwargs):
        self.db_field = kwargs.pop("db_field", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        """
        库表字段校验规则：
        1. 库表只能由`[0-9],[a-z],[A-Z],-,_` 组成，(某些单据)支持*/%/?通配符
        2. % ? 不能独立使用
        3. * 只能独立使用
        4. 如果为库字段，则不允许出现系统库
        """
        data = super().to_internal_value(data)

        # 库表字符集校验
        if not self.db_tb_pattern.match(data):
            raise serializers.ValidationError(_("【库表字段校验】库表只能由`[0-9],[a-z],[A-Z],-,_` 组成，(某些单据)支持*/%/?通配符。库表长度最大为35"))

        # 库表通配符规则校验
        try:
            glob_check(patterns=[data])
        except DbTableFilterValidateException as e:
            raise serializers.ValidationError(_("【库表字段校验】{}").format(e.message))

        # 系统库字段校验
        if self.db_field:
            if data in SYSTEM_DBS and data != "test":
                raise serializers.ValidationError(_("【库表字段校验】不允许系统库(除test)做任何变更类操作"))
            if data.startswith("stage_truncate"):
                raise serializers.ValidationError(_("【库表字段校验】DB名{}不能以stage_truncate开头").format(data))
            if data.endswith("dba_rollback"):
                raise serializers.ValidationError(_("【库表字段校验】DB名{}不能以dba_rollback结尾").format(data))

        return data

    def to_representation(self, value):
        return super().to_representation(value)
