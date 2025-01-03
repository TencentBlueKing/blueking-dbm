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
    @attributes cluster_id 传输模式
    @attributes is_trans_log_backup 是否自动查询日志备份
    @attributes is_trans_full_backup 是否自动查询全量备份
    """

    source_hosts: List[Host] = field(metadata={"validate": validate_hosts})
    target_hosts: List[Host] = field(metadata={"validate": validate_hosts})
    file_list: list = field(default_factory=list)
    file_target_path: str = DEFAULT_SQLSERVER_PATH
    file_type: Optional[MediumFileTypeEnum] = MediumFileTypeEnum.Server.value
    cluster_id: int = 0
    is_trans_log_backup: bool = True
    is_trans_full_backup: bool = True


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
    @attributes job_id 备份的job_id
    @attributes restore_dbs 恢复DB列表
    @attributes restore_mode 恢复模式，分全量备份文件恢复以及日志备份恢复
    @attributes exec_ips 操作机器
    @attributes port 实例端口
    @attributes job_timeout 操作超时时间
    """

    cluster_id: int
    job_id: str
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
    exec_ip: str


@dataclass()
class RestoreForDtsKwargs:
    """
    定义执行sqlserver_restore_for_dts活动节点的私有变量结构体
    @attributes cluster_id 集群id
    @attributes port 实例端口
    @attributes job_id 备份id
    @attributes restore_infos 恢复列表。元素结构{"db_name": xx, "target_db_name": xx}
    @attributes restore_mode 恢复模式，分全量备份文件恢复以及日志备份恢复
    @attributes restore_db_status 恢复后的DB模式
    @attributes restore_path 备份文件所在的目录位置
    @attributes exec_ips 操作机器
    @attributes job_timeout 操作超时时间
    """

    cluster_id: int
    port: int
    job_id: str
    restore_infos: list
    restore_mode: SqlserverRestoreMode
    restore_db_status: SqlserverRestoreDBStatus
    restore_path: str
    exec_ips: List[Host] = field(metadata={"validate": validate_hosts})
    job_timeout: int = DEFAULT_JOB_TIMEOUT


@dataclass()
class DownloadBackupFileKwargs:
    """
    定义执行sqlserver_Download_backup_file活动节点的私有变量结构体
    @attributes bk_cloud_id 云区域id
    @attributes dest_ip 目标ip
    @attributes dest_dir 目标目录
    @attributes get_backup_file_info_var 获取备份文件列表信息的上下文
    """

    bk_cloud_id: int
    dest_ip: str
    dest_dir: str
    get_backup_file_info_var: str


@dataclass()
class CreateRandomJobUserKwargs:
    """
    定义执行sqlserver_add_job_user活动节点的私有变量结构体
    @attributes cluster_ids 集群id列表
    @attributes user 随机账号名称
    @attributes sid 随机账号sid
    """

    cluster_ids: list
    sid: str
    other_instances: list = field(default_factory=list)


@dataclass()
class DropRandomJobUserKwargs:
    """
    定义执行sqlserver_add_job_user活动节点的私有变量结构体
    @attributes cluster_ids 集群id列表
    @attributes user 随机账号名称
    """

    cluster_ids: list
    other_instances: list = field(default_factory=list)


@dataclass()
class InsertAppSettingKwargs:
    """
    定义执行sqlserver_insert_app_setting活动节点的私有变量结构体
    @attributes cluster_domain 集群主域名
    @attributes ips 待处理的ip列表
    @attributes is_get_old_backup_config 是否要获取旧的备份配置信息，内部导入标准化使用
    """

    cluster_domain: str
    ips: list = field(default_factory=list)
    is_get_old_backup_config: bool = False


@dataclass()
class SqlserverDBConstructContext:
    """
    定义数据构造的可交互上下文dataclass类
    """

    full_backup_infos: list = field(default_factory=list)
    log_backup_infos: list = field(default_factory=list)

    @staticmethod
    def full_backup_infos_var_name() -> str:
        return "full_backup_infos"

    @staticmethod
    def log_backup_infos_var_name() -> str:
        return "log_backup_infos"


@dataclass()
class SqlserverBackupIDContext:
    """
    定义数据备份的可交互上下文dataclass类
    """

    full_backup_id: dict = field(default_factory=dict)
    log_backup_id: dict = field(default_factory=dict)

    @staticmethod
    def full_backup_id_var_name() -> str:
        return "full_backup_id"

    @staticmethod
    def log_backup_id_var_name() -> str:
        return "log_backup_id"


@dataclass()
class SqlserverRebuildSlaveContext:
    """
    定义重建slave的可交互上下文dataclass类
    """

    sync_dbs: list = field(default_factory=list)
    clean_dbs: list = field(default_factory=list)
    full_backup_id: dict = field(default_factory=dict)
    log_backup_id: dict = field(default_factory=dict)

    @staticmethod
    def sync_dbs_var_name() -> str:
        return "sync_dbs"

    @staticmethod
    def clean_dbs_var_name() -> str:
        return "clean_dbs"

    @staticmethod
    def full_backup_id_var_name() -> str:
        return "full_backup_id"

    @staticmethod
    def log_backup_id_var_name() -> str:
        return "log_backup_id"

    @staticmethod
    def conditions_var_name() -> str:
        return "fix_number"


@dataclass()
class CheckDBExistKwargs:
    """
    定义执行sqlserver_check_db_exist活动节点的私有变量结构体
    @attributes cluster_domain 集群主域名
    @attributes ips 待处理的ip列表
    @attributes is_get_old_backup_config 是否要获取旧的备份配置信息，内部导入标准化使用
    """

    cluster_id: str
    check_dbs: list = field(default_factory=list)


@dataclass
class UpdateWindowGseConfigKwargs:
    """
    定义变更gse参数的配置私有变量结构体
    """

    bk_cloud_id: int
    ips: list


@dataclass
class CheckSlaveSyncStatusKwargs:
    """
    定义sqlserver_check_rebuild_slave私有变量结构体
    """

    cluster_id: int
    fix_slave_host: list
