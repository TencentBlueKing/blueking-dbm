"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging
from typing import Any

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.flow.consts import ConfigTypeEnum

"""
定义一些mysql场景通过bk-config服务获取一些信息的公共方法，方便管理，减少代码重复率
"""

# 统一使用 flow logger，与本目录其他模块保持一致
logger = logging.getLogger("flow")


def get_cluster_config(domain_name: str, db_version: str, module_id: int, namespace: str, bk_biz_id: str) -> dict:
    """
    获取已部署的实例配置,这里主要是拿tendbcluster,tendb 集群的配置
    """
    data = DBConfigApi.query_conf_item(
        params={
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": domain_name,
            "level_info": {"module": str(module_id)},
            "conf_file": db_version,
            "conf_type": ConfigTypeEnum.DBConf,
            "namespace": namespace,
            "format": FormatType.MAP_LEVEL,
        }
    )
    return data["content"]


def get_engine_from_bk_mysql_config(mysql_config: dict) -> str:
    """
    Retrieve the storage engine from MySQL configuration.

    This function iterates over the provided MySQL configurations and
    attempts to find the storage engine specified under the "mysqld"
    section. It checks for both "default_storage_engine" and
    "default-storage-engine" keys. If neither is found, it defaults to
    returning "innodb".

    Args:
        mysql_configs (dict): A dictionary of MySQL configuration settings.

    Returns:
        str: The name of the storage engine, or "innodb" if not specified.
    """
    if "default_storage_engine" in mysql_config["mysqld"]:
        return mysql_config["mysqld"]["default_storage_engine"]
    if "default-storage-engine" in mysql_config["mysqld"]:
        return mysql_config["mysqld"]["default-storage-engine"]
    return "innodb"


def get_mysql_version_and_charset(bk_biz_id, db_module_id, cluster_type) -> Any:
    """
    根据业务ID和模块ID，通过bk-config服务获取MySQL的版本号和字符集信息。

    Args:
        bk_biz_id (int or str): 业务ID
        db_module_id (int or str): 模块ID
        cluster_type (str): 集群类型（如 "tendbcluster"）

    Returns:
        tuple: (charset, db_version)
            charset (str): 字符集信息
            db_version (str): 数据库版本号
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.MODULE,
            "level_value": str(db_module_id),
            "conf_file": "deploy_info",
            "conf_type": "deploy",
            "namespace": cluster_type,
            "format": FormatType.MAP,
        }
    )["content"]

    return data["charset"], data["db_version"]


def get_backup_ini_config(bk_biz_id: int, db_module_id: int, cluster_type: str, cluster_domain: str):
    """
    根据集群维度，获取备份options配置
    @param bk_biz_id: 业务id
    @param db_module_id: db模块id
    @param cluster_type: 集群类型
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": cluster_domain,
            "conf_file": "dbbackup.ini",
            "conf_type": "backup",
            "namespace": cluster_type,
            "format": FormatType.MAP_LEVEL,
            "level_info": {"module": str(db_module_id)},
        }
    )
    return data["content"]


def get_backup_options_config(bk_biz_id: int, db_module_id: int, cluster_type: str, cluster_domain: str):
    """
    根据集群维度，获取备份options配置
    @param bk_biz_id: 业务id
    @param db_module_id: db模块id
    @param cluster_type: 集群类型
    @param cluster_domain: 集群域名
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": cluster_domain,
            "level_info": {"module": str(db_module_id)},
            "conf_file": "dbbackup.options",
            "conf_type": "backup",
            "namespace": cluster_type,
            "format": FormatType.MAP_LEVEL,
        }
    )
    return data["content"]


def get_mysql_config(
    bk_biz_id: int | str,
    db_module_id: int | str,
    cluster_type: str,
    immutable_domain: str,
    db_version: str,
    conf_type: str = ConfigTypeEnum.DBConf,
) -> dict:
    """生成并获取 mysql 实例集群级别配置（spider / spider-ctl / spider-mysql 通用入口）。

    设计要点 / 怎么做：
        - 数据源：bk-config 服务（``DBConfigApi.get_or_generate_instance_config``），
          区别于本模块其他 ``query_conf_item`` 只读接口，本方法会触发"生成并发布"，
          因此仅用于"实例级 / 集群级配置装配"场景，不要用于只读探测。
        - 通过 ``conf_type`` 区分存储层与接入层：
            * MySQL 存储层     → ``ConfigTypeEnum.DBConf``（默认）
            * Spider 接入层    → ``ConfigTypeEnum.ProxyConf``
        - ``db_version`` 直接作为 dbconfig 的 ``conf_file``（如 ``MySQL-5.7`` /
          ``Spider-3.7`` / ``Tdbctl``）。

    :param bk_biz_id: 业务 ID（str / int 均可，内部会 str() 后传给 dbconfig）
    :param db_module_id: DB 模块 ID；``db_version != "Tdbctl"`` 时必须为大于 0 的合法值
    :param cluster_type: dbconfig ``namespace``，如 ``tendbha`` / ``tendbcluster``
    :param immutable_domain: 集群不可变域名，作为 dbconfig ``level_value``
    :param db_version: 数据库版本 / conf_file，如 ``MySQL-5.7`` / ``Spider-3.7`` / ``Tdbctl``
    :param conf_type: 配置类型，默认 ``ConfigTypeEnum.DBConf``；spider 接入层需显式传
                      ``ConfigTypeEnum.ProxyConf``
    :return: dict，dbconfig ``content`` 段（形如 ``{"mysqld": {...}, ...}``）

    边界 / 异常：
        - ``db_version != "Tdbctl"`` 但 ``int(db_module_id) == 0`` → raise Exception，
          防止误用默认模块导致产生错配置
        - 下游 API 异常 → 原样向上抛出，由调用方决定日志与降级策略
    """
    if db_version != "Tdbctl" and int(db_module_id) == 0:
        # 非 Tdbctl 实例必须传入合法的 db_module_id（>0），否则视为非法调用
        raise Exception(f"The db_module_id parameter is illegal, db_module_id:{db_module_id}, db_version:{db_version}")
    data = DBConfigApi.get_or_generate_instance_config(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": immutable_domain,
            "level_info": {"module": str(db_module_id)},
            "conf_file": db_version,
            "conf_type": conf_type,
            "namespace": cluster_type,
            "format": FormatType.MAP_LEVEL,
            "method": ReqType.GENERATE_AND_PUBLISH,
        }
    )
    return data["content"]


def get_system_time_zone_in_bk_config(
    bk_biz_id: int | str,
    db_module_id: int | str,
    cluster_type: str,
) -> str:
    """从 DBM 配置中心（模块级 ``deploy_info``）获取 ``set_os_timezone`` 归一化值。

    设计要点 / 怎么做：
        - 数据源：``DBConfigApi.query_conf_item`` 单次调用；
          固定参数 ``level_name=MODULE`` / ``conf_file=deploy_info`` /
          ``conf_type=deploy`` / ``format=MAP``；
        - 出参从 ``content["set_os_timezone"]`` 抽取，做首尾空白裁剪归一化后返回；
        - 下游 API 抛异常时原样向上传播，由调用方决定日志与降级策略（与本模块内
          :func:`get_mysql_config` 保持一致的"不吞异常"风格）；
        - 作为通用工具函数使用，不依赖任何 pipeline / Service 上下文。

    :param bk_biz_id: 业务 ID（str 或 int，均会 str() 传参给 dbconfig）
    :param db_module_id: 集群所属 DB 模块 ID（dbconfig ``level_value``）
    :param cluster_type: dbconfig ``namespace``（如 ``tendbha`` / ``tendbcluster`` /
                         ``tendbsingle``）
    :return: 归一化后的时区字符串（``SYSTEM`` 或形如 ``±HH:00`` 的整点偏移）；
             若配置缺失或为空字符串，则返回空字符串 ``""``（同时输出 warning 日志）

    边界 / 异常：
        - 下游 API 抛异常 → 原样向上传播（不吞异常）
    """
    resp: dict = (
        DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.MODULE,
                "level_value": str(db_module_id),
                "conf_file": "deploy_info",
                "conf_type": "deploy",
                "namespace": cluster_type,
                "format": FormatType.MAP,
            }
        )
        or {}
    )

    content: dict = resp.get("content") or {}
    raw_tz: Any = content.get("set_os_timezone")
    # 归一化：仅做首尾空白裁剪；非 str 视为非法，走缺失分支
    normalized: str = raw_tz.strip() if isinstance(raw_tz, str) else ""
    if not normalized:
        # 配置缺失 / 空串 / 非 str：调用方通常会据此短路不下发时区 Job，
        # 这里补一条 warning，便于运维在链路上感知"未配置时区"的静默分支
        logger.warning(
            "set_os_timezone missing/empty in dbconfig, " "bk_biz_id=%s db_module_id=%s cluster_type=%s raw=%r",
            bk_biz_id,
            db_module_id,
            cluster_type,
            raw_tz,
        )
    return normalized
