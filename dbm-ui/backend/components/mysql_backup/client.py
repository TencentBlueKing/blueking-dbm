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
from ..domains import BACKUP_APIGW_DOMAIN


class _BackupApi(BaseApi):
    MODULE = _("备份文件下载")
    BASE = BACKUP_APIGW_DOMAIN

    def __init__(self):
        self.query = self.generate_data_api(
            method="POST",
            url="backupapi/query",
            description=_("获取备份"),
        )
        self.download = self.generate_data_api(
            method="POST",
            url="backupapi/recover",
            description=_("备份文件下载"),
        )

        self.download_result = self.generate_data_api(
            method="GET",
            url="backupapi/get_recover_result",
            description=_("查询单据状态"),
        )
        self.download_backup_client = self.generate_data_api(
            method="POST",
            url="backupapi/client/install",
            description=_("backup_client下载，同步任务"),
            default_timeout=600,
            max_retry_times=1,
        )


MysqlBackupApi = _BackupApi()
RedisBackupApi = _BackupApi()
