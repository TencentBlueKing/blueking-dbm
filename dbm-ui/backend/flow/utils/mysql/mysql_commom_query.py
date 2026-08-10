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
import logging.config
from typing import List

from django.utils.translation import gettext as _

from backend.components import DBPrivManagerApi
from backend.components.db_remote_service.client import DRSApi
from backend.components.sql_import.client import SQLSimulationApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import TDBCTL_USER
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse

logger = logging.getLogger("flow")


def query_mysql_variables(host: str, port: int, bk_cloud_id: int):
    """
    查询远程节点变量
    """
    body = {
        "addresses": ["{}{}{}".format(host, IP_PORT_DIVIDER, port)],
        "cmds": ["show global variables;"],
        "force": False,
        "bk_cloud_id": bk_cloud_id,
    }
    resp = DRSApi.rpc(body)
    logger.info(f"query vaiables {resp}")
    if not resp and len(resp) < 1:
        raise Exception(_("DRS{}:{}查询变量失败,返回为空值").format(host, port))

    if not resp[0]["cmd_results"]:
        raise Exception(_("DRS查询字符集失败：{}").format(resp[0]["error_msg"]))

    var_list = resp[0]["cmd_results"][0]["table_data"]

    var_map = {}
    for var_item in var_list:
        var_name = var_item["Variable_name"]
        val = var_item["Value"]
        var_map[var_name] = val
    return var_map


# SQL 模拟执行：引擎无关公共参数（可同步值；default_tmp_storage_engine 不参与引擎门控）
# 只允许 mysqld 启动参数（可写入 my.cnf）；character_set_client / character_set_connection /
# collation_connection / foreign_key_checks / sql_safe_updates 等仅会话级，写入会导致
# "unknown variable" 启动失败，禁止加入。
# 未标注版本的为长期存在项；实例无该变量时由 _pick_existing_vars 跳过，不报错
COMMON_SEMANTIC_VARS = [
    "sql_mode",
    "lower_case_table_names",
    "character_set_server",
    "collation_server",
    "default_storage_engine",
    "default_tmp_storage_engine",  # MySQL 5.6.3+
    "explicit_defaults_for_timestamp",  # MySQL 5.6.6+；8.0 默认 ON
    "log_bin_trust_function_creators",
    "default_time_zone",
    "loose_log_bin_compress",  # TMySQL / TenDB 扩展（loose_ 前缀）
    "log_bin_compress",  # TMySQL / TenDB 扩展
    "slave_exec_mode",
    "max_allowed_packet",
    "wait_timeout",
    "interactive_timeout",
    "group_concat_max_len",
]

# MySQL 8.0 补丁级启动参数：源实例 SHOW 可能有，但仿真侧 GetImgFromMySQLVersion
# 常按粗粒度 "8.0" 选 Tendb80Img，镜像补丁可能低于源端。必须 loose_ 输出，
# 否则旧镜像会以 "unknown variable" Abort（与会话级变量 CrashLoop 同类）。
MYSQL80_PATCH_SEMANTIC_VARS = [
    "sql_require_primary_key",  # MySQL 8.0.13+
    "sql_generate_invisible_primary_key",  # MySQL 8.0.30+
]

INNODB_SEMANTIC_VARS = [
    "innodb_file_format",  # MySQL 5.5+；MySQL 8.0 已移除
    "innodb_file_per_table",
    "innodb_large_prefix",  # MySQL 5.5+；MySQL 8.0 已移除
    "innodb_default_row_format",  # MySQL 5.7.9+
    "innodb_strict_mode",
    "innodb_autoinc_lock_mode",
    "innodb_lock_wait_timeout",
    "innodb_online_alter_log_max_size",  # MySQL 5.6.27+ / 5.7+
]

TOKUDB_SEMANTIC_VARS = [
    "tokudb_lock_timeout",
    "tokudb_commit_sync",
    "tokudb_row_format",
]

ROCKSDB_SEMANTIC_VARS = [
    # 下列均为 TMySQL / TenDB RocksDB 引擎变量（非上游 MySQL 官方）
    "rocksdb_large_prefix",
    "rocksdb_strict_collation_check",
    "rocksdb_strict_collation_exceptions",
    "rocksdb_bulk_load",
    "rocksdb_bulk_load_allow_unsorted",
    "rocksdb_default_cf_options",
    "rocksdb_lock_wait_timeout",
]

# RocksDB 模拟启动必需：plugin-load 不是 SHOW VARIABLES 项，需在引擎门控分支硬写入
ROCKSDB_PLUGIN_LOAD = "rocksdb=ha_rocksdb.so;rocksdb_cfstats=ha_rocksdb.so;rocksdb_dbstats=ha_rocksdb.so;rocksdb_perf_context=ha_rocksdb.so;rocksdb_perf_context_global=ha_rocksdb.so;rocksdb_cf_options=ha_rocksdb.so;rocksdb_compaction_stats=ha_rocksdb.so;rocksdb_global_info=ha_rocksdb.so;rocksdb_ddl=ha_rocksdb.so;rocksdb_index_file_map=ha_rocksdb.so;rocksdb_locks=ha_rocksdb.so;rocksdb_trx=ha_rocksdb.so"  # noqa: E501

# Spider 专用白名单（不含 innodb_/rocksdb_/tokudb_ 等存储引擎参数；不含连接池类如 spider_max_connections）
# 版本标注来自 TenDB Cluster Manual《TSpider参数说明》；未标注表示手册未写明引入版本
SPIDER_SEMANTIC_VARS: List[str] = [
    # 超时
    "spider_net_read_timeout",
    "spider_net_write_timeout",
    # 事务 / XA
    "spider_support_xa",
    "spider_internal_xa",
    "spider_trans_rollback",
    "spider_with_begin_commit",
    "spider_force_commit",
    "spider_ignore_autocommit",
    "spider_sync_autocommit",
    "spider_sync_time_zone",
    # DDL / 表结构语义（模拟侧会拉起完整 TenDBCluster，含真实 Tdbctl）
    "spider_ignore_create_like",
    "ddl_execute_by_ctl",
    "spider_not_show_partition",  # TSpider 3.5.1+
    # 执行路径 / DML 语义
    "spider_bgs_mode",
    "spider_bgs_dml",
    "spider_index_hint_pushdown",
    "spider_direct_dup_insert",
    "spider_direct_insert_ignore",  # TSpider 3.5.3+
    "spider_string_key_equal_to_like",  # TSpider 3.7.5+
    "spider_query_one_shard",
    "spider_transaction_one_shard",
    "spider_get_sts_or_crd",
]

# Tdbctl 专用语义白名单（叠加在存储层抽取结果之上）
# 明确不抽 tc_admin：模拟集群 my.cnf 已强制 tc-admin=1，避免与生产值重复/冲突
# 不抽 wrapper 前缀、转发规则、巡检/超时类（模拟侧自建拓扑）
TDBCTL_SEMANTIC_VARS: List[str] = [
    "tc_ignore_partitioning_for_create_table",
    "tc_force_execute",
    "tc_enable_autoinc_check",
    "tc_partition_admin",
    "tc_dry_run",
    "tc_enable_internal_dump",
    "tc_enable_internal_grant",
    "tc_restrict_query_from_spider",
]

_INNODB_ENGINE_ALIASES = {"innodb"}


def _pick_existing_vars(mysql_var_map: dict, var_names: List[str], loose: bool = False) -> dict:
    """
    仅拷贝变量映射中已存在的 key。

    loose=True 时输出 loose_ 前缀：仿真镜像可能不认该启动项时，避免 "unknown variable" 退出。
    用于 Spider/Tdbctl 扩展项、以及 MySQL 8.0 补丁级公共项；RocksDB/TokuDB 引擎项故意裸名硬生效。
    """
    prefix = "loose_" if loose else ""
    return {f"{prefix}{name}": mysql_var_map[name] for name in var_names if name in mysql_var_map}


def _normalize_storage_engine(mysql_var_map: dict) -> str:
    """读取 default_storage_engine 并规范化；不看 default_tmp_storage_engine。"""
    return (mysql_var_map.get("default_storage_engine") or "").strip().lower()


def extract_storage_semantic_configs(mysql_var_map: dict) -> dict:
    """
    从存储层（MySQL Backend / Remote）变量中提取模拟执行启动配置。

    先抽公共参数，再仅按 default_storage_engine 追加引擎参数：
    InnoDB / RocksDB / TokuDB；其他引擎只保留公共参数。
    TDBCTL 请使用 extract_tdbctl_semantic_configs（存储策略 + tc_* 语义白名单）。
    """
    configs = _pick_existing_vars(mysql_var_map, COMMON_SEMANTIC_VARS)
    configs.update(_pick_existing_vars(mysql_var_map, MYSQL80_PATCH_SEMANTIC_VARS, loose=True))
    engine = _normalize_storage_engine(mysql_var_map)
    if engine in _INNODB_ENGINE_ALIASES:
        configs.update(_pick_existing_vars(mysql_var_map, INNODB_SEMANTIC_VARS))
    elif engine == "rocksdb":
        # 裸名写入：有引擎时必须硬生效；镜像缺引擎/缺变量时 CrashLoop 可接受
        configs.update(_pick_existing_vars(mysql_var_map, ROCKSDB_SEMANTIC_VARS))
        configs["plugin-load"] = ROCKSDB_PLUGIN_LOAD
    elif engine == "tokudb":
        configs.update(_pick_existing_vars(mysql_var_map, TOKUDB_SEMANTIC_VARS))
    return configs


def extract_tdbctl_semantic_configs(tdbctl_var_map: dict) -> dict:
    """
    从 Tdbctl 实例变量中提取模拟执行启动配置。

    先按存储层策略抽取（公共参数 + 引擎门控），再叠加 TDBCTL_SEMANTIC_VARS。
    不抽取 tc_admin（模拟侧已强制 tc-admin=1）。
    """
    configs = extract_storage_semantic_configs(tdbctl_var_map)
    configs.update(_pick_existing_vars(tdbctl_var_map, TDBCTL_SEMANTIC_VARS, loose=True))
    return configs


def extract_spider_semantic_configs(spider_var_map: dict) -> dict:
    """
    从 Spider 实例变量中提取模拟执行启动配置。

    先抽与存储层相同的公共默认参数（COMMON_SEMANTIC_VARS），再叠加 Spider 专用白名单。
    不做引擎门控，也不抽取 innodb_/rocksdb_/tokudb_ 等存储引擎参数。
    """
    configs = _pick_existing_vars(spider_var_map, COMMON_SEMANTIC_VARS)
    configs.update(_pick_existing_vars(spider_var_map, MYSQL80_PATCH_SEMANTIC_VARS, loose=True))
    configs.update(_pick_existing_vars(spider_var_map, SPIDER_SEMANTIC_VARS, loose=True))
    return configs


def get_mysql_start_configs(mysql_var_map: dict) -> dict:
    """
    从 MySQL 变量映射中提取模拟执行需要的启动配置。

    兼容旧调用点，委托 extract_storage_semantic_configs。

    @param mysql_var_map: MySQL 变量映射，由 query_mysql_variables 返回
    @return: 模拟执行需要的 MySQL 启动配置字典
    """
    return extract_storage_semantic_configs(mysql_var_map)


def show_user_host_for_host(host: str, instance: StorageInstance):
    """
    根据host查询账号信息
    """
    res = DRSApi.rpc(
        {
            "addresses": [instance.ip_port],
            "cmds": [f"select concat('`',user,'`@`',host,'`') as user_host from mysql.user where host = '{host}'"],
            "force": False,
            "bk_cloud_id": instance.machine.bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        logger.error(f"[{instance.ip_port}] get user info [{host}] failed: [{res['error_msg']}]")
        return False, []

    return True, [list(item.values())[0] for item in res[0]["cmd_results"][0]["table_data"]]


def show_privilege_for_user(db_version: str, host: str, instance: StorageInstance):
    """
    根据user_host 在实例查询授权情况，并拼接成对应的版本的授权语句
    """
    result, user_hosts = show_user_host_for_host(host=host, instance=instance)
    if not result:
        # 这里是异常退出
        return result, []
    if not user_hosts:
        # 这里查询为空则正常退出
        return True, []

    grants_sql = []
    if mysql_version_parse(db_version) >= mysql_version_parse("5.7"):
        res = DRSApi.rpc(
            {
                "addresses": [instance.ip_port],
                "cmds": [f"show create user {u} " for u in user_hosts],
                "force": False,
                "bk_cloud_id": instance.machine.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            logger.error(f"[{instance.ip_port}] show create user failed: [{res[0]['error_msg']}]")
            return False, []
        grants_sql.extend([list(i.values())[0] for item in res[0]["cmd_results"] for i in item["table_data"]])

    res = DRSApi.rpc(
        {
            "addresses": [instance.ip_port],
            "cmds": [f"show grants for {u} " for u in user_hosts],
            "force": False,
            "bk_cloud_id": instance.machine.bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        logger.error(f"[{instance.ip_port}] show grants failed: [{res[0]['error_msg']}]")
        return False, []

    grants_sql.extend([list(i.values())[0] for item in res[0]["cmd_results"] for i in item["table_data"]])
    return True, grants_sql


def check_backend_in_proxy(proxys: List[str], bk_cloud_id: int):
    """
    检测传入的proxy是否1.1.1.1:3306
    """
    res = DRSApi.proxyrpc(
        {
            "addresses": proxys,
            "cmds": ["SELECT * FROM backends;"],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )
    for i in res:
        if i["error_msg"]:
            logger.error(f"get proxy backends failed: [{i['error_msg']}]")
            return False

    is_pass = True
    for i in res[0]["cmd_results"]:
        backend_address = str(i["table_data"][0]["address"]).strip()
        if backend_address != "1.1.1.1:3306":
            logger.error(f"[{res[0]['address']}] the backends is not empty [{backend_address}] ")
            is_pass = False

    return is_pass


def parse_db_from_sqlfile(path: str, files: List[str]):
    """
    从变更sql文件中解析出变更相关的DB
    respone data is :
        {
            "data": {
                "create_dbs": [
                    "xxx"
                ],
                "dbs": null,
                "dump_all": false,
                "timestamp": 1733734571
            },
            "request_id": "9faaf67f-1b09-4575-8974-472677b2db5b",
            "message": "",
            "code": 0
        }
    create_dbs:  create database
    dbs:  need dump database
    dump_all:  是否需要dump所有数据库
    """
    payload = {}
    payload["path"] = path
    payload["files"] = files
    try:
        resp = SQLSimulationApi.query_relation_dbs_from_sqlfile(payload, raw=True)
        if resp["code"] != 0:
            logger.error(_("从SQL文件解析变更相关DB失败: {}").format(resp))
            return None
        return resp["data"]
    except Exception as e:
        logger.error(f"parse db from sqlfile failed: [{e}]")
        return None


def merge_resp_to_cluster(resp: dict):
    """
    合并返回的数据到集群
    """
    dump_schema_payload = {}
    logger.info(f"resp: {resp}")
    dump_schema_payload["dump_all"] = resp.get("dump_all")
    dump_schema_payload["parse_need_dump_dbs"] = resp.get("dbs")
    dump_schema_payload["parse_create_dbs"] = resp.get("create_dbs")
    dump_schema_payload["just_dump_special_tbls"] = resp.get("just_dump_special_tbls")
    dump_schema_payload["special_tbls"] = resp.get("special_tbls")
    return dump_schema_payload


def create_tdbctl_user_for_remote(cluster: Cluster, ctl_primary: str, new_ip: str, new_port: int, tdbctl_pass: str):
    """
    给新的remote实例对中控primary授权
    操作步骤：
    1: 主动回收primary在remote机器的账号权限,不返回异常，可以报warning信息
    2: 通过add_priv_without_account_rule添加spider账号
    参数信息:
    @param cluster: 集群元数据
    @param ctl_primary: 中控primary实例
    @param new_ip: 新加remote的ip信息
    @param new_port: 新加remote的port信息
    @param tdbctl_pass: 授权pass
    """
    # 删除已经存在的spider账号
    rpc_params = {
        "addresses": [f"{new_ip}{IP_PORT_DIVIDER}{new_port}"],
        "cmds": [
            f"drop user '{TDBCTL_USER}'@'{ctl_primary.split(IP_PORT_DIVIDER)[0]}'",
        ],
        "force": False,
        "bk_cloud_id": cluster.bk_cloud_id,
    }
    # drs服务远程请求
    res = DRSApi.rpc(rpc_params)
    if res[0]["error_msg"]:
        logger.warning(f"drop old tdbctl user in Instance[{new_ip}:{new_port}] failed: {res[0]['error_msg']}")

    # 添加临时账号
    DBPrivManagerApi.add_priv_without_account_rule(
        params={
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_biz_id": cluster.bk_biz_id,
            "operator": "",
            "user": TDBCTL_USER,
            "psw": tdbctl_pass,
            "dbname": "%",
            "dml_ddl_priv": "",
            "global_priv": "all privileges",
            "address": f"{new_ip}{IP_PORT_DIVIDER}{new_port}",
            "hosts": [ctl_primary.split(IP_PORT_DIVIDER)[0]],
        }
    )
    logger.info(f"add tdbctl user in instance [f'{new_ip}{IP_PORT_DIVIDER}{new_port}'] success")
    return True


def pre_check_proxy_host_in_definer(host: str, backend: StorageInstance):
    """
    根据传入的host，在backend实例中获取到与host相关的definer配置信息
    检查命令目前支持到的版本有：
    MySQL-8.0-Community
    MySQL-5.7
    MySQL-5.6
    MySQL-5.5
    MySQL-8.0
    TXSQL-8.0

    @param host: 待检测host
    @param backend: 查询的backend实例
    """
    check_routines_definer = (
        f"select ROUTINE_SCHEMA, ROUTINE_NAME, DEFINER from information_schema.ROUTINES  "
        f"where DEFINER like '%@{host}'"
    )
    check_views_definer = (
        f"select TABLE_SCHEMA, TABLE_NAME ,DEFINER from information_schema.VIEWS " f"where DEFINER like '%@{host}'"
    )
    check_triggers_definer = (
        f"select TRIGGER_SCHEMA, TRIGGER_NAME, DEFINER from information_schema.TRIGGERS "
        f"where DEFINER like '%@{host}'"
    )
    check_events_definer = (
        f"select EVENT_SCHEMA, EVENT_NAME, DEFINER from information_schema.EVENTS " f"where DEFINER like '%@{host}'"
    )

    res = DRSApi.rpc(
        {
            "addresses": [backend.ip_port],
            "cmds": [check_routines_definer, check_views_definer, check_triggers_definer, check_events_definer],
            "force": False,
            "bk_cloud_id": backend.machine.bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        # 如果执行命令异常报错
        raise Exception(res[0]["error_msg"])

    # 遍历每个SQL返回的结果，如果返回都是空，则返回正常
    return [i for r in res[0]["cmd_results"] for i in r["table_data"]]
