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

from ..base import BaseApi
from ..domains import DBRESOURCE_APIGW_DOMAIN


class _DBResourceApi(BaseApi):
    MODULE = _("资源池 服务")
    BASE = DBRESOURCE_APIGW_DOMAIN

    def __init__(self):
        self.resource_import = self.generate_data_api(
            method="POST",
            url="resource/import",
            description=_("资源导入"),
        )
        self.resource_list = self.generate_data_api(
            method="POST",
            url="resource/list",
            description=_("资源池资源列表"),
        )
        self.resource_list_all = self.generate_data_api(
            method="POST",
            url="resource/list/all",
            description=_("资源池全部资源列表"),
        )
        self.resource_apply = self.generate_data_api(
            method="POST",
            url="resource/apply",
            description=_("资源池资源申请"),
        )
        self.get_mountpoints = self.generate_data_api(
            method="POST",
            url="resource/mountpoints",
            description=_("获取挂载点"),
        )
        self.get_disktypes = self.generate_data_api(
            method="POST",
            url="resource/disktypes",
            description=_("获取磁盘类型"),
        )
        self.get_subzones = self.generate_data_api(
            method="POST",
            url="resource/subzones",
            description=_("根据逻辑城市查询园区"),
        )
        self.resource_pre_apply = self.generate_data_api(
            method="POST",
            url="resource/pre-apply",
            description=_("资源申请预占用"),
        )
        self.resource_confirm = self.generate_data_api(
            method="POST",
            url="resource/confirm/apply",
            description=_("资源申请确认"),
        )
        self.resource_delete = self.generate_data_api(
            method="POST",
            url="resource/delete",
            description=_("资源删除"),
        )
        self.resource_update = self.generate_data_api(
            method="POST",
            url="resource/update",
            description=_("资源更新"),
        )
        self.resource_batch_update = self.generate_data_api(
            method="POST",
            url="resource/batch/update",
            description=_("资源批量更新"),
        )
        self.get_device_class = self.generate_data_api(
            method="POST",
            url="/resource/deviceclass",
            description=_("获取机型List"),
        )
        self.operation_list = self.generate_data_api(
            method="POST",
            url="/resource/operation/list",
            description=_("获取操作记录"),
        )
        self.import_operation_create = self.generate_data_api(
            method="POST",
            url="/resource/operation/create",
            description=_("创建导入操作记录"),
        )
        self.apply_count = self.generate_data_api(
            method="POST",
            url="/resource/spec/sum",
            description=_("预申请获取资源数量"),
        )


DBResourceApi = _DBResourceApi()
