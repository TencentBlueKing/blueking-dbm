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
import re
import secrets
from collections import defaultdict
from typing import Dict, List

from django.db.models import QuerySet

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import (
    SQLSERVER_CUSTOM_SYS_DB,
    SQLSERVER_CUSTOM_SYS_USER,
    SqlserverBackupJobExecMode,
    SqlserverLoginExecMode,
    SqlserverSyncMode,
)
from backend.flow.utils.mysql.db_table_filter import DbTableFilter
from backend.flow.utils.mysql.get_mysql_sys_user import generate_mysql_tmp_user


def sqlserver_match_dbs(
    dbs: List[str],
    db_patterns: List[str],
    ignore_db_patterns: List[str] = None,
):
    """
    根据库表正则去匹配库
    @param dbs: 待匹配库
    @param db_patterns: 库正则
    @param ignore_db_patterns: 忽略库正则
    """
    # 拼接匹配正则
    db_filter = DbTableFilter(
        include_db_patterns=db_patterns,
        include_table_patterns=[""],
        exclude_db_patterns=ignore_db_patterns if ignore_db_patterns else [""],
        exclude_table_patterns=[""],
    )
    db_filter.inject_system_dbs([SQLSERVER_CUSTOM_SYS_DB])
    db_filter_pattern = re.compile(db_filter.db_filter_regexp(), re.IGNORECASE)

    # 获取过滤后db
    real_dbs = [db_name for db_name in dbs if db_filter_pattern.match(db_name)]
    return real_dbs


def get_dbs_for_drs(cluster_id: int, db_list: list, ignore_db_list: list) -> list:
    """
    根据传入的db列表正则匹配和忽略db列表的正则匹配，获取真实的db名称,
    统一不处理集群的只读库和在restoring状态的库
    @param cluster_id: 对应的cluster_id
    @param db_list: 匹配db的正则列表
    @param ignore_db_list: 忽略db的正则列表
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
                "select name from [master].[sys].[databases] where "
                f"database_id > 4 and name != '{SQLSERVER_CUSTOM_SYS_DB}' and source_database_id is null "
                "and state = 0 and is_read_only = 0"
            ],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] get dbs failed: {ret[0]['error_msg']}")
    # 获取所有db名称
    all_dbs = [i["name"] for i in ret[0]["cmd_results"][0]["table_data"]]
    # TODO: 上面流程可以简化调用 self.get_cluster_database([cluster_id])[cluster_id]
    real_dbs = sqlserver_match_dbs(all_dbs, db_list, ignore_db_list)
    return real_dbs


def multi_get_dbs_for_drs(cluster_ids: List[int], db_list: list, ignore_db_list: list) -> Dict[int, List[str]]:
    """
    根据库正则批量查询集群的正式DB列表
    @param cluster_ids: 集群ID列表
    @param db_list: 匹配db的正则列表
    @param ignore_db_list: 忽略db的正则列表
    """
    cluster_id__dbs: Dict[int, List[str]] = get_cluster_database(cluster_ids)
    cluster_id__dbs = {
        cluster_id: sqlserver_match_dbs(dbs, db_list, ignore_db_list) for cluster_id, dbs in cluster_id__dbs.items()
    }
    return cluster_id__dbs


def check_sqlserver_db_exist(cluster_id: int, check_dbs: list) -> list:
    """
    根据存入的db名称，判断库名是否在集群存在，这里判断是不区分大小写
    @param cluster_id: 对应的cluster_id
    @param check_dbs: 需要验证的check_dbs 列表
    """
    cmds = []
    result = []
    if len(check_dbs) == 0:
        raise Exception("no db check exist")

    cluster = Cluster.objects.get(id=cluster_id)
    # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
    master_instance = cluster.storageinstance_set.get(
        instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
    )
    in_condition = ",".join(f"'{item}'" for item in check_dbs)
    cmds.append(f"select name from [master].[sys].[databases] where name in ({in_condition})")

    # 执行
    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [master_instance.ip_port],
            "cmds": cmds,
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] check db failed: {ret[0]['error_msg']}")
    # 判断库是否存在, 这里判断不区分大小写
    for db_name in check_dbs:
        is_exists = False
        for info in ret[0]["cmd_results"][0]["table_data"]:
            if db_name.lower() == info["name"].lower():
                is_exists = True
                result.append({"name": db_name, "is_exists": is_exists})
                break
        # 不存在
        if not is_exists:
            result.append({"name": db_name, "is_exists": is_exists})

    return result


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
        check_sql = f"""select name from  master.sys.databases
where state=0 and is_read_only=0 and database_id > 4
and name != 'Monitor' and database_id in
(select database_id from master.sys.database_mirroring
where mirroring_guid is null or mirroring_state<>4) and
name not in (select name from {SQLSERVER_CUSTOM_SYS_DB}.dbo.MIRRORING_FILTER)"""
    elif sync_mode == SqlserverSyncMode.ALWAYS_ON:
        # always_on 模式
        check_sql = f"""select name from master.sys.databases
where state=0 and is_read_only=0 and  database_id>4 and name != 'Monitor'
and database_id not in(SELECT database_id from sys.dm_hadr_database_replica_states
where is_local=0 and synchronization_state=1) and
name not in (select name from {SQLSERVER_CUSTOM_SYS_DB}.dbo.MIRRORING_FILTER)"""
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


def get_restoring_dbs(instance: StorageInstance, bk_cloud_id: int) -> List[str]:
    """
    获取实例上存在的restoring状态的数据库
    针对于dr重建的场景
    @param instance: 检查实例
    @param bk_cloud_id: 云区域ID
    """

    check_sql = f"""select a.name from master.sys.databases as a
join master.sys.database_mirroring as b on a.database_id =b.database_id
where a.state = 1 and a.database_id > 4 and a.name <> '{SQLSERVER_CUSTOM_SYS_DB}'
and (b.mirroring_state not in (2,4) or b.mirroring_state is null)"""

    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [instance.ip_port],
            "cmds": [check_sql],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{instance.ip_port}] get no-sync-dbs failed: {ret[0]['error_msg']}")
    # 获取所有db名称
    restoring_db = [i["name"] for i in ret[0]["cmd_results"][0]["table_data"]]

    return restoring_db


def check_always_on_status(cluster: Cluster, instance: StorageInstance) -> bool:
    """
    检查实例的可用组的状态是否正常
    @param cluster: 集群信息
    @param instance: 检查实例
    """
    master_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
    get_replica_id_sql = """SELECT CAST(replica_id AS nvarchar(100)) as id
FROM master.sys.dm_hadr_availability_replica_states  where is_local = 1"""
    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [instance.ip_port],
            "cmds": [get_replica_id_sql],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{instance.ip_port}] get_replica_id failed: {ret[0]['error_msg']}")

    if len(ret[0]["cmd_results"][0]["table_data"]) == 0:
        # 代表没有加入的Alwayson可用组
        return False
    replica_id = ret[0]["cmd_results"][0]["table_data"][0]["id"]

    check_sql = (
        f"SELECT connected_state FROM master.sys.dm_hadr_availability_replica_states where replica_id = '{replica_id}'"
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
        raise Exception(f"[{instance.ip_port}] check replica_states failed: {ret[0]['error_msg']}")

    if len(ret[0]["cmd_results"][0]["table_data"]) == 0:
        # 代表没有加入的Alwayson可用组
        return False
    if ret[0]["cmd_results"][0]["table_data"][0]["connected_state"] == 0:
        # 代表改同步链路是失联状态
        return False

    return True


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


def get_backup_info_in_master(cluster_id: int, job_id: str, db_name: str, backup_type: str):
    """
    查询对应数据库的本地备份记录
    @param cluster_id: 操作的集群id
    @param job_id: 这次流程的备份id
    @param db_name: db名称
    @param backup_type: 备份类型
    """
    check_sql = f"""select top (1)
b.database_name as name ,
backup_finish_date ,
a.physical_device_name as backup_file
from msdb.dbo.backupmediafamily as a
inner join msdb.dbo.backupset as b on a.media_set_id = b.media_set_id
where a.physical_device_name like '%{job_id}%' and database_name = '{db_name}' and b.type = '{backup_type}'
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


def exec_instance_app_login(cluster: Cluster, exec_type: SqlserverLoginExecMode, instance: StorageInstance) -> bool:
    """
    操作实例的用户启动/禁用/删除
    """
    exec_sqls = []

    # 获取系统账号
    sys_users = SQLSERVER_CUSTOM_SYS_USER
    sys_users_str = ",".join([f"'{i}'" for i in sys_users])

    # 查询所有的业务账号名称，这里会隐藏过滤掉job的临时账号
    get_login_name_sql = f"""select a.name as login_name
from master.sys.sql_logins a left join master.sys.syslogins b
on a.name=b.name where principal_id>4 and a.name not in({sys_users_str}) and a.name not like '#%'
and a.name not like 'J_%'
"""
    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": cluster.bk_cloud_id,
            "addresses": [instance.ip_port],
            "cmds": [get_login_name_sql],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{instance.ip_port}] get login name failed: {ret[0]['error_msg']}")

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
            "addresses": [instance.ip_port],
            "cmds": exec_sqls,
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{instance.ip_port}] exec login-{exec_type} failed: {ret[0]['error_msg']}")

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

    if len(ret[0]["cmd_results"][0]["table_data"]) == 0:
        raise Exception(f"[{master_instance.ip_port}] get_group_name is null")
    return ret[0]["cmd_results"][0]["table_data"][0]["name"]


def get_cluster_database_with_cloud(bk_cloud_id: int, clusters: List[Cluster]) -> Dict[int, List[str]]:
    """
    获取集群的业务库
    @param bk_cloud_id: 云区域
    @param clusters: 集群ID列表(请保证这一批集群处于相同云区域)
    """
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
            "bk_cloud_id": bk_cloud_id,
            "addresses": [inst.ip_port for inst in master_instances],
            "cmds": [
                "select name from [master].[sys].[databases] where "
                f"database_id > 4 and name != '{SQLSERVER_CUSTOM_SYS_DB}' and source_database_id is null"
            ],
            "force": False,
        }
    )

    # 按照集群ID，分别获取各自的业务主库信息
    cluster_id__database: Dict[int, List[str]] = defaultdict(list)
    for ret in rets:
        if ret["error_msg"]:
            raise Exception(f"[{ret['address']}] check db failed: {ret['error_msg']}")
        all_dbs = [i["name"] for i in ret["cmd_results"][0]["table_data"]]
        cluster_id__database[master_ip_port__cluster[ret["address"]].id] = all_dbs

    return cluster_id__database


def get_cluster_database(cluster_ids: List[int]) -> Dict[int, List[str]]:
    """
    获取集群的业务库
    @param cluster_ids: 集群ID列表(请保证这一批集群处于相同云区域)
    """
    clusters = Cluster.objects.prefetch_related("storageinstance_set").filter(id__in=cluster_ids)

    # 按照云区域ID进行集群聚合
    cloud__clusters_map: Dict[int, List[Cluster]] = defaultdict(list)
    for cluster in clusters:
        cloud__clusters_map[cluster.bk_cloud_id].append(cluster)

    # 根据云区域分批查询集群的DB列表
    cluster_id__database: Dict[int, List[str]] = defaultdict(list)
    for bk_cloud_id, clusters in cloud__clusters_map.items():
        cluster_dbs_info = get_cluster_database_with_cloud(bk_cloud_id, clusters)
        cluster_id__database.update(cluster_dbs_info)
    return cluster_id__database


def get_instance_time_zone(instance: StorageInstance) -> str:
    """
    获取实例配置的时区信息
    """
    ret = DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": instance.machine.bk_cloud_id,
            "addresses": [instance.ip_port],
            "cmds": ["select DATENAME(TzOffset, SYSDATETIMEOFFSET()) as time_zone"],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{instance.ip_port}] get_time_zone failed: {ret[0]['error_msg']}")

    return ret[0]["cmd_results"][0]["table_data"][0]["time_zone"]


def create_sqlserver_login_sid() -> str:
    """
    生成login的sid，sid格式："0x" + 32位16进制字符串
    """
    num_bytes = 16  # 每个字节对应两个十六进制字符
    random_bytes = secrets.token_bytes(num_bytes)
    hex_string = random_bytes.hex()
    return "0x" + hex_string


def create_sqlserver_random_job_user(
    job_root_id: str, sid: str, pwd: str, storages: QuerySet, other_instances: list, bk_cloud_id: int
) -> list:
    """
    创建随机账号的基本函数
    @param job_root_id: 任务root_id
    @param sid: 用户的sid
    @param pwd: 用户密码
    @param storages: 添加随机账号的实例
    @param other_instances: 作为额外的实例传入，目标是满足集群添加实例且没有暂时没有元数据的场景， 每个元素是ip:port字符串
    @param bk_cloud_id: 云区域id
    """
    user = generate_mysql_tmp_user(job_root_id)
    create_cmds = [
        f"use master IF SUSER_SID('{user}') IS NULL "
        f"CREATE LOGIN {user} WITH PASSWORD=N'{pwd}', DEFAULT_DATABASE=[MASTER],SID={sid},CHECK_POLICY=OFF;"
        f"EXEC sp_addsrvrolemember @loginame = '{user}', @rolename = N'sysadmin';",
    ]
    return DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [s.ip_port for s in storages] + other_instances,
            "cmds": create_cmds,
            "force": False,
        }
    )


def drop_sqlserver_random_job_user(
    job_root_id: str, bk_cloud_id: int, storages: QuerySet, other_instances: list
) -> list:
    """
    删除随机账号的基本函数
    @param job_root_id: 任务root_id
    @param storages: 添加随机账号的实例
    @param other_instances: 作为额外的实例传入，目标是满足集群添加实例且没有暂时没有元数据的场景， 每个元素是ip:port字符串
    @param bk_cloud_id: 云区域id
    """
    user = generate_mysql_tmp_user(job_root_id)
    return DRSApi.sqlserver_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [s.ip_port for s in storages] + other_instances,
            "cmds": [
                f"USE MASTER IF SUSER_SID('{user}') IS NOT NULL " f"drop login [{user}] ;",
            ],
            "force": False,
        }
    )


def get_sync_filter_dbs(cluster_id: int):
    """
    获取不做同步的db列表
    @param 集群id
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
            "cmds": [f"select name from [{SQLSERVER_CUSTOM_SYS_DB}].[DBO].[MIRRORING_FILTER];"],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] get dbs failed: {ret[0]['error_msg']}")
    # 获取所有db名称
    return [i["name"] for i in ret[0]["cmd_results"][0]["table_data"]]


def insert_sqlserver_config(
    cluster: Cluster,
    storages: QuerySet,
    backup_config: dict,
    charset: str,
    alarm_config: dict,
    is_get_old_backup_config: bool = False,
):
    """
    给sqlserver实例插入配置信息
    @param cluster: 集群
    @param storages: 需要配置的实例列表
    @param backup_config: 实例的备份配置
    @param charset: 字符集
    @param alarm_config 实例的告警配置
    @param is_get_old_backup_config: 是否要获取旧的备份配置信息，内部导入标准化使用
    """
    old_backup_config = {}
    master = cluster.storageinstance_set.get(instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER])
    if cluster.cluster_type == ClusterType.SqlserverHA:
        sync_mode = SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
    else:
        sync_mode = ""
    drop_sql = "use Monitor truncate table [Monitor].[dbo].[APP_SETTING]"
    for storage in storages:
        if is_get_old_backup_config:
            # 按照需求获取旧的备份配置
            ret = DRSApi.sqlserver_rpc(
                {
                    "bk_cloud_id": cluster.bk_cloud_id,
                    "addresses": [storage.ip_port],
                    "cmds": [f"select * from [{SQLSERVER_CUSTOM_SYS_DB}].[dbo].[BACKUP_SETTING_OLD]"],
                    "force": False,
                }
            )
            if ret[0]["error_msg"]:
                raise Exception(f"[{storage.ip_port}] get old backup config failed: {ret[0]['error_msg']}")

            if len(ret[0]["cmd_results"][0]["table_data"]) != 0:
                old_backup_config = copy.deepcopy(ret[0]["cmd_results"][0]["table_data"][0])

        # 判断storage角色和备份位置，传入正确的DATA_SCHEMA_GRANT值
        if (
            storage.instance_role in [InstanceRole.BACKEND_MASTER, InstanceRole.ORPHAN]
            and backup_config["backup_space"] == "master"
        ):
            data_schema_grant = "all"
        elif (
            storage.instance_role == InstanceRole.BACKEND_SLAVE
            and storage.is_stand_by
            and backup_config["backup_space"] == "standby"
        ):
            data_schema_grant = "all"
        else:
            data_schema_grant = "grant"

        update_data_path_sql = (
            f"use Monitor update [{SQLSERVER_CUSTOM_SYS_DB}].[dbo].[APP_SETTING] set "
            f"DATA_PATH = REPLACE(physical_name,'master.mdf','') "
            f"from master.sys.database_files WHERE type=0"
        )
        update_log_path_sql = (
            f"use Monitor update [{SQLSERVER_CUSTOM_SYS_DB}].[dbo].[APP_SETTING] set "
            f"LOG_PATH = REPLACE(physical_name,'mastlog.ldf','') "
            f"from master.sys.database_files WHERE type=1"
        )

        insert_app_setting_sql = f"""INSERT INTO [{SQLSERVER_CUSTOM_SYS_DB}].[dbo].[APP_SETTING](
[APP],
[FULL_BACKUP_PATH],
[LOG_BACKUP_PATH],
[KEEP_FULL_BACKUP_DAYS],
[KEEP_LOG_BACKUP_DAYS],
[FULL_BACKUP_MIN_SIZE_MB],
[LOG_BACKUP_MIN_SIZE_MB],
[UPLOAD],
[MD5],
[CLUSTER_ID],
[CLUSTER_DOMAIN],
[IP],
[PORT],
[ROLE],
[MASTER_IP],
[MASTER_PORT],
[SYNCHRONOUS_MODE],
[BK_BIZ_ID],
[BK_CLOUD_ID],
[VERSION],
[BACKUP_TYPE],
[DATA_SCHEMA_GRANT],
[TIME_ZONE],
[CHARSET],
[BACKUP_CLIENT_PATH],
[BACKUP_STORAGE_TYPE],
[FULL_BACKUP_REPORT_PATH],
[LOG_BACKUP_REPORT_PATH],
[FULL_BACKUP_FILETAG],
[LOG_BACKUP_FILETAG],
[SHRINK_SIZE],
[RESTORE_PATH],
[LOG_SEND_QUEUE],
[TRACEON],
[SLOW_DURATION],
[SLOW_SAVEDAY],
[UPDATESTATS],
[COMMIT_MODEL],
[DATA_PATH],
[LOG_PATH])
values(
'{str(cluster.bk_biz_id)}',
'{old_backup_config.get('FULL_BACKUP_PATH', backup_config['full_backup_path'])}',
'{old_backup_config.get('LOG_BACKUP_PATH', backup_config['log_backup_path'])}',
{int(old_backup_config.get('KEEP_FULL_BACKUP_DAYS', backup_config['keep_full_backup_days']))},
{int(old_backup_config.get('KEEP_LOG_BACKUP_DAYS', backup_config['keep_log_backup_days']))},
{int(backup_config['full_backup_min_size_mb'])},
{int(backup_config['log_backup_min_size_mb'])},
1,
0,
{cluster.id},
'{cluster.immute_domain}',
'{storage.machine.ip}',
{storage.port},
'{storage.instance_inner_role}',
'{master.machine.ip}',
{master.port},
'{sync_mode}',
{cluster.bk_biz_id},
{cluster.bk_cloud_id},
'{cluster.major_version}',
'{backup_config['backup_type']}',
'{data_schema_grant}',
'{cluster.time_zone}',
'{charset}',
'{backup_config['backup_client_path']}',
'{backup_config['backup_storage_type']}',
'{backup_config['full_backup_report_path']}',
'{backup_config['log_backup_report_path']}',
'{backup_config['full_backup_file_tag']}',
'{backup_config['log_backup_file_tag']}',
{int(alarm_config['shrink_size'])},
'',
{int(alarm_config['log_send_queue'])},
{int(alarm_config['traceon'])},
{int(alarm_config['slow_duration'])},
{int(alarm_config['slow_saveday'])},
{int(alarm_config['updatestats'])},
'{alarm_config['commit_model']}',
'',
''
)
"""
        ret = DRSApi.sqlserver_rpc(
            {
                "bk_cloud_id": cluster.bk_cloud_id,
                "addresses": [storage.ip_port],
                "cmds": [drop_sql, insert_app_setting_sql, update_data_path_sql, update_log_path_sql],
                "force": False,
            }
        )

        if ret[0]["error_msg"]:
            raise Exception(f"[{storage.ip_port}] insert app_setting failed: {ret[0]['error_msg']}")

    return True
