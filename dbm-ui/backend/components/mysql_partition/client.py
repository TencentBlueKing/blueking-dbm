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

from ..base import BaseApi
from ..domains import PARTITION_APIGW_DOMAIN


class _PartitionApi(BaseApi):
    MODULE = _("分区管理")
    BASE = PARTITION_APIGW_DOMAIN

    def __init__(self):
        self.dry_run = self.generate_data_api(
            method="POST",
            url="partition/dry_run",
            description=_("获取分区语句"),
        )
        self.create_conf = self.generate_data_api(
            method="POST",
            url="partition/create_conf",
            description=_("添加分区配置"),
        )
        self.del_conf = self.generate_data_api(
            method="POST",
            url="partition/del_conf",
            description=_("删除分区配置"),
        )
        self.cluster_del_conf = self.generate_data_api(
            method="POST",
            url="partition/cluster_del_conf",
            description=_("cluster_del_conf"),
        )
        self.update_conf = self.generate_data_api(
            method="POST",
            url="partition/update_conf",
            description=_("修改分区配置"),
        )
        self.query_conf = self.generate_data_api(
            method="POST",
            url="partition/query_conf",
            description=_("查询分区配置"),
        )
        self.enable_partition = self.generate_data_api(
            method="POST",
            url="partition/enable_partition",
            description=_("启用分区"),
        )
        self.disable_partition = self.generate_data_api(
            method="POST",
            url="partition/disable_partition",
            description=_("禁用分区"),
        )
        self.enable_partition_cluster = self.generate_data_api(
            method="POST",
            url="partition/enable_partition_cluster",
            description=_("开启分区"),
        )
        self.disable_partition_cluster = self.generate_data_api(
            method="POST",
            url="partition/disable_partition_cluster",
            description=_("禁用分区"),
        )
        self.query_log = self.generate_data_api(
            method="POST",
            url="partition/query_log",
            description=_("查询分区日志"),
        )
        self.create_log = self.generate_data_api(
            method="POST",
            url="partition/create_log",
            description=_("创建分区操作日志"),
        )
        self.check_log = self.generate_data_api(
            method="POST",
            url="partition/check_log",
            description=_("获取巡检日志"),
            default_timeout=300,
            max_retry_times=1,
        )

        self.partition_conf_query = self.generate_data_api(
            method="Post", url="/partition/partition_conf_query", description=_("分区配置查询")
        )

        # v2 分区配置相关接口
        self.query_conf_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/query_conf",
            description=_("查询分区配置v2"),
        )
        self.create_conf_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/create_conf",
            description=_("添加分区配置v2"),
        )
        self.clone_conf_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/clone_conf",
            description=_("克隆分区配置v2"),
        )
        self.update_conf_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/update_conf",
            description=_("修改分区配置v2"),
        )
        self.del_conf_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/del_conf",
            description=_("删除分区配置v2"),
        )
        self.enable_partition_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/enable_partition",
            description=_("启用分区v2"),
        )
        self.disable_partition_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/disable_partition",
            description=_("禁用分区v2"),
        )
        # v2 集群删除后清理对应分区配置
        self.cluster_del_conf_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/cluster_del_conf",
            description=_("cluster_del_conf_v2"),
        )
        # v2 集群启用后开启对应分区
        self.enable_partition_cluster_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/enable_partition_cluster",
            description=_("开启分区"),
        )
        # v2 集群禁用后禁用对应分区
        self.disable_partition_cluster_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/disable_partition_cluster",
            description=_("禁用分区"),
        )
        # v2 巡检：按 cluster_type 分页列出待检业务（含 db_app_abbr、配置总数）
        self.list_check_biz_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/check/list_biz",
            description=_("分区v2巡检-按业务分页列表"),
            default_timeout=300,
            max_retry_times=1,
        )
        # v2 巡检：按 cluster_type + bk_biz_id 分页返回待检 config_id（服务端已做 phase/create_time 过滤）
        self.list_check_conf_ids_v2 = self.generate_data_api(
            method="POST",
            url="partition/v2/check/list_conf_ids",
            description=_("分区v2巡检-按业务分页配置ID"),
            default_timeout=300,
            max_retry_times=1,
        )


DBPartitionApi = _PartitionApi()
