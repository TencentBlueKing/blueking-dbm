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
from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import PARTITION_APIGW_DOMAIN


class _PartitionApi(object):
    MODULE = _("分区管理")

    def __init__(self):
        self.dry_run = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/dry_run",
            module=self.MODULE,
            description=_("获取分区语句"),
        )

        self.create_conf = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/create_conf",
            module=self.MODULE,
            description=_("添加分区配置"),
        )

        self.del_conf = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/del_conf",
            module=self.MODULE,
            description=_("删除分区配置"),
        )

        self.cluster_del_conf = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/cluster_del_conf",
            module=self.MODULE,
            description=_("cluster_del_conf"),
        )

        self.update_conf = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/update_conf",
            module=self.MODULE,
            description=_("修改分区配置"),
        )

        self.query_conf = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/query_conf",
            module=self.MODULE,
            description=_("查询分区配置"),
        )

        self.enable_partition = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/enable_partition",
            module=self.MODULE,
            description=_("启用分区"),
        )

        self.disable_partition = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/disable_partition",
            module=self.MODULE,
            description=_("禁用分区"),
        )

        self.query_log = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/query_log",
            module=self.MODULE,
            description=_("查询分区日志"),
        )

        self.create_log = DataAPI(
            method="POST",
            base=PARTITION_APIGW_DOMAIN,
            url="partition/create_log",
            module=self.MODULE,
            description=_("创建分区操作日志"),
        )


DBPartitionApi = _PartitionApi()
