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
from ..domains import JOB_APIGW_DOMAIN


class _JobApi(BaseApi):
    MODULE = _("作业平台")
    BASE = JOB_APIGW_DOMAIN

    def __init__(self):
        self.fast_execute_script = self.generate_data_api(
            method="POST",
            url="fast_execute_script/",
            description=_("快速执行脚本"),
        )
        self.fast_transfer_file = self.generate_data_api(
            method="POST",
            url="fast_transfer_file/",
            description=_("快速分发文件"),
        )
        self.push_config_file = self.generate_data_api(
            method="POST",
            url="push_config_file/",
            description=_("快速分发配置"),
        )
        self.get_job_instance_status = self.generate_data_api(
            method="GET",
            url="get_job_instance_status/",
            description=_("查询作业执行状态"),
        )
        self.get_job_instance_ip_log = self.generate_data_api(
            method="GET",
            url="get_job_instance_ip_log/",
            description=_("根据作业实例ID查询作业执行日志"),
        )
        self.batch_get_job_instance_ip_log = self.generate_data_api(
            method="POST",
            url="batch_get_job_instance_ip_log/",
            description=_("根据ip列表批量查询作业执行日志"),
        )
        self.create_credential = self.generate_data_api(
            method="POST",
            url="create_credential/",
            description=_("新建凭据"),
        )
        self.create_file_source = self.generate_data_api(
            method="POST",
            url="create_file_source/",
            description=_("新建文件源"),
        )
        self.create_account = self.generate_data_api(
            method="POST",
            url="create_account/",
            description=_("创建账号"),
        )
        self.get_account_list = self.generate_data_api(
            method="POST",
            url="get_account_list/",
            description=_("查询账号列表"),
        )


JobApi = _JobApi()
