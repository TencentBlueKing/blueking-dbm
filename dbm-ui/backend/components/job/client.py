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
from ..domains import JOB_APIGW_DOMAIN


class _JobApi(object):
    MODULE = _("作业平台")

    def __init__(self):
        self.fast_execute_script = DataAPI(
            method="POST",
            base=JOB_APIGW_DOMAIN,
            url="fast_execute_script/",
            module=self.MODULE,
            description=_("快速执行脚本"),
        )
        self.fast_transfer_file = DataAPI(
            method="POST",
            base=JOB_APIGW_DOMAIN,
            url="fast_transfer_file/",
            module=self.MODULE,
            description=_("快速分发文件"),
        )
        self.push_config_file = DataAPI(
            method="POST",
            base=JOB_APIGW_DOMAIN,
            url="push_config_file/",
            module=self.MODULE,
            description=_("快速分发配置"),
        )
        self.get_job_instance_status = DataAPI(
            method="GET",
            base=JOB_APIGW_DOMAIN,
            url="get_job_instance_status/",
            module=self.MODULE,
            description=_("查询作业执行状态"),
        )
        self.get_job_instance_ip_log = DataAPI(
            method="GET",
            base=JOB_APIGW_DOMAIN,
            url="get_job_instance_ip_log/",
            module=self.MODULE,
            description=_("根据作业实例ID查询作业执行日志"),
        )
        self.batch_get_job_instance_ip_log = DataAPI(
            method="POST",
            base=JOB_APIGW_DOMAIN,
            url="batch_get_job_instance_ip_log/",
            module=self.MODULE,
            description=_("根据ip列表批量查询作业执行日志"),
        )
        self.create_credential = DataAPI(
            method="POST",
            base=JOB_APIGW_DOMAIN,
            url="create_credential/",
            module=self.MODULE,
            description=_("新建凭据"),
        )
        self.create_file_source = DataAPI(
            method="POST",
            base=JOB_APIGW_DOMAIN,
            url="create_file_source/",
            module=self.MODULE,
            description=_("新建文件源"),
        )


JobApi = _JobApi()
