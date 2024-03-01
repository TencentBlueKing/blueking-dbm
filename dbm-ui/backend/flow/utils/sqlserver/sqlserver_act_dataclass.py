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
from typing import List, Optional

from backend.flow.consts import (
    DEFAULT_JOB_TIMEOUT,
    DEFAULT_SQLSERVER_PATH,
    MediumFileTypeEnum,
    SqlserverBackupJobExecMode,
    SqlserverLoginExecMode,
    SqlserverRestoreDBStatus,
    SqlserverRestoreMode,
)
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.validate import (
    ValidateHandler,
    validate_get_dbmeta_func,
    validate_get_payload_func,
    validate_hosts,
)

"""
定义sqlserver每个活动节点的私用变量kwargs的dataclass类型
"""


@dataclass()
class ExecActuatorKwargs(ValidateHandler):
    """
    定义执行sqlserver_db_actuator_execute活动节点的私用变量通用结构体
    @attributes get_payload_func SqlserverActPayload类的获取参数方法名称
    @attributes exec_ips 执行的ip列表信息
    @attributes job_timeout # 隐性参数，调用job平台任务的操作时间，不传默认3600s
    @attributes custom_params # 隐性参数，传入参数时作为额外参数传入，自定义拼接
    """

    get_payload_func: str = field(metadata={"validate": validate_get_payload_func})
    exec_ips: List[Host] = field(metadata={"validate": validate_hosts})
    job_timeout: int = DEFAULT_JOB_TIMEOUT
    custom_params: dict = field(default_factory=dict)


@dataclass()
class P2PFileForWindowKwargs(ValidateHandler):
    """
    定义执行trans_file_in_window活动节点的私用变量通用结构体
    制品库下载场景
    @attributes file_list 需要传送的源文件列表
    @attributes file_target_path 表示下载到目标机器的路径，默认则传d:\\install
    @attributes source_hosts 源机器host列表
    @attributes target_hosts 目标机器host列表
    @attributes file_type 传输模式
    """

    file_list: list
    source_hosts: List[Host] = field(metadata={"validate": validate_hosts})
    target_hosts: List[Host] = field(metadata={"validate": validate_hosts})
    file_target_path: str = DEFAULT_SQLSERVER_PATH
    file_type: Optional[MediumFileTypeEnum] = MediumFileTypeEnum.Server.value


@dataclass()
class DownloadMediaKwargs(ValidateHandler):
    """
    定义执行trans_file_in_window活动节点的私用变量通用结构体
    制品库下载场景
    @attributes file_list 需要传送的源文件列表
    @attributes target_hosts 目标机器host列表
    @attributes file_target_path 表示下载到目标机器的路径，默认则传d:\\install
    @attributes file_type 传输模式
    """

    file_list: list  # 需要传送的源文件列表
    target_hosts: List[Host] = field(metadata={"validate": validate_hosts})
    file_target_path: str = DEFAULT_SQLSERVER_PATH
    file_type: Optional[MediumFileTypeEnum] = MediumFileTypeEnum.Repo.value


@dataclass()
class DBMetaOPKwargs:
    """
    定义执行sqlserver_db_meta活动节点的私有变量结构体
    @attributes db_meta_class_func SqlserverDBMeta类的获取参数方法名称
    """

    db_meta_class_func: str = field(metadata={"validate": validate_get_dbmeta_func})


@dataclass()
class ExecBackupJobsKwargs:
    """
    定义执行exec_sqlserver_backup_job活动节点的私有变量结构体
    @attributes cluster_id 集群id
    @attributes exec_mode 操作类型
    """

    cluster_id: int
    exec_mode: SqlserverBackupJobExecMode


@dataclass()
class RestoreForDoDrKwargs:
    """
    定义执行exec_sqlserver_backup_job活动节点的私有变量结构体
    @attributes cluster_id 集群id
    @attributes backup_id 备份id
    @attributes restore_dbs 恢复DB列表
    @attributes restore_mode 恢复模式，分全量备份文件恢复以及日志备份恢复
    @attributes exec_ips 操作机器
    @attributes port 实例端口
    @attributes job_timeout 操作超时时间
    """

    cluster_id: int
    backup_id: str
    restore_dbs: list
    restore_mode: SqlserverRestoreMode
    exec_ips: List[Host] = field(metadata={"validate": validate_hosts})
    port: int
    job_timeout: int = DEFAULT_JOB_TIMEOUT


@dataclass()
class ExecLoginKwargs:
    """
    定义执行exec_sqlserver_login活动节点的私有变量结构体
    @attributes cluster_id 集群id
    @attributes exec_mode 操作类型
    """

    cluster_id: int
    exec_mode: SqlserverLoginExecMode


@dataclass()
class RestoreForDtsKwargs:
    """
    定义执行sqlserver_restore_for_dts活动节点的私有变量结构体
    @attributes cluster_id 集群id
    @attributes port 实例端口
    @attributes backup_id 备份id
    @attributes restore_infos 恢复列表。元素结构{"db_name": xx, "target_db_name": xx}
    @attributes restore_mode 恢复模式，分全量备份文件恢复以及日志备份恢复
    @attributes restore_db_status 恢复后的DB模式
    @attributes exec_ips 操作机器
    @attributes job_timeout 操作超时时间
    """

    cluster_id: int
    port: int
    backup_id: str
    restore_infos: list
    restore_mode: SqlserverRestoreMode
    restore_db_status: SqlserverRestoreDBStatus
    exec_ips: List[Host] = field(metadata={"validate": validate_hosts})
    job_timeout: int = DEFAULT_JOB_TIMEOUT
