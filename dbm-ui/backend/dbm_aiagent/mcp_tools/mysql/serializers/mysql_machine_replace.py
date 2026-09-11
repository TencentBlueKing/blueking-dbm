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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.ticket.builders.common.constants import MySQLBackupSource, OperaObjType


class SubmitBillMySQLMachineReplaceSerializer(serializers.Serializer):
    cluster_domains = serializers.ListField(child=serializers.CharField(), help_text=_("域名列表"))
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("待替换 ip 列表"))


class SubmitBillTenDBClusterMachineReplaceSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("域名列表"))
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("待替换 ip 列表"))


class SubmitBillMySQLProxyConfChangeSerializer(serializers.Serializer):
    class ProxyConfChangeInfoSerializer(serializers.Serializer):
        cluster_domain = serializers.CharField(help_text=_("集群域名"))
        target_spec_id = serializers.IntegerField(help_text=_("目标规格 ID"))
        labels = serializers.ListField(
            child=serializers.CharField(), help_text=_("资源标签 ID 列表"), default=[], required=False
        )

    infos = serializers.ListField(
        child=ProxyConfChangeInfoSerializer(), help_text=_("升降配信息（每行一个集群）"), allow_empty=False
    )


class SubmitBillMySQLMigrateClusterSerializer(serializers.Serializer):
    class MigrateInfoSerializer(serializers.Serializer):
        cluster_domain = serializers.CharField(help_text=_("集群域名"))
        spec_id = serializers.IntegerField(help_text=_("目标规格 ID"))
        count = serializers.IntegerField(help_text=_("机器组数（1组=1主+1从）"), default=1, required=False)
        labels = serializers.ListField(
            child=serializers.CharField(), help_text=_("资源标签 ID 列表"), default=[], required=False
        )

    infos = serializers.ListField(child=MigrateInfoSerializer(), help_text=_("迁移信息（每行一个集群）"), allow_empty=False)
    opera_object = serializers.ChoiceField(
        choices=[
            (OperaObjType.CLUSTER.value, _("集群迁移")),
            (OperaObjType.MACHINE.value, _("整机迁移")),
        ],
        help_text=_("迁移类型：cluster=集群迁移，machine=整机迁移"),
    )
    backup_source = serializers.ChoiceField(
        help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), default=MySQLBackupSource.REMOTE, required=False
    )
    need_checksum = serializers.BooleanField(help_text=_("执行前是否需要数据校验"), default=True, required=False)
    is_safe = serializers.BooleanField(help_text=_("安全模式"), default=True, required=False)


class SubmitBillSpiderConfChangeSerializer(serializers.Serializer):
    class SpiderConfChangeInfoSerializer(serializers.Serializer):
        cluster_domain = serializers.CharField(help_text=_("集群域名"))
        spider_role = serializers.ChoiceField(
            choices=[
                (TenDBClusterSpiderRole.SPIDER_MASTER.value, _("主接入层")),
                (TenDBClusterSpiderRole.SPIDER_SLAVE.value, _("从接入层")),
            ],
            help_text=_("接入层角色：spider_master=主接入层，spider_slave=从接入层"),
        )
        target_spec_id = serializers.IntegerField(help_text=_("目标规格 ID"))
        labels = serializers.ListField(
            child=serializers.CharField(), help_text=_("资源标签 ID 列表"), default=[], required=False
        )

    infos = serializers.ListField(
        child=SpiderConfChangeInfoSerializer(), help_text=_("升降配信息（每行一个集群）"), allow_empty=False
    )


class SubmitBillTendbClusterNodeRebalanceSerializer(serializers.Serializer):
    class NodeRebalanceInfoSerializer(serializers.Serializer):
        cluster_domain = serializers.CharField(help_text=_("集群域名"))
        spec_id = serializers.IntegerField(help_text=_("目标规格 ID"))
        count = serializers.IntegerField(help_text=_("目标机器组数"), default=1, required=False)
        labels = serializers.ListField(
            child=serializers.CharField(), help_text=_("资源标签 ID 列表"), default=[], required=False
        )

    infos = serializers.ListField(
        child=NodeRebalanceInfoSerializer(), help_text=_("容量变更信息（每行一个集群）"), allow_empty=False
    )
    backup_source = serializers.ChoiceField(
        help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), default=MySQLBackupSource.REMOTE, required=False
    )
    need_checksum = serializers.BooleanField(help_text=_("执行前是否需要数据校验"), default=True, required=False)
