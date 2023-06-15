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

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.db_meta.enums import ClusterType
from backend.flow.consts import DBA_ROOT_USER, DnsOpType, MediumFileTypeEnum
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

"""
定义每个活动节点的私用变量kwargs的dataclass类型
建议每个活动节点都需要定义，这样可以知道每个活动节点需要的私有变量的结构体都可以知道
todo 后续慢慢定义好目前存量的活动节点的私有变量kwargs，调整所有单据入参方式
todo 结合validator来对dataclass对数据校验
"""


@dataclass()
class ExecActuatorBaseKwargs:
    """
    定义执行mysql_db_actuator_executor活动节点的私用变量通用结构体
    """

    bk_cloud_id: int  # 对应的云区域ID
    run_as_system_user: str = None  # 表示执行job的api的操作用户, None 默认是用root用户
    get_mysql_payload_func: str = None  # 上下文中MysqlActPayload类的获取参数方法名称。空则传入None
    cluster_type: str = None  # 表示操作的集群类型,如果过程中不需要这个变量，则可以传None
    cluster: dict = field(default_factory=dict)  # 表示单据执行的集群信息，比如集群名称，集群域名等


@dataclass()
class ExecActuatorKwargs(ExecActuatorBaseKwargs):
    """
    针对手输IP的场景
    """

    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型，空则传入None，针对手输ip场景


@dataclass()
class ExecActuatorKwargsForPool(ExecActuatorBaseKwargs):
    """
    针对资源池获取IP的场景
    """

    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None, 针对资源池获取ip场景


@dataclass()
class P2PFileBaseKwargs:
    """
    定义服务器之间点对点传输的私用变量结构体
    """

    bk_cloud_id: int  # 对应的云区域ID
    file_list: list  # 需要传送的源文件列表
    source_ip_list: list  # 源文件的机器IP列表
    file_type: Optional[MediumFileTypeEnum] = MediumFileTypeEnum.Server.value
    file_target_path: str = None  # 表示下载到目标机器的路径，如果传None,默认则传/data/install


@dataclass()
class P2PFileKwargs(P2PFileBaseKwargs):
    """
    针对手输IP的场景
    """

    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型，空则传入None，针对手输ip场景


@dataclass()
class P2PFileKwargsForPool(P2PFileBaseKwargs):
    """
    针对资源池获取IP的场景
    """

    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None, 针对资源池获取ip场景


@dataclass()
class SlaveTransFileKwargs(P2PFileKwargs):
    """
    针对SlaveTransFileComponent活动节点定义结构体
    """

    file_list = None
    source_ip_list = None


@dataclass()
class DownloadMediaBaseKwargs:
    """
    定义在介质中心下发介质的私用变量结构体
    """

    bk_cloud_id: int  # 对应的云区域ID
    file_list: list  # 需要传送的源文件列表
    file_type: Optional[MediumFileTypeEnum] = MediumFileTypeEnum.Repo.value
    file_target_path: str = None  # 表示下载到目标机器的路径，如果传None,默认则传/data/install


@dataclass()
class DownloadMediaKwargs(DownloadMediaBaseKwargs):
    """
    针对手输IP的场景
    """

    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型，空则传入None，针对手输ip场景


@dataclass()
class DownloadMediaKwargsForPool(DownloadMediaBaseKwargs):
    """
    针对资源池获取IP的场景
    """

    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None, 针对资源池获取ip场景


@dataclass()
class CreateDnsBaseKwargs:
    """
    定义dns活动节点执行添加dns信息的专属参数
    """

    bk_cloud_id: int  # 操作的云区域id
    add_domain_name: str  # 如果添加域名时,添加域名名称
    dns_op_exec_port: int  # 如果做添加或者更新域名管理，执行实例的port
    dns_op_type: Optional[DnsOpType] = DnsOpType.CREATE.value


@dataclass()
class CreateDnsKwargs(CreateDnsBaseKwargs):
    """
    针对手输IP的场景
    """

    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型，空则传入None，针对手输ip场景


@dataclass()
class CreateDnsKwargsForPool(CreateDnsBaseKwargs):
    """
    针对资源池获取IP的场景
    """

    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None, 针对资源池获取ip场景


@dataclass()
class RecycleDnsRecordKwargs:
    """
    定义dns活动节点 根据实例，执行删除dns对应记录的专属参数
    """

    bk_cloud_id: int  # 操作的云区域id
    dns_op_exec_port: int  # mysql 端口
    exec_ip: Optional[Any]  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型
    dns_op_type: Optional[DnsOpType] = DnsOpType.RECYCLE_RECORD.value


@dataclass()
class DeleteClusterDnsKwargs:
    """
    定义dns管理的活动节点专属参数
    """

    bk_cloud_id: int  # 操作的云区域id
    delete_cluster_id: int  # 操作的集群，回收集群时需要
    dns_op_type: Optional[DnsOpType] = DnsOpType.CLUSTER_DELETE.value  # 操作的域名方式
    # 是否仅删除从域名
    is_only_delete_slave_domain: bool = False


@dataclass()
class PtTableSyncKwargs:
    """
    定义数据修复的活动节点专属参数
    """

    bk_cloud_id: int  # 操作的云区域id
    sync_user: str  # 数据修复时临时账号的名称
    sync_pass: str  # 数据修复时临时账号的密码
    check_sum_table: str  # 校验结果的表名称
    is_routine_checksum: bool = False  # 是否是例行校验而触发的数据修复单据，默认不是，不是代表通过单据校验而触发修复


@dataclass()
class DBMetaOPKwargs:
    """
    定义db-meta元数据信息更新的活动节点的专属参数
    """

    # 表示活动节点变更db-meta元数据的方法名称，对应着MySQLDBMeta类，

    db_meta_class_func: str
    cluster: dict = field(default_factory=dict)  # 表示单据执行的集群信息，比如集群名称，集群域名等
    is_update_trans_data: bool = False  # 表示是否把流程中上下文trans_data合并到cluster信息，默认不合并


@dataclass()
class InstanceUserCloneKwargs:
    """
    定义实例之间用户权限克隆的活动节点的专属参数
    """

    # 表示克隆的信息，格式样例：[{"source": "1.1.1.1", "target": "2.2.2.2"}..]
    clone_data: list = field(default_factory=list)


@dataclass()
class AddSwitchUserKwargs:
    """
    定义添加mysql的主从切换流程中添加临时账号的专属参数
    """

    bk_cloud_id: int  # 操作的云区域id
    user: str = None  # 添加的临时账号的名称
    psw: str = None  # 添加的临时账号的加密后的密码
    hosts: list = field(default_factory=list)  # 账号授权的host列表
    address: str = None  # 授权的实例，格式是ip:port


@dataclass()
class IfTimingAfterNowKwargs:
    """
    检查定时时间是否晚于当前时间
    """

    force_check_timing: bool = False


@dataclass()
class UploadFile:
    """
    定义上传文件的参数
    """

    path: str = None  # 文件路径
    content: str = None  # 文件内容


@dataclass()
class AddTempUserKwargs:
    """
    定义添加用户的参数
    """

    bk_cloud_id: int  # 操作的云区域
    hosts: list = field(default_factory=list)
    user: str = None
    psw: str = None
    address: str = None  # 授权的实例
    dbname: str = None  # 授权db，示例:db1，db%
    dml_ddl_priv: str = None
    global_priv: str = None  # global权限授权：grant xxx on *.* to user@host identified by 'xxx';


@dataclass()
class DropUserKwargs:
    """
    定义删除用户的参数
    """

    bk_cloud_id: int  # 操作的云区域
    host: str = None
    user: str = None
    address: str = None  # 授权的实例


@dataclass()
class ClearMachineKwargs:
    """
    MySQLClearMachineComponent 专属活动节点的私用变量
    """

    bk_cloud_id: int  # 对应的云区域ID
    exec_ip: Optional[Any]  # 执行ip信息，单个传字符串；多个传列表
    run_as_system_user: str = DBA_ROOT_USER
    get_mysql_payload_func: str = MysqlActPayload.get_clear_machine_crontab.__name__


@dataclass()
class RollBackTransFileKwargs(P2PFileKwargs):
    """
    RollBackTransFileComponent 专属活动节点的私用变量
    """

    cluster: dict = field(default_factory=dict)


@dataclass()
class BKCloudIdKwargs:
    """
    制定bk_cloud_id 专属变量的dataclass
    """

    bk_cloud_id: int  # 对应的云区域ID


@dataclass()
class AddSpiderSystemUserKwargs:
    """
    针对部署spider(tenDB cluster)集群场景，添加内置账号的专属私有变量
    """

    ctl_master_ip: str  # 中控集群的master ip
    user: str  # 内置账号名称
    passwd: str  # 内置账号密码


@dataclass()
class DelServiceInstKwargs:
    """
    删除集群内服务实例的专属私有变量
    """

    cluster_id: int  # 对应的cluster_id
    del_instance_list: list  # 删除对应的实例信息


@dataclass
class DownloadBackupFileKwargs:
    """
    定义下载mysql备份文件的变量结构体
    """

    bk_cloud_id: int
    task_ids: list
    dest_ip: str
    login_user: str
    desc_dir: str
    reason: str
