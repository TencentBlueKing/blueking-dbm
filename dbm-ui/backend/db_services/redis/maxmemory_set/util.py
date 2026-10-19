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

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.models import Cluster
from backend.flow.consts import (
    DEFAULT_DB_MODULE_ID,
    ConfigFileEnum,
    ConfigTypeEnum,
    NameSpaceEnum,
    RedisMaxmemoryConfigType,
)

from .models import TbTendisMaxmemoryConfig


def is_bk_biz_id_in_blacklist(bk_biz_id: int) -> bool:
    """
    判断bk_biz_id是否在黑名单中
    :param bk_biz_id: 业务ID
    :return: True: 在黑名单中, False: 不在黑名单中
    """
    # select * from tb_tendis_maxmemory_config where config_type = 'bk_biz_id_blacklist';
    # 如果返回结果为空, 则不在黑名单中
    row = TbTendisMaxmemoryConfig.objects.filter(
        config_type=RedisMaxmemoryConfigType.BK_BIZ_ID_BLACKLIST.value
    ).first()
    if row and row.config_data != "":
        bk_biz_id_set = set(row.config_data.split(","))
        if str(bk_biz_id) in bk_biz_id_set:
            return True
    return False


def is_cluster_id_in_blacklist(cluster_id: int) -> bool:
    """
    判断cluster_id是否在黑名单中
    :param cluster_id: 集群ID
    :return: True: 在黑名单中, False: 不在黑名单中
    """
    # select * from tb_tendis_maxmemory_config where config_type = 'cluster_id_blacklist';
    # 如果返回结果为空, 则不在黑名单中
    row = TbTendisMaxmemoryConfig.objects.filter(
        config_type=RedisMaxmemoryConfigType.CLUSTER_ID_BLACKLIST.value
    ).first()
    if row and row.config_data != "":
        cluster_id_set = set(row.config_data.split(","))
        if str(cluster_id) in cluster_id_set:
            return True
    return False


def is_cluster_ids_in_blacklist(cluster_ids: list) -> bool:
    """
    判断cluster_ids是否在黑名单中,任意一个在黑名单中,则返回True
    :param cluster_ids: 集群ID列表
    :return: True: 在黑名单中, False: 不在黑名单中
    """
    if not cluster_ids:
        return False
    # bk_biz_ids 先去重
    bk_biz_ids = set()
    for cluster_id in cluster_ids:
        cluster = Cluster.objects.get(id=cluster_id)
        bk_biz_ids.add(cluster.bk_biz_id)
    for bk_biz_id in bk_biz_ids:
        if is_bk_biz_id_in_blacklist(bk_biz_id):
            return True

    for cluster_id in cluster_ids:
        if is_cluster_id_in_blacklist(cluster_id):
            return True
    return False


def default_maxmemory_config() -> dict:
    """
    获取默认的maxmemory配置
    """
    ret = {"used_memory_change_threshold": "200MB", "used_memory_change_percent": 20}
    row = TbTendisMaxmemoryConfig.objects.filter(
        config_type=RedisMaxmemoryConfigType.USED_MEMORY_CHANGE_THRESHOLD.value
    ).first()
    if row and row.config_data != "" and row.config_data != "0":
        ret["used_memory_change_threshold"] = row.config_data
    else:
        ret["used_memory_change_threshold"] = "200MB"

    row = TbTendisMaxmemoryConfig.objects.filter(
        config_type=RedisMaxmemoryConfigType.USED_MEMORY_CHANGE_PERCENT.value
    ).first()
    if row and row.config_data != "" and row.config_data != "0":
        ret["used_memory_change_percent"] = int(row.config_data)
    else:
        ret["used_memory_change_percent"] = 20
    return ret


def _query_maxmemory_config(bk_biz_id: int, namespace: str, level_name: str, level_value: str) -> dict:
    return DBConfigApi.query_conf_item(
        params={
            "bk_biz_id": str(bk_biz_id),
            "level_name": level_name,
            "level_value": str(level_value),
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "conf_file": ConfigFileEnum.MaxMemorySet,
            "conf_type": ConfigTypeEnum.Config,
            "namespace": namespace,
            "format": FormatType.MAP,
        }
    )["content"]


def get_dbmon_maxmemory_config_by_bkbizid(bk_biz_id: int, namespace: str = NameSpaceEnum.RedisCommon) -> dict:
    """按业务级别查询 maxmemory_set，只下发 DBConfig 的 content。"""
    return _query_maxmemory_config(bk_biz_id, namespace, LevelName.APP, str(bk_biz_id))


def get_dbmon_maxmemory_config_by_cluster_ids(cluster_ids: list) -> dict:
    """
    按集群级别查询 maxmemory_set，同一 dbmon 的多个集群须配置一致。
    在主从安装的时候可能会有传入多个cluster_id的情况。
    """
    if not cluster_ids:
        raise ValueError("cluster_ids cannot be empty")

    result = None
    for cluster_id in sorted(set(cluster_ids)):
        cluster = Cluster.objects.get(id=cluster_id)
        content = _query_maxmemory_config(
            cluster.bk_biz_id, cluster.cluster_type, LevelName.CLUSTER, cluster.immute_domain
        )
        if result is None:
            result = content
        elif content != result:
            raise ValueError(_("集群 {} 的 maxmemory_set 配置不一致，无法合并为一份 dbmon 配置").format(cluster_ids))
    assert result is not None
    return result
