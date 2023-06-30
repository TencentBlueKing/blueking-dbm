# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import DBRESOURCE_APIGW_DOMAIN


class _DBResourceApi(object):
    MODULE = _("资源池 服务")

    def __init__(self):
        self.resource_import = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/import",
            module=self.MODULE,
            description=_("资源导入"),
        )
        self.resource_list = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/list",
            module=self.MODULE,
            description=_("资源池资源列表"),
        )
        self.resource_list_all = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/list/all",
            module=self.MODULE,
            description=_("资源池全部资源列表"),
        )
        self.resource_apply = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/apply",
            module=self.MODULE,
            description=_("资源池资源申请"),
        )
        self.get_mountpoints = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/mountpoints",
            module=self.MODULE,
            description=_("获取挂载点"),
        )
        self.get_disktypes = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/disktypes",
            module=self.MODULE,
            description=_("获取磁盘类型"),
        )
        self.get_subzones = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/subzones",
            module=self.MODULE,
            description=_("根据逻辑城市查询园区"),
        )
        self.resource_pre_apply = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/pre-apply",
            module=self.MODULE,
            description=_("资源申请预占用"),
        )
        self.resource_confirm = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/confirm/apply",
            module=self.MODULE,
            description=_("资源申请确认"),
        )
        self.resource_delete = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/delete",
            module=self.MODULE,
            description=_("资源删除"),
        )
        self.resource_update = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="resource/update",
            module=self.MODULE,
            description=_("资源更新"),
        )
        self.get_device_class = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="/resource/deviceclass",
            module=self.MODULE,
            description=_("获取机型List"),
        )
        self.operation_list = DataAPI(
            method="POST",
            base=DBRESOURCE_APIGW_DOMAIN,
            url="/resource/operation/list",
            module=self.MODULE,
            description=_("获取操作记录"),
        )


DBResourceApi = _DBResourceApi()
