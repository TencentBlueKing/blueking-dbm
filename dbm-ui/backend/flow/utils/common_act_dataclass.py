"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.flow.consts import BACKUP_DEFAULT_OS_USER


@dataclass()
class DownloadBackupClientKwargs:
    """
    定义下载并安装backup_client
    BACKUP_DEFAULT_OS_USER = mysql
    """

    bk_cloud_id: int
    bk_biz_id: int
    download_host_list: list
    backup_os_user: str = BACKUP_DEFAULT_OS_USER


@dataclass()
class DNSContext:
    redis_act_payload: Optional[Any] = None  # 代表获取payload参数的类
    resolv_content: dict = field(default_factory=dict)
