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

from ..base import BaseApi
from ..domains import DBCONFIG_APIGW_DOMAIN
from ..utils.handlers import get_first_item_from_list


class _DBConfigApi(BaseApi):
    MODULE = _("DB配置系统")
    BASE = DBCONFIG_APIGW_DOMAIN

    def __init__(self):
        self.add_conf_file = self.generate_data_api(
            method="POST",
            url="bkconfig/v1/conffile/add",
            description=_("新增平台级配置文件"),
        )
        self.list_conf_file = self.generate_data_api(
            method="GET",
            url="bkconfig/v1/conffile/list",
            description=_("查询配置文件列表"),
        )
        self.update_conf_file = self.generate_data_api(
            method="POST",
            url="bkconfig/v1/conffile/update",
            description=_("编辑平台级配置"),
        )
        self.query_conf_file = self.generate_data_api(
            method="GET",
            url="bkconfig/v1/conffile/query",
            description=_("查询公共配置项列表"),
        )
        self.list_conf_name = self.generate_data_api(
            method="GET",
            url="bkconfig/v1/confname/list",
            description=_("查询定义的配置名列表"),
        )
        self.query_conf_item = self.generate_data_api(
            method="POST",
            url="bkconfig/v1/confitem/query",
            description=_("查询配置项列表"),
            # 这里保证每个版本在统一层级只会有一份配置文件
            after_request=get_first_item_from_list,
        )
        self.save_conf_item = self.generate_data_api(
            method="POST",
            url="bkconfig/v1/confitem/save",
            description=_("保存不可变配置（如字符集等）"),
        )
        self.upsert_conf_item = self.generate_data_api(
            method="POST",
            url="bkconfig/v1/confitem/upsert",
            description=_("编辑发布层级（业务、集群、模块）配置"),
        )
        self.batch_get_conf_item = self.generate_data_api(
            method="POST",
            url="bkconfig/v1/confitem/batchget",
            description=_("批量获取多个对象的某一配置项"),
        )
        self.list_version = self.generate_data_api(
            method="GET",
            url="bkconfig/v1/version/list",
            description=_("查询历史配置版本名列表"),
        )
        self.version_detail = self.generate_data_api(
            method="GET",
            url="bkconfig/v1/version/detail",
            description=_("查询版本详细信息"),
        )
        self.get_or_generate_instance_config = self.generate_data_api(
            method="POST",
            url="bkconfig/v1/version/generate",
            description=_("查询实例配置文件模版"),
        )


DBConfigApi = _DBConfigApi()
