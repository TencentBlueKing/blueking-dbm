"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import re
from collections import defaultdict
from typing import Dict, List

from backend.components import DRSApi
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import SqlserverBackupJobExecMode, SqlserverLoginExecMode, SqlserverSyncMode
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.utils.mysql.db_table_filter import DbTableFilter


def get_dbs_for_drs(cluster_id: int, db_list: list, ignore_db_list: list) -> list:
    """
    根据传入的db列表正则匹配和忽略db列表的正则匹配，获取真实的db名称
    @param cluster_id: 对应的cluster_id
    @param db_list: 匹配db的正则列表
    @param ignore_db_list: 忽略db的正则列表
    """
    real_dbs = []
    cluster = Cluster.objects.get(id=cluster_id)
    # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
    master_instance = cluster.storageinstance_set.get(
        instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
    )
    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": [
                "select name from [master].[sys].[databases] where "
                "database_id > 4 and name != 'Monitor' and source_database_id is null"
            ],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] get dbs failed: {ret[0]['error_msg']}")
    # 获取所有db名称
    all_dbs = [i["name"] for i in ret[0]["cmd_results"][0]["table_data"]]
    # TODO: 上面流程可以简化调用 self.get_cluster_database([cluster_id])[cluster_id]

    # 拼接匹配正则
    db_filter = DbTableFilter(
        include_db_patterns=db_list,
        include_table_patterns=[""],
        exclude_db_patterns=ignore_db_list,
        exclude_table_patterns=[""],
    )
    db_filter.inject_system_dbs(["Monitor"])
    db_filter_pattern = re.compile(db_filter.db_filter_regexp())

    # 获取过滤后db
    for db_name in all_dbs:
        if db_filter_pattern.match(db_name):
            real_dbs.append(db_name)

    return real_dbs


def check_sqlserver_db_exist(cluster_id: int, check_db: str) -> bool:
    """
    根据存入的db名称，判断库名是否在集群存在
    @param cluster_id: 对应的cluster_id
    @param check_db: 需要验证的check_db
    """
    cluster = Cluster.objects.get(id=cluster_id)
    # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
    master_instance = cluster.storageinstance_set.get(
        instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
    )
    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": [f"select count(0) as cnt from [master].[sys].[databases] where name = '{check_db}'"],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] check db failed: {ret[0]['error_msg']}")
    if ret[0]["cmd_results"][0]["table_data"][0]["cnt"] > 0:
        # 代表db存在
        return True
    else:
        # 代表db不存在
        return False


def get_no_sync_dbs(cluster_id: int) -> list:
    """
    获取没有同步的db列表
    @param cluster_id 集群id
    """

    cluster = Cluster.objects.get(id=cluster_id)
    # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
    master_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
    sync_mode = SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
    if sync_mode == SqlserverSyncMode.MIRRORING:
        # mirroring 模式
        check_sql = """select name from  master.sys.databases
where state=0 and is_read_only=0 and database_id > 4
and name != 'Monitor' and database_id in
(select database_id from master.sys.database_mirroring
where mirroring_guid is null or mirroring_state<>4) and
name not in (select name from Monitor.dbo.MIRRORING_FILTER)"""
    elif sync_mode == SqlserverSyncMode.ALWAYS_ON:
        # always_on 模式
        check_sql = """select name from master.sys.databases
where state=0 and is_read_only=0 and  database_id>4 and name != 'Monitor'
and database_id not in(SELECT database_id from sys.dm_hadr_database_replica_states
where is_local=0 and synchronization_state=1) and
name not in (select name from Monitor.dbo.MIRRORING_FILTER)"""
    else:
        raise Exception(f"sync-mode [{sync_mode}] not support")

    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": [check_sql],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] get no-sync-dbs failed: {ret[0]['error_msg']}")
    # 获取所有db名称
    no_sync_db = [i["name"] for i in ret[0]["cmd_results"][0]["table_data"]]

    return no_sync_db


def exec_instance_backup_jobs(cluster_id, backup_jobs_type: SqlserverBackupJobExecMode) -> bool:
    """
    操作实例的例行备份作业
    """
    cluster = Cluster.objects.get(id=cluster_id)
    # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
    master_instance = cluster.storageinstance_set.get(
        instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
    )

    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": [
                f"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_FULL',@enabled={backup_jobs_type}",
                f"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_LOG',@enabled={backup_jobs_type}",
            ],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] exec backup-jobs failed: {ret[0]['error_msg']}")

    return True


def get_backup_info_in_master(cluster_id: int, backup_id: str, db_name: str, backup_type: str):
    """
    查询对应数据库的本地备份记录
    @param cluster_id: 操作的集群id
    @param backup_id: 这次流程的备份id
    @param db_name: db名称
    @param backup_type: 备份类型
    """
    check_sql = f"""select top (1)
b.database_name as name ,
backup_finish_date ,
a.physical_device_name as backup_file
from msdb.dbo.backupmediafamily as a
inner join msdb.dbo.backupset as b on a.media_set_id = b.media_set_id
where a.physical_device_name like '%{backup_id}%' and database_name = '{db_name}' and b.type = '{backup_type}'
order by backup_finish_date desc"""

    cluster = Cluster.objects.get(id=cluster_id)
    master_instance = cluster.storageinstance_set.get(
        instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
    )

    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": [check_sql],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] get-backup_db failed: {ret[0]['error_msg']}")

    return ret[0]["cmd_results"][0]["table_data"]


def exec_instance_app_login(cluster_id, exec_type: SqlserverLoginExecMode) -> bool:
    """
    操作实例的用户启动/禁用
    """
    exec_sqls = []
    cluster = Cluster.objects.get(id=cluster_id)
    # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
    master_instance = cluster.storageinstance_set.get(
        instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
    )

    # 查询所有的业务账号名称
    get_login_name_sql = """select a.name as login_name
from master.sys.sql_logins a left join sys.syslogins b
on a.name=b.name where principal_id>4 and a.name not in('monitor') and a.name not like '#%'
"""

    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": [get_login_name_sql],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] get login name failed: {ret[0]['error_msg']}")

    if exec_type == "drop":
        for info in ret[0]["cmd_results"][0]["table_data"]:
            exec_sqls.append(f"DROP LOGIN {info['login_name']}")
    else:
        for info in ret[0]["cmd_results"][0]["table_data"]:
            exec_sqls.append(f"ALTER LOGIN {info['login_name']} {exec_type}")

    # 执行
    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": exec_sqls,
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] exec login-{exec_type} failed: {ret[0]['error_msg']}")

    return True

def get_group_name(master_instance: StorageInstance, bk_cloud_id: int):
    """
    获取集群group_name名称
    @param master_instance: master实例
    @param bk_cloud_id: 云区域id
    """
    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": ["select name FROM master.sys.availability_groups;"],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] get_group_name failed: {ret[0]['error_msg']}")

    if len(ret[0]["cmd_results"][0]["table_data"]):
        raise Exception(f"[{master_instance.ip_port}] get_group_name is null")
    return ret[0]["cmd_results"][0]["table_data"][0]["name"]


def get_cluster_database(cluster_ids: List[int]) -> Dict[int, List[str]]:
    """
    获取集群的业务库
    @param cluster_ids: 集群ID列表
    """
    clusters = Cluster.objects.prefetch_related("storageinstance_set").filter(id__in=cluster_ids)

    # 获取每个集群的主节点信息
    master_instances: List[StorageInstance] = []
    master_ip_port__cluster: Dict[str, Cluster] = {}
    for cluster in clusters:
        master_instance = cluster.storageinstance_set.get(
            instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
        )
        master_instances.append(master_instance)
        master_ip_port__cluster[master_instance.ip_port] = cluster

    # 通过DRS获取每个集群的业务主库信息
    rets = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": clusters.first().bk_cloud_id,
            "addresses": [inst.ip_port for inst in master_instances],
            "cmds": ["select name from [master].[sys].[databases] where database_id > 4 and name != 'Monitor'"],
            "force": False,
        }
    )

    # 按照集群ID，分别获取各自的业务主库信息
    cluster_id__database: Dict[int, List[str]] = defaultdict(list)
    for ret in rets:
        if ret["error_msg"]:
            raise Exception(f"[{ret['address']}] check db failed: {ret[0]['error_msg']}")

        all_dbs = [i["name"] for i in ret["cmd_results"][0]["table_data"]]
        cluster_id__database[master_ip_port__cluster[ret["address"]].id] = all_dbs

    return cluster_id__database
