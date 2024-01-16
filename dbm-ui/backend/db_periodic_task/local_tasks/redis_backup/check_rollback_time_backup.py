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
from typing import Any, List

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta import api
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_services.redis.rollback.handlers import DataStructureHandler
from backend.db_services.redis.util import (
    is_have_binlog,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigTypeEnum
from backend.flow.engine.bamboo.scene.redis.common.exceptions import TendisGetBinlogFailedException
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


def check_backupfile_is_normal(cluster_id: int, rollback_time: str) -> bool:
    """
    输入集群id和回档时间：
    1、如果缺失全备份或者binlog备份，将抛出具体异常
    2、如果这个时间回档OK，则返回Ture

    """
    cluster_info = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)[0]
    # 获取 redis_config
    redis_config = get_cluster_config(
        cluster_info["immute_domain"],
        cluster_info["major_version"],
        ConfigTypeEnum.DBConf,
        cluster_info["cluster_type"],
        str(cluster_info["bk_biz_id"]),
    )
    kvstorecount = None
    if is_tendisplus_instance_type(cluster_info["cluster_type"]):
        logger.info("check_backupfile_is_normal kvstorecount:{}".format(redis_config["kvstorecount"]))
        # 获取tendisplus kvstorecount
        kvstorecount = redis_config["kvstorecount"]
    slave_instance = get_slave_instance(cluster_info["redis_slave_set"], cluster_info["cluster_type"])
    tendis_type = get_tendis_type_by_cluster_type(cluster_info["cluster_type"])
    for instance in slave_instance:
        slave_ip = instance.split(IP_PORT_DIVIDER)[0]
        slave_port = instance.split(IP_PORT_DIVIDER)[1]
        instance_full_backup, instance_binlog_backup = get_instance_backupfile(
            cluster_id, rollback_time, slave_ip, slave_port, tendis_type, kvstorecount
        )
        logger.info(
            "check_backupfile_is_normal tendis_type:{},instance_full_backup:{},instance_binlog_backup:{}".format(
                tendis_type, instance_full_backup, instance_binlog_backup
            )
        )
    return True


def get_instance_backupfile(
    cluster_id, rollback_time, source_ip, source_port, tendis_type, kvstorecount
) -> (dict, dict):
    rollback_handler = DataStructureHandler(cluster_id)
    instance_binlog_backupfile = []
    instance_full_backupfile = rollback_handler.query_latest_backup_log(
        str2datetime(rollback_time), source_ip, source_port
    )
    if instance_full_backupfile is None:
        raise TendisGetBinlogFailedException(message=_("获取实例 {}:{} 的binlog备份信息失败".format(source_ip, source_port)))
    # 全备份的开始时间
    backup_time = instance_full_backupfile["file_last_mtime"]
    logger.info(_("get_instance_backupfile instance_full_backupfile: {}".format(instance_full_backupfile)))
    # tendis ssd 和tendisplus才有binlog
    if is_have_binlog(tendis_type):
        # 查询binlog
        instance_binlog_backupfile = rollback_handler.query_binlog_from_bklog(
            start_time=str2datetime(backup_time),
            end_time=str2datetime(rollback_time),
            minute_range=120,
            host_ip=source_ip,
            port=source_port,
            kvstorecount=kvstorecount,
            tendis_type=tendis_type,
        )

        if instance_binlog_backupfile is None:
            raise TendisGetBinlogFailedException(message=_("获取实例 {}:{} 的binlog备份信息失败".format(source_ip, source_port)))

    return instance_full_backupfile, instance_binlog_backupfile


def get_tendis_type_by_cluster_type(cluster_type: str) -> str:
    """
    获取tendis_type
    """

    if is_tendisplus_instance_type(cluster_type):
        tendis_type = ClusterType.TendisplusInstance.value
    elif is_tendisssd_instance_type(cluster_type):
        tendis_type = ClusterType.TendisSSDInstance.value
    elif is_redis_instance_type(cluster_type):
        tendis_type = ClusterType.RedisInstance.value
    else:
        raise NotImplementedError("Not supported tendis type: %s" % cluster_type)
    logger.info(_("redis_data_structure_flow cluster_type: {}".format(cluster_type)))
    return tendis_type


def get_cluster_config(domain_name: str, db_version: str, conf_type: str, namespace: str, bk_biz_id: str) -> Any:
    """
    获取已部署的实例配置,这里主要是拿tendisplus kvstore
    """
    data = DBConfigApi.query_conf_item(
        params={
            "bk_biz_id": bk_biz_id,
            "level_name": LevelName.CLUSTER,
            "level_value": domain_name,
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "conf_file": db_version,
            "conf_type": conf_type,
            "namespace": namespace,
            "format": FormatType.MAP,
        }
    )
    return data["content"]


def get_slave_instance(redis_slave_set: List[str], cluster_type: str) -> List:
    """
    cahce,ssd :
    "redis_slave_set:['xx.xx.xx.xx:30000 0-104999', 'xx.xx.xx.xx:30001 105000-209999',
     'xx.xx.xx.xx:30002 210000-314999', 'xx.xx.xx.xx:30003 315000-419999']"}
     tendisplus:
     'redis_slave_set': ['xx.xx.xx.xx:30000', 'xx.xx.xx.xx:30000', 'xx.xx.xx.xx:30000'],
    """
    slave_instance = []
    if is_twemproxy_proxy_type(cluster_type):
        for instance_segment in redis_slave_set:
            instance = instance_segment.split(" ")[0]
            slave_instance.append(instance)
    else:
        slave_instance = redis_slave_set
    logger.info("check_backupfile_is_normal slave_instance:{}".format(slave_instance))
    return slave_instance
