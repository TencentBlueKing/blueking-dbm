"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from dataclasses import dataclass, field, fields
from typing import Any, List, Optional

from backend import env
from backend.db_dirty.constants import MachineEventType
from backend.flow.consts import BACKUP_DEFAULT_OS_USER


@dataclass
class IgnoreNotExistFieldDataclass:
    """
    实现一个自定义类，忽略dataclass中不存在的字段
    """

    def __post_init__(self):
        pass

    def __init__(self, **kwargs):
        field_names = {f.name for f in fields(self.__class__)}
        kwargs = {k: v for k, v in kwargs.items() if k in field_names}
        for k, v in kwargs.items():
            setattr(self, k, v)


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
    common_act_payload: Optional[Any] = None  # 代表获取payload参数的类
    resolv_content: dict = field(default_factory=dict)


@dataclass
class InstallNodemanPluginKwargs:
    """
    定义安装插件的私有变量结构体
    """

    plugin_name: str
    bk_host_ids: List[int] = None
    ips: List[str] = None
    bk_cloud_id: int = None


@dataclass()
class FailoverDrillContext:
    """
    容灾演练相关上下文参数
    """

    schedule_count: int = 1


@dataclass
class InitCheckKwargs:
    """
    定义空闲检查的私有变量结构体
    """

    bk_cloud_id: int
    ips: list
    account_name: str = "root"


@dataclass
class InitCheckForResourceKwargs:
    """
    定义导入资源池的场景下空闲检查的私有变量结构体
    """

    ips: list
    bk_biz_id: int = env.DBA_APP_BK_BIZ_ID
    account_name: str = "root"
    strict_idle_check: bool = False


@dataclass
class ImportMachinePollKwargs:
    """
    定义导入主机池的私有变量结构体
    """

    bk_biz_id: int
    db_type: str
    cluster_type: str
    operator: str
    ticket_id: int
    event: MachineEventType = ""
    hosts: list = None


@dataclass
class ResourceHcmReplenishKwargs:
    """
    定义资源池补货的私有变量结构体
    """

    city: str
    subzone: str
    os_name: str
    spec_id: int
    count: int


@dataclass
class ResourceImportContext(IgnoreNotExistFieldDataclass):
    """
    资源导入相关上下文参数
    """

    hosts: List[dict] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
