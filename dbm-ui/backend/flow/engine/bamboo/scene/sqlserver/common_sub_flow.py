"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy
from dataclasses import asdict
from pathlib import PureWindowsPath
from typing import Dict, List, Optional

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import (
    DBM_SQLSERVER_JOB_LONG_TIMEOUT,
    WINDOW_ADMIN_USER_FOR_CHECK,
    SqlserverBackupFileTagEnum,
    SqlserverBackupJobExecMode,
    SqlserverBackupMode,
    SqlserverCleanMode,
    SqlserverRestoreMode,
    SqlserverSyncMode,
    SqlserverSyncModeMaps,
    SqlserverVersion,
)
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.common.install_plugins import install_nodeman_plugins
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.common.sa_udns_add import UdnsAddInMachineComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.sqlserver.backup_path_file_trans import (
    SqlserverTransBackupFileFor2P2Component,
)
from backend.flow.plugins.components.collections.sqlserver.check_no_sync_db import CheckNoSyncDBComponent
from backend.flow.plugins.components.collections.sqlserver.clone_linkserver import CloneLinkServerComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.exec_sqlserver_backup_job import (
    ExecSqlserverBackupJobComponent,
)
from backend.flow.plugins.components.collections.sqlserver.init_dbm_nginx_proxy import (
    InitDBMNginxForSQLServerComponent,
)
from backend.flow.plugins.components.collections.sqlserver.insert_app_setting import InsertAppSettingComponent
from backend.flow.plugins.components.collections.sqlserver.restore_for_do_dr import RestoreForDoDrComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_download_backup_file import (
    SqlserverDownloadBackupFileComponent,
)
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.plugins.components.collections.sqlserver.update_window_gse_config import (
    UpdateWindowGseConfigComponent,
)
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs, InitCheckKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import UpdateDnsRecordKwargs
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    DownloadBackupFileKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    ExecBackupJobsKwargs,
    InsertAppSettingKwargs,
    P2PFileForWindowKwargs,
    RestoreForDoDrKwargs,
    SqlserverBackupIDContext,
    UpdateWindowGseConfigKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_bk_config import get_sqlserver_backup_config
from backend.flow.utils.sqlserver.sqlserver_db_function import get_backup_path
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.validate import SqlserverCluster, SqlserverInstance


def init_machine_sub_flow(
    uid: str,
    bk_biz_id: int,
    bk_cloud_id: int,
    root_id: str,
    target_hosts: List[Host],
) -> SubProcess:
    """机器初始化的通用子流程（Windows 机器纳管前置动作）。

    设计要点 / 怎么做：
      - 数据源：target_hosts（Host 对象列表，包含 ip / bk_cloud_id / bk_host_id）。
      - 编排顺序：空闲检查 -> udns 解析下发 -> gse 配置更新 -> nodeman 蓝鲸插件安装。
      - 每一步都通过环境开关（env.SA_CHECK_TEMPLATE_ID / env.UPDATE_WINDOW_UDNS_CONFIG /
        env.UPDATE_WINDOW_GSE_CONFIG）控制是否启用，未配置的开关会跳过对应节点，
        保证在不同私有化部署环境（未提供作业平台模板）下仍可运行。
      - 通道：作业平台（SA 模板）+ nodeman 插件安装子流程。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param bk_biz_id: 目标机器所属业务 id，必填
    :param bk_cloud_id: 目标机器所在云区域 id，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param target_hosts: 待初始化的机器列表；每个元素必须携带有效 bk_host_id，否则插件安装会失败
    :return: SubProcess，子流程节点名为 "初始化机器"

    边界 / 异常：
      - target_hosts 为空 -> 允许，仅生成一个空的插件安装子流程（无副作用）。
      - env 全部开关关闭 -> 仅保留插件安装节点；若 target_hosts 也为空，则子流程为空 pipeline。
      - target_hosts 中存在 bk_host_id=None -> 插件安装阶段会失败，本函数不做二次校验。
    """
    # 构造只读上下文
    global_data = {
        "uid": uid,
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": bk_cloud_id,
    }
    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 空闲检查
    if env.SA_CHECK_TEMPLATE_ID:
        sub_pipeline.add_act(
            act_name=_("空闲检查"),
            act_component_code=CheckMachineIdleComponent.code,
            kwargs=asdict(
                InitCheckKwargs(
                    ips=[host.ip for host in target_hosts],
                    bk_cloud_id=bk_cloud_id,
                    account_name=WINDOW_ADMIN_USER_FOR_CHECK,
                )
            ),
        )

    # 强制添加udns解析
    if env.UPDATE_WINDOW_UDNS_CONFIG:
        sub_pipeline.add_act(
            act_name=_("更新机器的udns配置"),
            act_component_code=UdnsAddInMachineComponent.code,
            kwargs=asdict(
                UdnsAddInMachineComponent.kwargs(
                    ips=[host.ip for host in target_hosts],
                    bk_cloud_id=bk_cloud_id,
                    account_name=WINDOW_ADMIN_USER_FOR_CHECK,
                    template_id=env.UPDATE_WINDOW_UDNS_CONFIG,
                )
            ),
        )

    # 更新window机器的gse配置信息
    if env.UPDATE_WINDOW_GSE_CONFIG:
        sub_pipeline.add_act(
            act_name=_("更新gse配置信息"),
            act_component_code=UpdateWindowGseConfigComponent.code,
            kwargs=asdict(
                UpdateWindowGseConfigKwargs(
                    ips=[host.ip for host in target_hosts],
                    bk_cloud_id=bk_cloud_id,
                )
            ),
        )

    # 安装蓝鲸插件
    bk_host_ids = [t.bk_host_id for t in target_hosts]
    sub_pipeline.add_sub_pipeline(install_nodeman_plugins(root_id, uid, bk_host_ids))

    return sub_pipeline.build_sub_process(sub_name=_("初始化机器"))


def install_sqlserver_sub_flow(
    uid: str,
    root_id: str,
    bk_biz_id: int,
    bk_cloud_id: int,
    db_module_id: int,
    install_ports: List[int],
    clusters: List[SqlserverCluster],
    cluster_type: ClusterType,
    target_hosts: List[Host],
    db_version: SqlserverVersion,
) -> SubProcess:
    """按机器维度安装 SQLServer 实例的通用子流程。

    设计要点 / 怎么做：
      - 数据源：target_hosts（Host 列表） + install_ports（端口列表，多实例时并存）。
      - 编排顺序：下发安装包介质 -> 机器初始化（system_init）-> 并发按机器安装实例
        -> 并发按机器初始化实例。
      - 前两步串行确保介质与 OS 前置就绪；后两步以机器粒度并发以缩短总耗时。
      - 通道：TransFileInWindowsComponent（介质下发）+ SqlserverActuatorScriptComponent
        （通过 db-actuator 执行安装/初始化）。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param bk_biz_id: 目标业务 id，必填
    :param bk_cloud_id: 目标云区域 id，必填
    :param db_module_id: 对应的 DB 模块 id（决定安装配置模板），必填
    :param install_ports: 机器需安装的实例端口列表，支持多实例场景
    :param clusters: 本次机器部署所关联的集群列表（用于全局上下文透传给 payload）
    :param cluster_type: 集群类型（单节点 / HA / 只读组等），影响下游 actuator 分支
    :param target_hosts: 本次待部署的机器列表；每个元素必须携带 bk_host_id
    :param db_version: SQLServer 版本枚举，用于选取安装介质
    :return: SubProcess，子流程节点名为 "安装sqlserver实例"

    边界 / 异常：
      - target_hosts 中任一元素缺失 bk_host_id -> 直接抛 Exception，附带缺失 IP 信息，
        避免安装到一半才发现 CMDB 未纳管。
      - install_ports 为空 -> 允许（只做机器初始化，不装实例）；实际生产不建议。
      - target_hosts 为空 -> 下发/初始化节点会空转，通常调用方需保证非空。
    """
    # 预防性检测
    is_err = False
    err_messages = ""
    for host in target_hosts:
        if not host.bk_host_id:
            is_err = True
            err_messages += _("流程中安装机器【{}】没有存入bk_host_id,请联系系统管理员\n".format(host.ip))
    if is_err:
        raise Exception(err_messages)

    # 构造只读上下文
    global_data = {
        "uid": uid,
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": bk_cloud_id,
        "db_module_id": db_module_id,
        "install_ports": install_ports,
        "clusters": [asdict(i) for i in clusters],
        "cluster_type": cluster_type,
    }
    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 下发安装包
    sub_pipeline.add_act(
        act_name=_("下发安装包介质"),
        act_component_code=TransFileInWindowsComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                target_hosts=target_hosts,
                file_list=GetFileList(db_type=DBType.Sqlserver).get_sqlserver_package(db_version=db_version),
            ),
        ),
    )
    # 机器初始化
    sub_pipeline.add_act(
        act_name=_("机器初始化"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=target_hosts, get_payload_func=SqlserverActPayload.system_init_payload.__name__
            ),
        ),
    )
    # 安装机器维度安装实例
    acts_list = []
    for hosts in target_hosts:
        acts_list.append(
            {
                "act_name": _("安装Sqlserver实例:{}".format(hosts.ip)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[hosts], get_payload_func=SqlserverActPayload.get_install_sqlserver_payload.__name__
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 安装机器维度初始化实例
    acts_list = []
    for hosts in target_hosts:
        acts_list.append(
            {
                "act_name": _("初始化Sqlserver实例:{}".format(hosts.ip)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[hosts], get_payload_func=SqlserverActPayload.get_init_sqlserver_payload.__name__
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("安装sqlserver实例"))


def switch_domain_sub_flow_for_cluster(
    uid: str,
    root_id: str,
    cluster: Cluster,
    old_master_host: Host,
    old_master_port: int,
    old_master_dns_list: List[ClusterEntry],
    new_master_host: Host,
    new_master_port: int,
    new_master_dns_list: List[ClusterEntry],
    is_force: bool = False,
) -> SubProcess:
    """主从切换（HA / 单节点迁移）后的域名切换子流程。

    设计要点 / 怎么做：
      - 数据源：old / new master 的 Host + port + 当前挂载的 ClusterEntry 域名列表。
      - 编排顺序：并发替换主域名映射（旧 master -> 新 master）；
        非强切场景下再并发替换从域名映射（新 master -> 旧 master，做角色对调）。
      - is_force=True 时视为"主故障强切"，认为旧主已不可用，不再把从域名指向旧主。
      - 通道：MySQLDnsManageComponent（DBM 内的 DNS 管理组件，MySQL/SQLServer 共用）。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param cluster: 集群元数据，用于取 bk_biz_id / bk_cloud_id / name
    :param old_master_host: 集群原主机器
    :param old_master_port: 集群原主端口
    :param old_master_dns_list: 原主实例当前挂载的域名列表（只处理 DNS 类型条目）
    :param new_master_host: 集群新主机器
    :param new_master_port: 集群新主端口
    :param new_master_dns_list: 新主实例当前挂载的域名列表（用于反向切换成从域名）
    :param is_force: 是否强制切换；True=主故障强切，从域名不回切旧主；默认 False
    :return: SubProcess，子流程节点名为 "变更集群[{cluster.name}]域名映射"

    边界 / 异常：
      - old_master_dns_list 与 new_master_dns_list 均为空 -> 生成空并发节点，
        pipeline 会直接完成（无副作用）。
      - is_force=True -> 仅执行主域名替换，不做从域名反向替换。
      - 域名不存在于 DNS 服务 -> 由 MySQLDnsManageComponent 内部处理，本函数不感知。
    """
    # 构造只读上下文
    global_data = {"uid": uid, "bk_biz_id": cluster.bk_biz_id}

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 替换主域名映射
    acts_list = []
    for old_master_dns in old_master_dns_list:
        acts_list.append(
            {
                "act_name": _("[{}]替换主域名映射".format(old_master_dns.entry)),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=f"{old_master_host.ip}#{old_master_port}",
                        new_instance=f"{new_master_host.ip}#{new_master_port}",
                        update_domain_name=old_master_dns.entry,
                    ),
                ),
            }
        )
    # 并发替换从域名映射
    if not is_force:
        for slave_dns in new_master_dns_list:
            acts_list.append(
                {
                    "act_name": _("[{}]替换从域名映射".format(slave_dns.entry)),
                    "act_component_code": MySQLDnsManageComponent.code,
                    "kwargs": asdict(
                        UpdateDnsRecordKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            old_instance=f"{new_master_host.ip}#{new_master_port}",
                            new_instance=f"{old_master_host.ip}#{old_master_port}",
                            update_domain_name=slave_dns.entry,
                        ),
                    ),
                }
            )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("变更集群[{}]域名映射".format(cluster.name)))


def migrate_domain_for_cluster_ha(
    uid: str,
    root_id: str,
    cluster: Cluster,
    old_master: StorageInstance,
    old_stand_by: StorageInstance,
    new_master_host: Host,
    new_stand_by_host: Host,
) -> SubProcess:
    """HA 集群整体迁移后的域名切换子流程（主+备一并搬迁）。

    设计要点 / 怎么做：
      - 数据源：从 StorageInstance.bind_entry 查询当前挂载的 DNS 域名列表，
        避免调用方额外传参、也保证域名的实时一致性。
      - 编排顺序：并发替换主/备域名映射；同一 pipeline 内一次性完成主备切换。
      - 端口沿用旧实例端口（迁移前后端口不变假设）。
      - 通道：MySQLDnsManageComponent。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param cluster: 集群元数据，用于取 bk_biz_id / bk_cloud_id / immute_domain
    :param old_master: 集群原主实例（StorageInstance，含机器 IP、端口、绑定域名）
    :param old_stand_by: 集群原备实例
    :param new_master_host: 集群新主机器（端口沿用 old_master.port）
    :param new_stand_by_host: 集群新备机器（端口沿用 old_stand_by.port）
    :return: SubProcess，子流程节点名为 "变更集群[{cluster.immute_domain}]域名映射"

    边界 / 异常：
      - old_master / old_stand_by 未绑定任何 DNS 域名 -> 生成空并发节点，无副作用。
      - 新主/新备端口与旧端口不一致的迁移场景 -> 本函数假设端口不变，若不满足需使用
        switch_domain_sub_flow_for_cluster 或扩展参数。
    """
    # 构造只读上下文
    global_data = {"uid": uid, "bk_biz_id": cluster.bk_biz_id}

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 替换主域名映射
    acts_list = []
    old_master_dns_list = old_master.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
    for old_master_dns in old_master_dns_list:
        acts_list.append(
            {
                "act_name": _("[{}]替换主域名映射".format(old_master_dns.entry)),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=f"{old_master.machine.ip}#{old_master.port}",
                        new_instance=f"{new_master_host.ip}#{old_master.port}",
                        update_domain_name=old_master_dns.entry,
                    ),
                ),
            }
        )
    # 并发替换从域名映射
    slave_dns_list = old_stand_by.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
    for slave_dns in slave_dns_list:
        acts_list.append(
            {
                "act_name": _("[{}]替换从域名映射".format(slave_dns.entry)),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=f"{old_stand_by.machine.ip}#{old_stand_by.port}",
                        new_instance=f"{new_stand_by_host.ip}#{old_stand_by.port}",
                        update_domain_name=slave_dns.entry,
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("变更集群[{}]域名映射".format(cluster.immute_domain)))


def migrate_domain_for_cluster_single(
    uid: str,
    root_id: str,
    cluster: Cluster,
    old_instance: StorageInstance,
    new_host: Host,
) -> SubProcess:
    """单节点集群迁移后的域名切换子流程。

    设计要点 / 怎么做：
      - 数据源：从 old_instance.bind_entry 查询当前挂载的 DNS 域名列表。
      - 编排顺序：并发替换所有绑定域名，从旧机器指向新机器；端口沿用 old_instance.port。
      - 与 HA 差异：无从域名概念，只处理"主"域名列表。
      - 通道：MySQLDnsManageComponent。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param cluster: 集群元数据，用于取 bk_biz_id / bk_cloud_id / name
    :param old_instance: 原实例（含机器 IP、端口、绑定域名）
    :param new_host: 待替换的新机器；端口沿用 old_instance.port
    :return: SubProcess，子流程节点名为 "变更集群[{cluster.name}]域名映射"

    边界 / 异常：
      - old_instance 未绑定任何 DNS 域名 -> 生成空并发节点，无副作用。
      - 端口变更场景 -> 本函数假设端口不变，需扩展调用方参数。
    """
    # 构造只读上下文
    global_data = {"uid": uid, "bk_biz_id": cluster.bk_biz_id}

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 替换主域名映射
    acts_list = []
    dns_list = old_instance.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
    for dns_info in dns_list:
        acts_list.append(
            {
                "act_name": _("[{}]替换主域名映射".format(dns_info.entry)),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=f"{old_instance.machine.ip}#{old_instance.port}",
                        new_instance=f"{new_host.ip}#{old_instance.port}",
                        update_domain_name=dns_info.entry,
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("变更集群[{}]域名映射".format(cluster.name)))


def pre_check_sub_flow(
    uid: str,
    root_id: str,
    cluster_id: int,
    check_host: Host,
    check_port: int,
    is_check_abnormal_db: bool = True,
    is_check_inst_process: bool = True,
    is_check_sync_db: bool = True,
) -> SubProcess:
    """主从切换/迁移前的实例预检查子流程。

    设计要点 / 怎么做：
      - 编排顺序：三类检查按开关拼装到并发列表，一次并发执行。
      - 检查项：
          1) 未同步的数据库（CheckNoSyncDBComponent，读元数据比对）
          2) 异常状态 DB（SqlserverActuatorScriptComponent，实例侧扫描 sys.databases）
          3) 业务连接（SqlserverActuatorScriptComponent，检查是否有活动 spid）
      - 通道：CheckNoSyncDBComponent + SqlserverActuatorScriptComponent。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param cluster_id: 集群 id，用于同步 DB 检查从元数据取归属
    :param check_host: 待检查的实例所在机器
    :param check_port: 待检查的实例端口
    :param is_check_abnormal_db: 是否检查异常状态 DB（Suspect / Recovery_Pending 等），默认 True
    :param is_check_inst_process: 是否检查存在业务连接（避免误切），默认 True
    :param is_check_sync_db: 是否检查未同步 DB（避免主从不一致），默认 True
    :return: SubProcess，子流程节点名为 "预检测"

    边界 / 异常：
      - 三个开关全部为 False -> 生成空并发节点，pipeline 直接完成；调用方需自行判断。
      - 检查项失败 -> 由各 Component 内部抛业务异常中止流程，本函数不做二次拦截。
    """
    # 构造只读上下文
    global_data = {"uid": uid, "port": check_port}

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 并发检测异常状态DB
    acts_list = []
    if is_check_sync_db:
        acts_list.append(
            {
                "act_name": _("检查实例{}:{}是否存在没有同步的数据库".format(check_host.ip, check_port)),
                "act_component_code": CheckNoSyncDBComponent.code,
                "kwargs": {"cluster_id": cluster_id},
            }
        )

    if is_check_abnormal_db:
        acts_list.append(
            {
                "act_name": _("检查实例{}:{}是否有异常状态DB".format(check_host.ip, check_port)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[check_host],
                        get_payload_func=SqlserverActPayload.get_check_abnormal_db_payload.__name__,
                    )
                ),
            }
        )
    # 并发检测是否有业务链接
    if is_check_inst_process:
        acts_list.append(
            {
                "act_name": _("检查实例{}:{}是否有业务链接".format(check_host.ip, check_port)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[check_host],
                        get_payload_func=SqlserverActPayload.get_check_inst_process_payload.__name__,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("预检测"))


def clone_configs_sub_flow(
    uid: str,
    root_id: str,
    bk_biz_id: int,
    source_host: Host,
    source_port: int,
    target_host: Host,
    target_port: int,
    is_clone_user: bool = True,
    is_clone_jobs: bool = True,
    is_clone_linkserver: bool = True,
    is_clone_backup_filter: bool = True,
    is_clone_mirroring_filter: bool = True,
    sub_flow_name: str = _("克隆实例周边配置"),
) -> SubProcess:
    """实例间"周边配置克隆"子流程（用户/作业/LinkServer/过滤规则）。

    设计要点 / 怎么做：
      - 编排顺序：五类克隆动作按开关拼装到并发列表，一次并发下发。
      - 克隆项：
          * Users（登录名 + 库级用户 + 权限）
          * Jobs（SQL Agent 作业）
          * LinkServer（跨实例链接服务器，需从 DBM 授权中心按 bk_biz_id 取密码）
          * backup_filter（备份忽略表）
          * mirroring_filter（同步忽略表）
      - 通道：SqlserverActuatorScriptComponent + CloneLinkServerComponent（LinkServer 需
        额外读授权中心）。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param bk_biz_id: 业务 id；CloneLinkServer 从 DBM 授权中心按业务隔离查询密码
    :param source_host: 源实例所在机器
    :param source_port: 源实例端口
    :param target_host: 目标实例所在机器
    :param target_port: 目标实例端口
    :param is_clone_user: 是否克隆用户权限，默认 True
    :param is_clone_jobs: 是否克隆 SQL Agent 作业，默认 True
    :param is_clone_linkserver: 是否克隆 LinkServer 配置，默认 True
    :param is_clone_backup_filter: 是否克隆备份忽略表，默认 True
    :param is_clone_mirroring_filter: 是否克隆同步忽略表，默认 True
    :param sub_flow_name: 子流程节点显示名，默认 "克隆实例周边配置"
    :return: SubProcess，子流程节点名由 sub_flow_name 指定

    边界 / 异常：
      - is_clone_user / is_clone_jobs / is_clone_linkserver 三者同时为 False
        -> 直接抛 Exception（保守拦截：认为调用方误用，且历史约束未纳入后两个 filter 开关）。
      - 目标实例不可连 / 权限不足 -> 由 actuator 内部抛异常中止流程。
    """
    if not is_clone_user and not is_clone_jobs and not is_clone_linkserver:
        raise Exception("is_clone_user, is_clone_jobs and is_clone_linkserver is False, check")

    # 构造只读上下文
    global_data = {
        "uid": uid,
        "port": target_port,
        "source_host": source_host.ip,
        "source_port": source_port,
    }
    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)
    acts_list = []
    # 并发克隆Users
    if is_clone_user:
        acts_list.append(
            {
                "act_name": _("克隆Users"),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_user_payload.__name__,
                    )
                ),
            }
        )
    # 并发克隆LinkServer
    if is_clone_linkserver:
        acts_list.append(
            {
                "act_name": _("克隆LinkServer"),
                "act_component_code": CloneLinkServerComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_linkserver_payload.__name__,
                        component_kwargs={
                            "bk_biz_id": bk_biz_id,
                            "target_port": target_port,
                            "source_host": source_host.ip,
                            "source_port": source_port,
                            "bk_cloud_id": target_host.bk_cloud_id,
                        },
                    )
                ),
            }
        )
    # 并发克隆Jobs
    if is_clone_jobs:
        acts_list.append(
            {
                "act_name": _("克隆Jobs"),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_jobs_payload.__name__,
                    )
                ),
            }
        )

    # 并发克隆backup_filter
    if is_clone_backup_filter:
        acts_list.append(
            {
                "act_name": _("克隆备份忽略表"),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_backup_filter_payload.__name__,
                    )
                ),
            }
        )

    # 并发克隆mirroring_filter
    if is_clone_mirroring_filter:
        acts_list.append(
            {
                "act_name": _("克隆同步忽略表"),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_mirroring_filter_payload.__name__,
                    )
                ),
            }
        )

    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=sub_flow_name)


def sync_dbs_for_cluster_sub_flow(
    uid: str,
    root_id: str,
    cluster: Cluster,
    master_host: Host,
    sync_slaves: List[Host],
    port: int,
    sync_dbs: List[str],
    clean_dbs: Optional[List[str]] = None,
    sub_flow_name: str = _("建立数据库同步子流程"),
    is_recalc_sync_dbs: bool = False,
    is_recalc_clean_dbs: bool = False,
    sync_mode: Optional[SqlserverSyncMode] = None,
) -> SubProcess:
    """在集群主/从间建立数据库级同步关系（Mirroring / AlwaysOn）的子流程。

    设计要点 / 怎么做：
      - 数据源：master_host + sync_slaves + sync_dbs（业务库列表）+ 集群备份路径配置。
      - 编排顺序：
          1) 禁用例行备份 jobs（避免与全量备份冲突）
          2) 下发 db-actuator 介质到所有 slave + master
          3) 并发在各 slave 清理旧库（DROP_DBS，force=True）
          4) 在 master 执行全量备份 -> 日志备份，backup_id 写入上下文
          5) 传送备份文件 master -> 各 slave（P2P，rolling）
          6) 并发在各 slave 恢复全量 -> 恢复日志
          7) 在 master 建立数据库级同步（按 sync_mode 分派 payload）
          8) 恢复例行备份 jobs
      - 同步模式：
          * MIRRORING -> get_build_database_mirroring，要求最多 1 个 slave
          * ALWAYS_ON -> get_build_add_dbs_in_always_on，支持多 slave
      - 通道：TransFileInWindowsComponent / SqlserverActuatorScriptComponent /
        SqlserverTransBackupFileFor2P2Component / RestoreForDoDrComponent /
        ExecSqlserverBackupJobComponent。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param cluster: 关联的集群对象；用于查备份路径、bk_cloud_id、cluster_id
    :param master_host: 当前集群主机器（承担备份产出）
    :param sync_slaves: 待同步的从机器列表；MIRRORING 模式下长度必须 ≤ 1
    :param port: 实例端口（主/从同端口）
    :param sync_dbs: 待建立同步的业务库列表；is_recalc_sync_dbs=True 时可为空占位
    :param clean_dbs: 从库清理时使用的库列表；None 时复用 sync_dbs
    :param sub_flow_name: 子流程节点显示名，默认 "建立数据库同步子流程"
    :param is_recalc_sync_dbs: 是否在运行时从上下文动态取 sync_dbs（原地重建 slave 场景）
    :param is_recalc_clean_dbs: 是否在运行时从上下文动态取 clean_dbs（原地重建 slave 场景）
    :param sync_mode: 显式指定同步模式；None 时从元数据 SqlserverClusterSyncMode 读取；
                     单节点集群迁移等特殊场景可显式传入
    :return: SubProcess，子流程节点名由 sub_flow_name 指定

    边界 / 异常：
      - sync_slaves 为空 -> 抛 Exception（无 slave 无法建立同步）。
      - sync_dbs 为空且 is_recalc_sync_dbs=False -> 抛 Exception。
      - MIRRORING 模式下 sync_slaves 数量 > 1 -> 抛 Exception（协议限制）。
      - 集群未配置备份路径 -> 使用 D:/dbbak/restore_dr_{root_id}_{port} 兜底。
      - 集群未在 SqlserverClusterSyncMode 中登记 -> 上游查询会抛 DoesNotExist，由调用方兜底。
    """

    # 获取集群的备份路径
    cluster_backup_path = get_backup_path(cluster.id)
    if cluster_backup_path == "":
        # 如果没有配置，则用默认路径
        backup_path = str(PureWindowsPath("d:/") / "dbbak" / f"restore_dr_{root_id}_{port}")
    else:
        backup_path = str(PureWindowsPath(cluster_backup_path) / f"restore_dr_{root_id}_{port}")
    # 获取集群的同步模式
    # 如果cluster_sync_mode 为空，则默认是mirror
    cluster_sync_mode = (
        sync_mode if sync_mode else SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
    )

    # 生成切换payload的字典
    sync_payload_func_map = {
        SqlserverSyncMode.MIRRORING: SqlserverActPayload.get_build_database_mirroring.__name__,
        SqlserverSyncMode.ALWAYS_ON: SqlserverActPayload.get_build_add_dbs_in_always_on.__name__,
    }
    #  判断必要参数
    if len(sync_slaves) == 0 or (len(sync_dbs) == 0 and is_recalc_sync_dbs is False):
        raise Exception("sync_slaves or sync_dbs is null, check")

    # 做判断, cluster_sync_mode 如果是mirror，原则上不允许一主多从的架构, 所以判断传入的slave是否有多个
    if cluster_sync_mode == SqlserverSyncMode.MIRRORING and len(sync_slaves) > 1:
        raise Exception(f"[{cluster_sync_mode}] does not support multiple slaves")

    global_data = {
        "uid": uid,
        "port": port,
        "backup_dbs": sync_dbs,
        "target_backup_dir": backup_path,
        "is_set_full_model": True,
        "job_id": f"restore_dr_{root_id}_{port}",
        "clean_dbs": clean_dbs if clean_dbs else sync_dbs,
        "clean_mode": SqlserverCleanMode.DROP_DBS.value,
        "clean_tables": ["*"],
        "ignore_clean_tables": [],
        "sync_mode": SqlserverSyncModeMaps[cluster_sync_mode],
        "slaves": [],
        "is_recalc_sync_dbs": is_recalc_sync_dbs,  # 判断标志位待入到全局上下文，获取payload进行判断
        "is_recalc_clean_dbs": is_recalc_clean_dbs,  # 判断标志位待入到全局上下文，获取payload进行判断
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 先禁用例行备份逻辑
    sub_pipeline.add_act(
        act_name=_("禁用backup jobs"),
        act_component_code=ExecSqlserverBackupJobComponent.code,
        kwargs=asdict(
            ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.DISABLE),
        ),
    )
    # 给所有的sync_slave下发执行器
    sub_pipeline.add_act(
        act_name=_("下发执行器"),
        act_component_code=TransFileInWindowsComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                target_hosts=sync_slaves + [master_host],
                file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
            ),
        ),
    )
    # 清理从库对应的数据库
    acts_list = []
    for slave in sync_slaves:
        acts_list.append(
            {
                "act_name": _("清理slave实例数据库[{}]".format(slave.ip)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[slave],
                        get_payload_func=SqlserverActPayload.get_clean_dbs_payload.__name__,
                        custom_params={"is_force": True},
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 执行备份
    sub_pipeline.add_act(
        act_name=_("执行数据库备份"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[master_host],
                get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                custom_params={
                    "port": port,
                    "file_tag": SqlserverBackupFileTagEnum.DBFILE1M.value,
                    "backup_type": SqlserverBackupMode.FULL_BACKUP.value,
                },
            )
        ),
        write_payload_var=SqlserverBackupIDContext.full_backup_id_var_name(),
    )
    # 执行数据库日志备份
    sub_pipeline.add_act(
        act_name=_("执行数据库日志备份"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[master_host],
                get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                custom_params={
                    "port": port,
                    "file_tag": SqlserverBackupFileTagEnum.INCREMENT_BACKUP.value,
                    "backup_type": SqlserverBackupMode.LOG_BACKUP.value,
                },
            )
        ),
        write_payload_var=SqlserverBackupIDContext.log_backup_id_var_name(),
    )
    # 传送备份文件
    sub_pipeline.add_act(
        act_name=_("传送文件到目标机器"),
        act_component_code=SqlserverTransBackupFileFor2P2Component.code,
        kwargs=asdict(
            P2PFileForWindowKwargs(
                source_hosts=[master_host],
                target_hosts=sync_slaves,
                file_target_path=backup_path,
                cluster_id=cluster.id,
                is_rolling=True,
            ),
        ),
    )
    # 恢复全量备份文件
    acts_list = []
    for slave in sync_slaves:
        acts_list.append(
            {
                "act_name": _("恢复全量备份数据[{}:{}]".format(slave.ip, port)),
                "act_component_code": RestoreForDoDrComponent.code,
                "kwargs": asdict(
                    RestoreForDoDrKwargs(
                        cluster_id=cluster.id,
                        job_id=global_data["job_id"],
                        restore_dbs=sync_dbs,
                        restore_mode=SqlserverRestoreMode.FULL,
                        exec_ips=[slave],
                        port=port,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    # 恢复日志备份文件
    acts_list = []
    for slave in sync_slaves:
        acts_list.append(
            {
                "act_name": _("恢复增量备份数据[{}:{}]".format(slave.ip, port)),
                "act_component_code": RestoreForDoDrComponent.code,
                "kwargs": asdict(
                    RestoreForDoDrKwargs(
                        cluster_id=cluster.id,
                        job_id=global_data["job_id"],
                        restore_dbs=sync_dbs,
                        restore_mode=SqlserverRestoreMode.LOG,
                        exec_ips=[slave],
                        port=port,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    # 建立数据库级别同步关系
    if cluster_sync_mode == SqlserverSyncMode.MIRRORING:
        custom_params = {"dr_host": sync_slaves[0].ip, "dr_port": port, "dbs": sync_dbs}
    else:
        custom_params = {
            "add_slaves": [{"host": i.ip, "port": port} for i in sync_slaves],
            "dbs": sync_dbs,
        }
    # 建立数据同步
    sub_pipeline.add_act(
        act_name=_("在master建立数据同步[{}]".format(master_host.ip)),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[master_host],
                get_payload_func=sync_payload_func_map[cluster_sync_mode],
                custom_params=custom_params,
            )
        ),
    )
    # 先禁用例行备份逻辑
    sub_pipeline.add_act(
        act_name=_("启动backup jobs"),
        act_component_code=ExecSqlserverBackupJobComponent.code,
        kwargs=asdict(
            ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.ENABLE),
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=sub_flow_name)


def install_surrounding_apps_sub_flow(
    uid: str,
    root_id: str,
    bk_biz_id: int,
    bk_cloud_id: int,
    slave_host: List[Host],
    master_host: List[Host],
    cluster_domain_list: List[str],
    is_install_backup_client: bool = True,
    is_init_app_setting: bool = True,
    is_init_nginx: bool = True,
    is_get_old_backup_config: bool = False,
    nginx_exclude_ips: Optional[List[str]] = None,
) -> SubProcess:
    """SQLServer 周边程序安装的通用子流程（不跨业务、不跨云区域）。

    设计要点 / 怎么做：
      - 数据源：master_host + slave_host 去重后的 IP 列表 + cluster_domain_list。
      - 编排顺序：三类动作按开关拼装到并发列表，一次并发下发。
      - 周边动作：
          * 安装 backup-client 工具（机器粒度，一次覆盖去重 IP）
          * 初始化每个集群的 app_setting 表（记录集群元信息到实例）
          * 初始化每个集群的 nginx 反代配置（用于 dbm 侧访问）
      - is_get_old_backup_config=True 时，app_setting 初始化会读取历史备份配置进行兼容
        （内部导入标准化专属场景）。
      - nginx_exclude_ips 仅作用于 nginx 反代配置初始化节点：命中的机器（按 IP 匹配）
        其名下所有实例都不再下发 nginx 配置；不影响 backup-client / app_setting 节点。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param bk_biz_id: 业务 id，用于 backup-client 安装的业务隔离
    :param bk_cloud_id: 云区域 id，backup-client 安装通道
    :param slave_host: 从实例所在机器列表
    :param master_host: 主实例所在机器列表
    :param cluster_domain_list: 本次涉及的集群主域名列表
    :param is_install_backup_client: 是否安装 backup-client 工具，默认 True
    :param is_init_app_setting: 是否初始化 app_setting 表，默认 True
    :param is_init_nginx: 是否初始化 nginx 反代配置，默认 True
    :param is_get_old_backup_config: 是否读取旧备份配置（内部导入标准化专属），默认 False
    :param nginx_exclude_ips: nginx 初始化时需要排除的机器 IP 列表；默认 None（不排除）；
                              典型场景：机器已下架/隔离/待剔除，避免下发 nginx 配置到失联机器；
                              仅作用于 nginx 节点，透传给 InitDBMNginxForSQLServerKwargs.exclude_ips
    :return: SubProcess，子流程节点名为 "部署sqlserver周边程序"

    边界 / 异常：
      - 三个开关全部为 False -> 抛 Exception（生成空并发节点无意义，直接拦截）。
      - master_host + slave_host 全部为空 IP -> unique_ips 为空，各 Component 内部处理。
      - 假设所有机器同属 bk_biz_id / bk_cloud_id；跨业务/跨云调用请拆分为多个子流程。
      - nginx_exclude_ips 命中后该集群下无剩余实例 -> 由
        InitDBMNginxForSQLServerService 内部抛异常中止流程，本函数不做二次拦截。
    """
    # 构建子流程global_data
    global_data = {
        "uid": uid,
        "root_id": root_id,
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 提取所有主从实例的去重 IP 列表（过滤空值）
    unique_ips = list({host.ip for host in master_host + slave_host if host.ip})

    acts_list = []
    if is_install_backup_client:
        acts_list.append(
            {
                "act_name": _("安装backup-client工具"),
                "act_component_code": DownloadBackupClientComponent.code,
                "kwargs": asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=bk_cloud_id,
                        bk_biz_id=bk_biz_id,
                        ip_list=unique_ips,
                    )
                ),
            }
        )
    if is_init_app_setting:
        for cluster_domain in cluster_domain_list:
            acts_list.append(
                {
                    "act_name": _("集群[{}]初始化app_setting表".format(cluster_domain)),
                    "act_component_code": InsertAppSettingComponent.code,
                    "kwargs": asdict(
                        InsertAppSettingKwargs(
                            cluster_domain=cluster_domain,
                            ips=unique_ips,
                            is_get_old_backup_config=is_get_old_backup_config,
                        )
                    ),
                }
            )
    # 对dbm的nginx初始化
    if is_init_nginx:
        # 归一化为 list：调用方未传或显式传 None 时，等价于"不排除任何机器"
        # 语义与 InitDBMNginxForSQLServerKwargs.exclude_ips 的默认值（空列表）保持一致
        exclude_ips_for_nginx: List[str] = list(nginx_exclude_ips or [])
        for cluster_domain in cluster_domain_list:
            acts_list.append(
                {
                    "act_name": _("集群[{}]初始化nginx配置".format(cluster_domain)),
                    "act_component_code": InitDBMNginxForSQLServerComponent.code,
                    "kwargs": asdict(
                        InitDBMNginxForSQLServerComponent.kwargs(
                            cluster_domain=cluster_domain,
                            exclude_ips=exclude_ips_for_nginx,
                        )
                    ),
                }
            )
    if not acts_list:
        raise Exception(_("install_surrounding_apps_sub_flow的子流程列表为空"))

    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("部署sqlserver周边程序"))


def build_always_on_sub_flow(
    uid: str,
    root_id: str,
    master_instance: SqlserverInstance,
    slave_instances: List[SqlserverInstance],
    cluster_name: str,
    group_name: str,
    is_use_sa: bool = False,
) -> SubProcess:
    """建立集群 AlwaysOn 可用组的子流程。

    设计要点 / 怎么做：
      - 数据源：入参 master_instance + slave_instances（均为 SqlserverInstance），
        通过 host / bk_cloud_id 字段转换为 Host 对象用于介质下发与 actuator 执行。
      - 编排顺序：下发 db-actuator 介质 -> 并发在每台机器执行 AlwaysOn 别名初始化 ->
        在主实例上创建可用组并纳管 slaves。
      - is_new 语义：
          * is_new=True  的机器视为"本次新加入"，需要把集群内所有其它节点信息告知它；
          * is_new=False 的机器为"已在集群中"，只需把本次新加入的节点信息补齐即可。
      - 通道：SqlserverActuatorScriptComponent（Windows 上通过 db-actuator 执行 T-SQL）。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param master_instance: 集群主实例（承担 primary replica）；is_new 决定其在别名初始化时是否为首次
    :param slave_instances: 集群从实例列表；is_new=True 的将作为 add_slaves 加入可用组
    :param cluster_name: 集群名称，用于子流程节点展示名
    :param group_name: AlwaysOn 可用组名称（Availability Group Name）
    :param is_use_sa: 是否使用 sa 账号执行；默认 False，走 DBM 管理账号；
                     True 时兼容"集群部署阶段（DBM 账号尚未就绪）"场景
    :return: SubProcess，子流程节点名为 "集群[{cluster_name}]建立AlwaysOn可用组"

    边界 / 异常：
      - slave_instances 为空 -> 允许（仅初始化 primary，可用组无 secondary replica），
        但下游 actuator 若不支持零 secondary 会抛异常，由调用方保证语义。
      - master_instance / slave_instances 中出现同一 (ip, bk_cloud_id) 的多实例
        -> 下发执行器阶段按 (ip, bk_cloud_id) 去重，避免重复下发介质。
      - 入参实例的 host / bk_cloud_id 非法 -> 由上游 validate_instances 保证，本函数不再二次校验。
    """
    global_data = {
        "uid": uid,
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 拼接下发执行器的目标机器列表：
    #   - 数据来源：master_instance + slave_instances（均为 SqlserverInstance）
    #   - 转换规则：SqlserverInstance.host / bk_cloud_id -> Host(ip, bk_cloud_id)
    #   - 去重规则：按 (ip, bk_cloud_id) 去重，避免同一台机器多实例场景重复下发
    #   - 用途：后续在这些机器上执行 alwaysOn 别名初始化、建立可用组等 actuator 动作，
    #           因此必须先把 db-actuator 介质下发到位
    _seen_hosts: set = set()
    target_hosts: List[Host] = []
    for _inst in [master_instance] + slave_instances:
        _key = (_inst.host, _inst.bk_cloud_id)
        if _key in _seen_hosts:
            continue
        _seen_hosts.add(_key)
        target_hosts.append(Host(ip=_inst.host, bk_cloud_id=_inst.bk_cloud_id))

    # 给所有参与 alwaysOn 的机器下发执行器
    sub_pipeline.add_act(
        act_name=_("下发执行器"),
        act_component_code=TransFileInWindowsComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                target_hosts=target_hosts,
                file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
            ),
        ),
    )

    # 为配置AlwaysOn可用组，对所有新加入的机器做对应初始化
    acts_list = []
    cluster_instances = [master_instance] + slave_instances
    for inst in cluster_instances:
        add_instances = copy.deepcopy(cluster_instances)
        # add_instances.remove(inst)
        if inst.is_new:
            # 表示机器是新加入，应该加入集群所有的节点信息到新机器上
            add_instances.remove(inst)
            add_members = [asdict(s) for s in add_instances]
        else:
            # 表示机器已经加入到集群内，则只加入新机器节点信息即可
            add_members = [asdict(s) for s in add_instances if s.is_new]

        acts_list.append(
            {
                "act_name": _("[{}]为alwaysOn做别名初始化".format(inst.host)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=inst.host, bk_cloud_id=inst.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_init_machine_for_always_on.__name__,
                        custom_params={
                            "port": inst.port,
                            "add_members": add_members,
                            "is_first": inst.is_new,
                            "is_use_sa": is_use_sa,
                        },
                    )
                ),
            }
        )

    sub_pipeline.add_parallel_acts(acts_list)

    # 在主实例配置AlwaysOn可用组
    sub_pipeline.add_act(
        act_name=_("[{}]集群配置可用组".format(cluster_name)),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[Host(ip=master_instance.host, bk_cloud_id=master_instance.bk_cloud_id)],
                get_payload_func=SqlserverActPayload.get_build_always_on.__name__,
                custom_params={
                    "port": master_instance.port,
                    "add_slaves": [asdict(s) for s in slave_instances if s.is_new],
                    "group_name": group_name,
                    "is_first": master_instance.is_new,
                    "is_use_sa": is_use_sa,
                },
            )
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=_("集群[{}]建立AlwaysOn可用组".format(cluster_name)))


def download_backup_file_sub_flow(
    uid: str,
    root_id: str,
    backup_file_list: List[str],
    target_path: str,
    write_payload_var: str,
    target_instance: StorageInstance,
    sub_name: str = _("下载备份文件"),
) -> SubProcess:
    """下载备份文件到目标实例所在机器的通用子流程（本地优先 + 备份系统兜底）。

    设计要点 / 怎么做：
      - 编排顺序：
          1) 在目标机器上判断备份文件是否已存在本地；
             若存在则本地移动到 target_path，结果（文件路径元信息）写入上下文
             变量 write_payload_var；
          2) 调用备份系统下载文件到 target_path；下载组件优先读取上下文变量，
             若已本地就绪则跳过实际下载动作。
      - 上下文变量传递：write_payload_var 由步骤 1 写入、步骤 2 消费，实现"本地命中即跳过下载"。
      - 通道：SqlserverActuatorScriptComponent + SqlserverDownloadBackupFileComponent。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param backup_file_list: 待下载/查找的备份文件名列表
    :param target_path: 目标机器上备份文件的存放目录（Windows 路径）
    :param write_payload_var: 上下文变量名，用于在两步之间传递"本地是否命中"的结果
    :param target_instance: 目标实例（StorageInstance），取机器 IP / bk_cloud_id
    :param sub_name: 子流程节点显示名，默认 "下载备份文件"
    :return: SubProcess，子流程节点名由 sub_name 指定

    边界 / 异常：
      - backup_file_list 为空 -> 本地判断节点入参为空，行为由 actuator 定义，通常应由调用方保证。
      - 目标机器磁盘不足 / target_path 无写权限 -> 由下载组件抛异常中止流程。
      - 备份系统查不到文件 -> 由 SqlserverDownloadBackupFileComponent 抛业务异常。
    """
    # 构建子流程global_data
    global_data = {
        "uid": uid,
        "root_id": root_id,
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 判断备份文件是否存在，如果存在则移动对应恢复目录, 结果写入上下文
    sub_pipeline.add_act(
        act_name=_("判断备份文件存在本地机器"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[Host(ip=target_instance.machine.ip, bk_cloud_id=target_instance.machine.bk_cloud_id)],
                get_payload_func=SqlserverActPayload.check_backup_file_is_in_local.__name__,
                custom_params={"target_path": target_path, "file_list": backup_file_list},
            )
        ),
        write_payload_var=write_payload_var,
    )

    # 备份系统下载文件
    sub_pipeline.add_act(
        act_name=_("下载备份文件"),
        act_component_code=SqlserverDownloadBackupFileComponent.code,
        kwargs=asdict(
            DownloadBackupFileKwargs(
                bk_cloud_id=target_instance.machine.bk_cloud_id,
                dest_ip=target_instance.machine.ip,
                dest_dir=target_path,
                get_backup_file_info_var=write_payload_var,
            )
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=sub_name)


def switch_cluster_sub_flow(
    uid: str,
    root_id: str,
    cluster: Cluster,
    old_master_host: Host,
    new_master_host: Host,
    port: int,
    sync_mode_number: int,
    other_slaves: List[Dict],
    force: bool = False,
    sub_name: str = _("切换集群"),
) -> Optional[SubProcess]:
    """执行集群切换（旧主 -> 新主）的完整子流程。

    设计要点 / 怎么做：
      - 编排顺序：
          1) 非强切场景下先做预检测（异常 DB / 业务连接 / 未同步 DB）
          2) 非强切场景下先克隆 user + LinkServer（保证切换前该类信息在新主上已就绪）
          3) 执行切换动作（在新主上执行 actuator 切换 payload）
          4) 非强切场景下再克隆 Jobs（切换后再克隆，避免旧主 Job 干扰）
      - 强切策略：force=True 时跳过所有克隆和预检测，直接切换（用于主故障场景）。
      - 通道：pre_check_sub_flow / clone_configs_sub_flow / SqlserverActuatorScriptComponent。

    :param uid: 单据 id，用于全局上下文透传，必填
    :param root_id: 主流程 root_id，SubBuilder 归属，必填
    :param cluster: 集群对象，用于取 bk_biz_id / db_module_id / immute_domain / bk_cloud_id
    :param old_master_host: 集群原主机器
    :param new_master_host: 集群新主机器
    :param port: 实例端口（主/从同端口）
    :param sync_mode_number: 同步模式编号（数值枚举，透传给 actuator 切换 payload）
    :param other_slaves: 其余从实例列表（兼容一主多从集群，格式由 actuator 定义）
    :param force: 是否强制切换（主故障场景）；True 时跳过预检测和克隆，默认 False
    :param sub_name: 子流程节点显示名，默认 "切换集群"
    :return: Optional[SubProcess]，子流程节点名由 sub_name 指定

    边界 / 异常：
      - force=True -> 跳过 pre_check / user 克隆 / LinkServer 克隆 / Jobs 克隆。
      - 集群未配置备份路径 -> get_sqlserver_backup_config 内部按默认值兜底。
      - 切换 actuator 失败 -> 中止流程，元数据不会被更新（元数据更新由外层 pipeline 负责）。
    """
    # 获取集群的备份位置
    backup_space = get_sqlserver_backup_config(
        bk_biz_id=cluster.bk_biz_id,
        db_module_id=cluster.db_module_id,
        cluster_domain=cluster.immute_domain,
    )["backup_space"]

    sub_pipeline = SubBuilder(root_id=root_id, data={"uid": uid, "root_id": root_id})

    if not force:
        # 如果是强制模式，不做预检测, 不做克隆
        sub_pipeline.add_sub_pipeline(
            sub_flow=pre_check_sub_flow(
                uid=uid,
                root_id=root_id,
                check_host=old_master_host,
                check_port=port,
                cluster_id=cluster.id,
            )
        )

        # 先做克隆user和link_server，保证这块内容切换前是同步的
        sub_pipeline.add_sub_pipeline(
            sub_flow=clone_configs_sub_flow(
                uid=uid,
                root_id=root_id,
                bk_biz_id=cluster.bk_biz_id,
                source_host=old_master_host,
                source_port=port,
                target_host=new_master_host,
                target_port=port,
                is_clone_user=True,
                is_clone_jobs=False,
                is_clone_linkserver=True,
                sub_flow_name=_("克隆user和Link_server配置"),
            )
        )

    # 执行切换
    sub_pipeline.add_act(
        act_name=_("执行切换"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[new_master_host],
                get_payload_func=SqlserverActPayload.get_switch_payload.__name__,
                component_kwargs={
                    "target_port": port,
                    "master_host": old_master_host.ip,
                    "master_port": port,
                    "sync_mode": sync_mode_number,
                    "other_slaves": other_slaves,
                    "force": force,
                    "backup_space": backup_space,
                },
            )
        ),
    )

    if not force:
        # 再克隆job
        sub_pipeline.add_sub_pipeline(
            sub_flow=clone_configs_sub_flow(
                uid=uid,
                root_id=root_id,
                bk_biz_id=cluster.bk_biz_id,
                source_host=old_master_host,
                source_port=port,
                target_host=new_master_host,
                target_port=port,
                is_clone_user=False,
                is_clone_jobs=True,
                is_clone_linkserver=False,
                sub_flow_name=_("克隆job配置"),
            )
        )

    return sub_pipeline.build_sub_process(sub_name=sub_name)
