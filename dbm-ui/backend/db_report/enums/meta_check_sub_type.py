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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class MetaCheckSubType(StrStructuredEnum):
    InstanceBelong = EnumField("instance_belong", _("实例集群归属"))
    ReplicateRole = EnumField("replicate_role", _("数据同步实例角色"))
    ClusterTopo = EnumField("cluster_topo", _("集群结构"))
    AloneInstance = EnumField("alone_instance", _("孤立的实例"))
    StatusAbnormal = EnumField("status_abnormal", _("不属于RUNNING状态"))
    # tendbha
    TenDBHAProxyBindWrongBackendRole = EnumField("proxy_bind_wrong_backend_role", _("proxy bind backend 角色错误"))
    TenDBHAProxyCountNotMatch = EnumField("proxy_count_not_match", _("访问入口关联 proxy 数和集群 proxy 数不相等"))
    TenDBHAMasterEntryBindStorage = EnumField("master_entry_bind_storage", _("主访问入口指向存储实例"))
    TenDBHAMasterAsReceiver = EnumField("master_as_receiver", _("master 在同步其他实例"))
    TenDBHASlaveAsEjector = EnumField("slave_as_ejector", _("slave 是同步的源"))
    TenDBHARepWithOtherCluster = EnumField("rep_with_other_cluster", _("和其他集群存在同步"))
    TenDBHAClusterAbnormal = EnumField("cluster_abnormal", _("集群状态异常"))
    TenDBHAInstanceAbnormal = EnumField("instance_abnormal", _("实例状态异常"))
    TenDBHAMissingMasterEntry = EnumField("missing_master_entry", _("缺少主访问入口"))
    TenDBHAShortProxy = EnumField("short_proxy", _("proxy 数量不足"))
    TenDBHANoMaster = EnumField("no_master", _("无 master 实例"))
    TenDBHATooManyMaster = EnumField("too_many_master", _("大于 1 个 master 实例"))
    TenDBHAMasterBadStatus = EnumField("master_bad_status", _("master status, phase, standby 状态异常"))
    TenDBHANoStandbySlave = EnumField("no_standby_slave", _("缺少 standby slave"))
    TenDBHATooManyStandbySlave = EnumField("too_many_standby_slave", _("大于 1 个 standby slave"))
    TenDBHAStandbySlaveBadStatus = EnumField(
        "standby_slave_bad_status", _("standby slave status, phase, standby 状态异常")
    )
    TenDBHAMultiClusterBelong = EnumField("multi_cluster_belong", _("实例属于多个集群"))
    # tendbcluster
    TenDBClusterSpiderBindWrongRole = EnumField("spider_bind_wrong_role", _("spider 访问错误 remote 角色"))
    TenDBClusterRemoteCountNotMatch = EnumField(
        "remote_count_not_match", _("spider bind 的 remote 实例数和集群 master 实例数不相等")
    )
    TenDBClusterSpiderCountNotMatch = EnumField("spider_count_not_match", _("访问入口关联 spider 实例数和集群 spider 实例数不相等"))
    TenDBClusterEntryBindStorage = EnumField("entry_bind_storage", _("访问入口指向存储实例"))
    TenDBClusterShortSpider = EnumField("short_spider", _("spider 数量不足"))
    TenDBClusterShardCountNotMatch = EnumField("shard_count_not_match", _("分片数和实例数不相等"))
    TenDBClusterNoStandbySlave = EnumField("no_standby_slave", _("没有 standby slave"))
    TenDBClusterTooManyStandbySlave = EnumField("too_many_standby_slave", _("大于 1 个 standby slave"))
