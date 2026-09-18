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

from backend.flow.consts import SqlserverBackupFileTagEnum, SqlserverBackupMode


class SubmitSQLServerClusterMigrateSerializer(serializers.Serializer):
    class ClusterMigrateInfoSerializer(serializers.Serializer):
        cluster_domain = serializers.CharField(help_text=_("集群域名"))
        spec_id = serializers.IntegerField(help_text=_("目标规格 ID"))
        count = serializers.IntegerField(help_text=_("机器组数（1组=1主+1从）"), default=1, required=False)
        labels = serializers.ListField(
            child=serializers.CharField(), help_text=_("资源标签 ID 列表"), default=[], required=False
        )

    infos = serializers.ListField(child=ClusterMigrateInfoSerializer(), help_text=_("迁移信息（每行一个集群）"), allow_empty=False)


class SubmitSQLServerHostMigrateSerializer(serializers.Serializer):
    class HostMigrateInfoSerializer(serializers.Serializer):
        cluster_domains = serializers.ListField(
            child=serializers.CharField(), help_text=_("待迁移集群域名列表（同机关联集群）"), allow_empty=False
        )
        ip = serializers.CharField(help_text=_("源主机 IP"))
        spec_id = serializers.IntegerField(help_text=_("目标规格 ID"))
        count = serializers.IntegerField(help_text=_("机器组数（1组=1主+1从）"), default=1, required=False)
        labels = serializers.ListField(
            child=serializers.CharField(), help_text=_("资源标签 ID 列表"), default=[], required=False
        )

    infos = serializers.ListField(child=HostMigrateInfoSerializer(), help_text=_("整机迁移信息（每行一台源主机）"), allow_empty=False)


class SubmitSQLServerMasterSlaveSwitchSerializer(serializers.Serializer):
    cluster_domains = serializers.ListField(child=serializers.CharField(), help_text=_("集群域名列表"))
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("master ip 列表（仅支持单个）"))


class SubmitSQLServerRestoreLocalSlaveSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("slave ip 列表（仅支持单个）"))


class SubmitSQLServerRestoreSlaveSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("旧 slave ip 列表（仅支持单个）"))
    spec_id = serializers.IntegerField(help_text=_("新机目标规格 ID"))
    labels = serializers.ListField(
        child=serializers.CharField(), help_text=_("资源标签 ID 列表"), default=[], required=False
    )


class SubmitSQLServerBackupDbsSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    backup_dbs = serializers.ListField(child=serializers.CharField(), help_text=_("需要备份的库名列表"))
    file_tag = serializers.ChoiceField(
        help_text=_("备份保存时间"),
        choices=SqlserverBackupFileTagEnum.get_choices(),
        default="DBFILE1M",
        required=False,
    )
    backup_type = serializers.ChoiceField(
        help_text=_("备份方式"),
        choices=SqlserverBackupMode.get_choices(),
        default="full_backup",
        required=False,
    )
    backup_place = serializers.CharField(help_text=_("备份位置（固定为 master）"), default="master", required=False)
