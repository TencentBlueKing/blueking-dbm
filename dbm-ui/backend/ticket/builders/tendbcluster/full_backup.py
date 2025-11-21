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
import collections

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import MySQLBackupFileTagEnum, MySQLBackupTypeEnum
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TenDBClusterFullBackUpDetailSerializer(TendbBaseOperateDetailSerializer):
    class TenDBClusterFullBackupInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        backup_local = serializers.CharField(help_text=_("备份位置信息"), default=InstanceInnerRole.SLAVE)
        spider_mnt_address = serializers.CharField(help_text=_("运维节点地址"), required=False)

    backup_type = serializers.ChoiceField(help_text=_("备份选项"), choices=MySQLBackupTypeEnum.get_choices())
    file_tag = serializers.ChoiceField(help_text=_("备份保存时间"), choices=MySQLBackupFileTagEnum.get_choices())

    infos = serializers.ListSerializer(child=TenDBClusterFullBackupInfoSerializer())

    @classmethod
    def get_backup_local_params(cls, info):
        """
        对备份位置进行提取，
        两种情况：remote/spider_mnt::127.0.0.1
        """
        divider = "::"
        if divider not in info["backup_local"]:
            return info

        backup_local, spider_mnt_address = info["backup_local"].split(divider)
        info["backup_local"] = backup_local
        info["spider_mnt_address"] = spider_mnt_address

        return info

    def validate(self, attrs):
        attrs = super(TendbBaseOperateDetailSerializer, self).validate(attrs)
        for cluster_info in attrs["infos"]:
            self.get_backup_local_params(cluster_info)

        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]

        errors = []

        msg = self.__validate_cluster_id_unique(cluster_ids=cluster_ids)
        if msg:
            errors.append(msg)

        msg = self.__validate_cluster_type(cluster_ids=cluster_ids)
        if msg:
            errors.append(msg)

        msg = self.__validate_cluster_exists(cluster_ids=cluster_ids)
        if msg:
            errors.append(msg)

        msg = self.__validate_backup_local(attrs=attrs)
        if msg:
            errors.append(msg)

        msg = self.__validate_cluster_status(attrs=attrs)
        if msg:
            errors.append(msg)

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    @staticmethod
    def __validate_cluster_id_unique(cluster_ids) -> str:
        """
        集群 id 不能重复出现
        """
        dup_cluster_ids = [cid for cid, cnt in collections.Counter(cluster_ids).items() if cnt > 1]
        if dup_cluster_ids:
            return _(
                "重复输入集群: {}".format(
                    Cluster.objects.filter(pk__in=dup_cluster_ids).values_list("immute_domain", flat=True)
                )
            )

    @staticmethod
    def __validate_cluster_type(cluster_ids) -> str:
        """
        集群类型不能混合
        """
        bad = list(
            Cluster.objects.filter(pk__in=cluster_ids)
            .exclude(cluster_type=ClusterType.TenDBCluster)
            .values_list("immute_domain", flat=True)
        )
        if bad:
            return _("不支持的集群类型 {}".format(", ".join(bad)))

    @staticmethod
    def __validate_cluster_exists(cluster_ids) -> str:
        """
        集群 id 必须存在
        """
        exists_cluster_ids = list(
            Cluster.objects.filter(pk__in=cluster_ids, cluster_type=ClusterType.TenDBCluster).values_list(
                "id", flat=True
            )
        )
        not_exists_cluster_ids = list(set(cluster_ids) - set(exists_cluster_ids))
        if not_exists_cluster_ids:
            return _("cluster id: {} 不存在".format(cluster_ids))

    @staticmethod
    def __validate_backup_local(attrs):
        bad = []

        for info in attrs["infos"]:
            backup_local = info["backup_local"]
            if backup_local not in ["master", "slave", "spider_mnt"]:
                bad.append(str(_("不支持的备份位置 {}".format(backup_local))))

            if backup_local == "spider_mnt" and "spider_mnt_address" not in info:
                bad.append(str(_("缺少 spider_mnt_address")))

        if bad:
            return ", ".join(list(set(bad)))

    @staticmethod
    def __validate_cluster_status(attrs):
        bad = []
        for info in attrs["infos"]:
            cluster_id = info["cluster_id"]
            backup_local = info["backup_local"]
            cluster_obj = Cluster.objects.get(pk=cluster_id)
            if (
                backup_local == "spider_mnt"
                and not cluster_obj.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MNT, status=InstanceStatus.RUNNING
                ).exists()
            ):
                bad.append(cluster_obj.immute_domain)
            elif (
                backup_local in ["remote", "slave"]
                and cluster_obj.storageinstance_set.filter(instance_inner_role=backup_local, is_stand_by=True)
                .exclude(status=InstanceStatus.RUNNING)
                .exists()
            ):
                bad.append(cluster_obj.immute_domain)

        if bad:
            return _("集群状态异常: {}".format(", ".join(list(set(bad)))))


class TenDBClusterFullBackUpFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.full_backup


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_FULL_BACKUP)
class TenDBClusterFullBackUpFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TenDBClusterFullBackUpDetailSerializer
    inner_flow_builder = TenDBClusterFullBackUpFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 全库备份")
