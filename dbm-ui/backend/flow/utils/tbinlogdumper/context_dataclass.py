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


@dataclass()
class TBinlogDumperAddContext:
    """
    定义添加Tbinlogdumper的可交互上下文dataclass类
    """

    master_ip_sync_info: dict = field(default_factory=dict)  # 代表获取到master的主从复制位点信息
    backup_info: dict = field(default_factory=dict)  # 代表做全量同步时备份信息

    @staticmethod
    def get_sync_info_var_name() -> str:
        return "master_ip_sync_info"


@dataclass
class StopSlaveKwargs:
    """
    定义tbinlogdumper 执行stop slave的私有变量
    """

    bk_cloud_id: int
    tbinlogdumper_ip: str
    tbinlogdumper_port: int
    is_safe: bool


@dataclass
class TBinlogDumperFullSyncDataKwargs:
    """
    定义为tbinlogdumper实例同步的私有变量
    """

    bk_cloud_id: int
    backup_ip: str
    backup_port: int
    backup_role: str
    module_id: int
