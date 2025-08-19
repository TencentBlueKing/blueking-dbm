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

import copy
import logging.config
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import MYSQL_DATA_RESTORE_TIME, MYSQL_USUAL_JOB_TIME
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.mysql.mysql_backup.handers import MySQLBackupHandler
from backend.flow.consts import MysqlChangeMasterType, RollbackType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.mysql_restore_download_sub_flow import (
    mysql_restore_download_sub_flow,
)
from backend.flow.engine.bamboo.scene.spider.common.exceptions import (
    TendbGetBackupInfoFailedException,
    TendbGetBinlogFailedException,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


def mysql_restore_data_sub_flow(
    root_id: str, ticket_data: dict, cluster: dict, cluster_model: Cluster, filter_ips: list = None
):
    """
    定义 TenDB HA 和 TenDB Cluster 单节点恢复数据的子流程，使用本地备份文件

    该函数实现了单节点数据恢复的完整流程，包括：
    1. 获取最新的备份信息
    2. 下载备份文件到目标服务器
    3. 恢复新从节点的数据
    4. 建立新从库指向旧主库的主从关系（可选）
    5. 恢复数据库权限（可选，仅TenDB HA）

    @param root_id: 流程的根ID，用于标识整个流程实例
    @param ticket_data: 工单数据，包含用户ID等基本信息
    @param cluster: 集群配置信息，包含以下关键字段：
                   - cluster_id: 集群ID
                   - new_slave_ip: 新从节点IP
                   - new_slave_port: 新从节点端口
                   - master_ip: 原主节点IP
                   - master_port: 原主节点端口
                   - file_target_path: 备份文件目标路径
                   - backup_source: 备份源类型（本地/远程）
                   - backup_id: 指定备份ID（可选）
                   - binlog_sync: 是否同步binlog建立主从关系
                   - shard_id: 分片ID（TenDB Cluster专用）
                   - restore_privilege: 是否恢复权限
                   - privilege_ips: 权限来源IP列表
    @param cluster_model: 集群元数据模型对象
    @param filter_ips: 过滤的IP列表，用于指定备份查询范围
    @return: 返回构建好的子流程对象，包含完整的恢复流程
    """
    # 创建子流程构建器
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取配置参数
    backup_id = cluster.get("backup_id", None)  # 指定备份ID，可选
    binlog_sync = cluster.get("binlog_sync", True)  # 是否同步binlog建立主从关系，默认True

    # 初始化备份处理器，用于获取集群的最新备份信息
    backup_handler = MySQLBackupHandler(
        cluster_id=cluster_model.id,
        is_full_backup=True,
        check_instance_exist=True,
        filter_ips=filter_ips,
        backup_id=backup_id,
    )

    # 如果是TenDB Single类型，设置为增量备份
    if cluster_model.cluster_type == ClusterType.TenDBSingle:
        backup_handler.is_full_backup = False

    # 阶段1: 查询备份信息
    # 如果是TenDB Cluster类型，需要设置分片ID
    if cluster_model.cluster_type == ClusterType.TenDBCluster:
        backup_handler.shard_id = int(cluster["shard_id"])

    # 获取最新的备份信息
    backup_info = backup_handler.get_tendb_latest_backup_info()

    # 检查备份信息是否存在
    if backup_info is None:
        logger.error("cluster {} backup info not exists".format(cluster_model.id))
        raise TendbGetBackupInfoFailedException(
            message=_(
                "获取集群 {} 备份信息失败, 错误信息: {} , 备份查询语句: {}".format(
                    cluster_model.id, backup_handler.errmsg, backup_handler.query
                )
            )
        )
    cluster["backupinfo"] = backup_info

    # 阶段2: 下载备份文件
    # 根据备份源类型（本地/远程）确定下载参数
    if cluster["backup_source"] == MySQLBackupSource.LOCAL:
        # 本地备份：从备份主机下载
        download_source_ip = backup_info["backup_host"]
        task_ids = backup_info["local_files"]
    else:
        # 远程备份：从远程存储下载
        download_source_ip = None
        task_ids = backup_info["task_ids"]

    # 添加下载备份文件的子流程
    sub_pipeline.add_sub_pipeline(
        sub_flow=mysql_restore_download_sub_flow(
            root_id=root_id,
            uid=ticket_data["uid"],
            bk_cloud_id=cluster["bk_cloud_id"],
            file_target_path=cluster["file_target_path"],
            task_ids=task_ids,
            dest_ips=[cluster["new_slave_ip"]],
            source_ip=download_source_ip,
        )
    )

    # 初始化执行器参数
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_model.bk_cloud_id,
        cluster_type=cluster_model.cluster_type,
    )

    # 阶段3: 恢复新从节点的数据
    # 配置恢复参数
    cluster["restore_ip"] = cluster["new_slave_ip"]
    cluster["restore_port"] = cluster["new_slave_port"]
    cluster["source_ip"] = cluster["master_ip"]
    cluster["source_port"] = cluster["master_port"]
    # 恢复数据完毕不自动 change master，避免影响后续的主从关系建立
    cluster["change_master"] = False

    # 设置恢复任务参数
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.job_timeout = MYSQL_DATA_RESTORE_TIME
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_restore_remotedb_payload.__name__
    # 添加数据恢复任务
    sub_pipeline.add_act(
        act_name=_(
            "恢复新从节点数据 {}:{} 备份backup_id: {}".format(
                exec_act_kwargs.exec_ip, cluster["restore_port"], backup_info["backup_id"]
            )
        ),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )

    # 阶段4: 建立主从关系 - 新从库指向旧主库（可选）
    # 根据binlog_sync配置决定是否建立主从关系
    if binlog_sync:
        # 在旧主库上为新从库创建复制用户
        cluster["target_ip"] = cluster["master_ip"]
        cluster["target_port"] = cluster["master_port"]
        cluster["repl_ip"] = cluster["new_slave_ip"]
        exec_act_kwargs.cluster = copy.deepcopy(cluster)
        exec_act_kwargs.exec_ip = cluster["master_ip"]
        exec_act_kwargs.job_timeout = MYSQL_USUAL_JOB_TIME
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_grant_remotedb_repl_user.__name__
        sub_pipeline.add_act(
            act_name=_("新增repl帐户{}".format(exec_act_kwargs.exec_ip)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        # 配置新从库指向旧主库的主从关系参数
        cluster["repl_ip"] = cluster["new_slave_ip"]
        cluster["repl_port"] = cluster["new_slave_port"]
        cluster["target_ip"] = cluster["master_ip"]
        cluster["target_port"] = cluster["master_port"]
        # 使用备份文件的方式建立主从关系
        cluster["change_master_type"] = MysqlChangeMasterType.BACKUPFILE.value
        exec_act_kwargs.cluster = copy.deepcopy(cluster)
        exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_remotedb_change_master.__name__
        sub_pipeline.add_act(
            act_name=_("建立主从关系 {}:{}".format(exec_act_kwargs.exec_ip, cluster["repl_port"])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
    # 阶段5: 恢复数据库权限（可选，仅TenDB HA）
    # 如果是TenDB HA集群且要求恢复权限，则从其他实例恢复权限到新从节点
    if cluster_model.cluster_type == ClusterType.TenDBHA and cluster.get("restore_privilege", False):
        privilege_ips = cluster.get("privilege_ips", None)
        restore_priv_sub_pipeline = priv_recover_sub_flow(
            root_id=root_id,
            ticket_data=ticket_data,
            cluster_model=cluster_model,
            ips=[cluster["new_slave_ip"]],
            privilege_ips=privilege_ips,
        )
        if restore_priv_sub_pipeline is not None:
            sub_pipeline.add_sub_pipeline(restore_priv_sub_pipeline)

    # 构建并返回完整的子流程
    return sub_pipeline.build_sub_process(
        sub_name=_("恢复数据{} backup_id: {}".format(exec_act_kwargs.exec_ip, backup_info["backup_id"]))
    )


def mysql_restore_master_slave_sub_flow(
    root_id: str, ticket_data: dict, cluster: dict, cluster_model: Cluster, filter_ips: list = None
):
    """
    定义 TenDB HA 和 TenDB Cluster 主从成对恢复的子流程，使用本地备份文件

    该函数实现了主从成对恢复的完整流程，包括：
    1. 获取最新的备份信息
    2. 下载备份文件到目标服务器
    3. 并行恢复新主节点和新从节点的数据
    4. 建立新从库指向新主库的主从关系
    5. 建立新主库指向旧主库的主从关系
    6. 恢复数据库权限（可选）

    @param root_id: 流程的根ID，用于标识整个流程实例
    @param ticket_data: 工单数据，包含用户ID等基本信息
    @param cluster: 集群配置信息，包含以下关键字段：
                   - cluster_id: 集群ID
                   - new_master_ip: 新主节点IP
                   - new_master_port: 新主节点端口
                   - new_slave_ip: 新从节点IP
                   - new_slave_port: 新从节点端口
                   - master_ip: 原主节点IP
                   - master_port: 原主节点端口
                   - file_target_path: 备份文件目标路径
                   - backup_source: 备份源类型（本地/远程）
                   - shard_id: 分片ID（TenDB Cluster专用）
                   - restore_privilege: 是否恢复权限
                   - privilege_ips: 权限来源IP列表
    @param cluster_model: 集群元数据模型对象
    @param filter_ips: 过滤的IP列表，用于指定备份查询范围
    @return: 返回构建好的子流程对象，包含完整的恢复流程
    """
    # 创建子流程构建器
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 初始化备份处理器，用于获取集群的最新备份信息
    backup_handler = MySQLBackupHandler(
        cluster_id=cluster["cluster_id"], is_full_backup=True, check_instance_exist=True, filter_ips=filter_ips
    )

    # 如果是TenDB Cluster类型，需要设置分片ID
    if cluster_model.cluster_type == ClusterType.TenDBCluster:
        backup_handler.shard_id = int(cluster["shard_id"])

    # 获取最新的备份信息
    backup_info = backup_handler.get_tendb_latest_backup_info()
    if backup_info is None:
        logger.error("cluster {} backup info not exists".format(cluster_model.id))
        raise TendbGetBackupInfoFailedException(
            message=_(
                "获取集群 {} 备份信息失败, 错误信息: {} 备份查询语句: {}".format(
                    cluster_model.id, backup_handler.errmsg, backup_handler.query
                )
            )
        )
    cluster["backupinfo"] = backup_info

    # 阶段3: 下载备份文件
    # 根据备份源类型（本地/远程）确定下载参数
    if cluster["backup_source"] == MySQLBackupSource.LOCAL:
        # 本地备份：从备份主机下载
        download_source_ip = backup_info["backup_host"]
        task_ids = backup_info["local_files"]
    else:
        # 远程备份：从远程存储下载
        download_source_ip = None
        task_ids = backup_info["task_ids"]

    # 添加下载备份文件的子流程
    sub_pipeline.add_sub_pipeline(
        sub_flow=mysql_restore_download_sub_flow(
            root_id=root_id,
            uid=ticket_data["uid"],
            bk_cloud_id=cluster_model.bk_cloud_id,
            file_target_path=cluster["file_target_path"],
            task_ids=task_ids,
            dest_ips=[cluster["new_slave_ip"], cluster["new_master_ip"]],
            source_ip=download_source_ip,
        )
    )

    # 阶段4: 并行恢复数据
    # 初始化执行器参数
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_model.bk_cloud_id,
        cluster_type=cluster_model.cluster_type,
    )
    restore_list = []

    # 配置新主节点的恢复参数
    cluster["restore_ip"] = cluster["new_master_ip"]
    cluster["restore_port"] = cluster["new_master_port"]
    cluster["source_ip"] = cluster["master_ip"]
    cluster["source_port"] = cluster["master_port"]
    # 恢复数据完毕不自动 change master，避免影响后续的主从关系建立
    cluster["change_master"] = False

    # 设置新主节点恢复任务
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.job_timeout = MYSQL_DATA_RESTORE_TIME
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_restore_remotedb_payload.__name__
    restore_list.append(
        {
            "act_name": _(
                "恢复新主节点数据 {}:{} 备份backup_id: {}".format(
                    exec_act_kwargs.exec_ip, cluster["restore_port"], backup_info["backup_id"]
                )
            ),
            "act_component_code": ExecuteDBActuatorScriptComponent.code,
            "kwargs": asdict(exec_act_kwargs),
            "write_payload_var": "change_master_info",
        }
    )

    # 配置新从节点的恢复参数
    cluster["restore_ip"] = cluster["new_slave_ip"]
    cluster["restore_port"] = cluster["new_slave_port"]
    cluster["source_ip"] = cluster["master_ip"]
    cluster["source_port"] = cluster["master_port"]
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_restore_remotedb_payload.__name__
    restore_list.append(
        {
            "act_name": _(
                "恢复新从节点数据 {}:{} 备份backup_id: {}".format(
                    exec_act_kwargs.exec_ip, cluster["restore_port"], backup_info["backup_id"]
                )
            ),
            "act_component_code": ExecuteDBActuatorScriptComponent.code,
            "kwargs": asdict(exec_act_kwargs),
        }
    )

    # 并行执行新主节点和新从节点的数据恢复
    sub_pipeline.add_parallel_acts(acts_list=restore_list)

    # 阶段5: 建立主从关系 - 新从库指向新主库
    # 在新主库上为从库创建复制用户
    cluster["target_ip"] = cluster["new_master_ip"]
    cluster["target_port"] = cluster["new_master_port"]
    cluster["repl_ip"] = cluster["new_slave_ip"]
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.job_timeout = MYSQL_USUAL_JOB_TIME
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_grant_remotedb_repl_user.__name__
    sub_pipeline.add_act(
        act_name=_("新增repl帐户{}".format(exec_act_kwargs.exec_ip)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="show_master_status_info",
    )

    # 配置新从库指向新主库的主从关系参数
    cluster["repl_ip"] = cluster["new_slave_ip"]
    cluster["repl_port"] = cluster["new_slave_port"]
    cluster["target_ip"] = cluster["new_master_ip"]
    cluster["target_port"] = cluster["new_master_port"]
    # 使用show master status的方式建立主从关系
    cluster["change_master_type"] = MysqlChangeMasterType.MASTERSTATUS.value
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_remotedb_change_master.__name__
    sub_pipeline.add_act(
        act_name=_("建立主从关系:新从库指向新主库 {} {}:".format(exec_act_kwargs.exec_ip, cluster["repl_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 阶段6: 建立主从关系 - 新主库指向旧主库
    # 在旧主库上为新主库创建复制用户
    cluster["target_ip"] = cluster["master_ip"]
    cluster["target_port"] = cluster["master_port"]
    cluster["repl_ip"] = cluster["new_master_ip"]
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_grant_remotedb_repl_user.__name__
    sub_pipeline.add_act(
        act_name=_("新增repl帐户{}".format(exec_act_kwargs.exec_ip)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 配置新主库指向旧主库的主从关系参数
    cluster["repl_ip"] = cluster["new_master_ip"]
    cluster["repl_port"] = cluster["new_master_port"]
    cluster["target_ip"] = cluster["master_ip"]
    cluster["target_port"] = cluster["master_port"]
    # 使用备份文件的方式建立主从关系
    cluster["change_master_type"] = MysqlChangeMasterType.BACKUPFILE.value
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_remotedb_change_master.__name__
    sub_pipeline.add_act(
        act_name=_("建立主从关系:新主库指向旧主库 {}:{}".format(exec_act_kwargs.exec_ip, cluster["repl_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    # 阶段7: 恢复数据库权限（可选）
    # TenDB HA主从成对迁移是2个is_stand_by的迁移，权限对等，这里补充恢复权限
    if cluster_model.cluster_type == ClusterType.TenDBHA.value and cluster.get("restore_privilege", False):
        privilege_ips = cluster.get("privilege_ips", None)
        restore_priv_sub_pipeline = priv_recover_sub_flow(
            root_id=root_id,
            ticket_data=ticket_data,
            cluster_model=cluster_model,
            ips=[cluster["new_slave_ip"], cluster["new_master_ip"]],
            privilege_ips=privilege_ips,
        )
        if restore_priv_sub_pipeline is not None:
            sub_pipeline.add_sub_pipeline(restore_priv_sub_pipeline)

    # 构建并返回完整的子流程
    return sub_pipeline.build_sub_process(
        sub_name=_("主从成对恢复数据 {} backup_id: {}".format(exec_act_kwargs.exec_ip, backup_info["backup_id"]))
    )


def priv_recover_sub_flow(
    root_id: str, ticket_data: dict, cluster_model: Cluster, ips: list, privilege_ips: list = None
):
    """
    定义 tendbHa 从集群备份的主从节点恢复权限。这里主要用于恢复从节点权限,补充主从权限差异时slave重建直接从 。
    恢复权限目前只从远程下载权限文件
    主节点克隆权限可能有权限不全的问题。
    tendb privilege recover 指定实例权限恢复。
    @param root_id:  flow流程的root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_model:  cluster对象
    @param ips: 实例ip
    @param privilege_ips:  指定查询权限的过滤ip
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    backup_handler = MySQLBackupHandler(cluster_id=cluster_model.id, filter_ips=privilege_ips)
    backup_info = backup_handler.get_tendb_priv_backup_info()
    if backup_info is None:
        logger.error("cluster {} backup info not exists".format(cluster_model.id))
        return None

    storages = cluster_model.storageinstance_set.filter(machine__ip__in=ips)
    priv_sub_pipeline_list = []
    for storage in storages:
        priv_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
        cluster = {
            "cluster_id": cluster_model.id,
            "file_target_path": f"/data/dbbak/{root_id}/{storage.port}/restore_priv",
            "sql_files": backup_info["priv_files"],
            "port": storage.port,
            "force": False,
        }

        sub_pipeline.add_sub_pipeline(
            sub_flow=mysql_restore_download_sub_flow(
                root_id=root_id,
                uid=ticket_data["uid"],
                bk_cloud_id=cluster_model.bk_cloud_id,
                file_target_path=cluster["file_target_path"],
                task_ids=backup_info["task_ids"],
                dest_ips=[storage.machine.ip],
                source_ip=None,
            )
        )
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=cluster_model.bk_cloud_id,
            cluster_type=cluster_model.cluster_type,
            cluster=copy.deepcopy(cluster),
            job_timeout=MYSQL_USUAL_JOB_TIME,
            get_mysql_payload_func=MysqlActPayload.tendb_restore_priv_payload.__name__,
            exec_ip=storage.machine.ip,
        )
        priv_sub_pipeline.add_act(
            act_name=_("权限恢复 {} 权限backup_id: {}".format(storage.ip_port, backup_info["backup_ids"])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        priv_sub_pipeline_list.append(
            priv_sub_pipeline.build_sub_process(sub_name=_(_("{}权限恢复").format(storage.ip_port)))
        )

    if len(priv_sub_pipeline_list) > 0:
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=priv_sub_pipeline_list)
        return sub_pipeline.build_sub_process(sub_name=_("集群{}恢复权限".format(cluster_model.id)))
    else:
        return None


def tendbha_rollback_data_sub_flow(root_id: str, uid: str, cluster_model: Cluster, cluster_info: dict):
    """
    tendbHa 回档流程
    @param root_id: flow 流程root_id
    @param uid: 单据 uid
    @param cluster_model: 关联的cluster对象
    @param cluster_info: 关联的cluster对象
    """
    #  阶段1 查询备份
    rollback_time = None
    check_instance_exist = False
    cluster_info["recover_binlog"] = False
    if (
        cluster_info["rollback_type"] == RollbackType.LOCAL_AND_TIME
        or cluster_info["rollback_type"] == RollbackType.REMOTE_AND_TIME
    ):
        cluster_info["recover_binlog"] = True
        rollback_time = str2datetime(cluster_info["rollback_time"])
    if (
        cluster_info["rollback_type"] == RollbackType.LOCAL_AND_BACKUPID
        or cluster_info["rollback_type"] == RollbackType.LOCAL_AND_TIME
    ):
        check_instance_exist = True

    # 指定了backup_id,则查询只用backup_id作为条件
    backup_id = cluster_info.get("backup_id", None)
    backup_handler = MySQLBackupHandler(
        cluster_id=cluster_model.id,
        is_full_backup=True,
        backup_id=backup_id,
        check_instance_exist=check_instance_exist,
    )
    backup_info = backup_handler.get_tendb_latest_backup_info(latest_time=rollback_time)
    if backup_info is None:
        logger.error("cluster {} backup info not exists".format(cluster_model.id))
        raise TendbGetBackupInfoFailedException(
            message=_(
                "获取集群 {} 备份信息失败,错误信息 {} 备份查询语句: {}".format(
                    cluster_model.id, backup_handler.errmsg, backup_handler.query
                )
            )
        )
    cluster_info["backupinfo"] = copy.deepcopy(backup_info)
    cluster_info["backup_time"] = backup_info["backup_time"]
    backup_time = str2datetime(backup_info["backup_time"])

    if (
        cluster_info["rollback_type"] == RollbackType.LOCAL_AND_BACKUPID
        or cluster_info["rollback_type"] == RollbackType.LOCAL_AND_TIME
    ):
        download_source_ip = backup_info["backup_host"]
        task_ids = backup_info["local_files"]
    else:
        download_source_ip = None
        task_ids = backup_info["task_ids"]

    # 阶段2 下载备份文件
    cluster_info["uid"] = uid
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(cluster_info))
    sub_pipeline.add_sub_pipeline(
        sub_flow=mysql_restore_download_sub_flow(
            root_id=root_id,
            uid=uid,
            bk_cloud_id=cluster_model.bk_cloud_id,
            file_target_path=cluster_info["file_target_path"],
            task_ids=task_ids,
            dest_ips=[cluster_info["rollback_ip"]],
            source_ip=download_source_ip,
        )
    )

    # 阶段3 恢复数据
    # 恢复数据完毕不自动 change master
    cluster_info["change_master"] = False
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_model.bk_cloud_id,
        cluster_type=cluster_model.cluster_type,
        cluster=copy.deepcopy(cluster_info),
        job_timeout=MYSQL_DATA_RESTORE_TIME,
        exec_ip=cluster_info["rollback_ip"],
        get_mysql_payload_func=MysqlActPayload.get_rollback_data_restore_payload.__name__,
    )
    sub_pipeline.add_act(
        act_name=_("恢复数据 {}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )

    # 阶段4 如果指定了时间，则前滚binlog todo 后续是否以指定时间为条件来前滚binlog?
    if (
        cluster_info["rollback_type"] == RollbackType.LOCAL_AND_TIME
        or cluster_info["rollback_type"] == RollbackType.REMOTE_AND_TIME
    ):
        binlog_result = backup_handler.get_binlog_for_rollback(backup_info, backup_time, rollback_time)
        if "query_binlog_error" in binlog_result.keys():
            raise TendbGetBinlogFailedException(
                message="{} binlog sql: {}".format(binlog_result["query_binlog_error"], backup_handler.query)
            )
        cluster_info.update(binlog_result)

        sub_pipeline.add_sub_pipeline(
            sub_flow=mysql_restore_download_sub_flow(
                root_id=root_id,
                uid=uid,
                bk_cloud_id=cluster_model.bk_cloud_id,
                file_target_path=cluster_info["file_target_path"],
                task_ids=binlog_result["binlog_task_ids"],
                dest_ips=[cluster_info["rollback_ip"]],
                source_ip=None,
            )
        )

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_recover_binlog_payload.__name__
        exec_act_kwargs.cluster = copy.deepcopy(cluster_info)
        sub_pipeline.add_act(
            act_name=_("前滚binlog{}".format(exec_act_kwargs.exec_ip)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

    return backup_info, sub_pipeline.build_sub_process(
        sub_name=_("tendbHa定点回档 {}:{} ".format(cluster_info["rollback_ip"], cluster_info["rollback_port"]))
    )
