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

from django.db.models import Q

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import LevelName
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigTypeEnum

from .models import TbRedisModuleSupport


def get_redis_moudles_detail(major_version: str, module_names: list = []) -> list:
    """
    根据major_version获取redis module详情信息
    """
    if not major_version:
        return []
    where = Q(major_version=major_version)
    if module_names:
        where = where & Q(module_name__in=module_names)

    redis_moudles = TbRedisModuleSupport.objects.filter(where).values("major_version", "module_name", "so_file")
    ret = []
    for row in redis_moudles:
        ret.append(
            {"major_version": row["major_version"], "module_name": row["module_name"], "so_file": row["so_file"]}
        )
    return ret


def get_cluster_redis_module_names(cluster_id: int) -> list:
    """
    获取集群的redis module名称
    """
    cluster = Cluster.objects.get(id=cluster_id)
    conf_data = DBConfigApi.query_conf_item(
        params={
            "bk_biz_id": str(cluster.bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": cluster.immute_domain,
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "conf_file": cluster.major_version,
            "conf_type": ConfigTypeEnum.DBConf,
            "namespace": cluster.cluster_type,
            "format": "map",
        }
    )
    if "loadmodule" not in conf_data["content"]:
        return []
    if not conf_data["content"]["loadmodule"]:
        return []
    modules_name = conf_data["content"]["loadmodule"].split(",")
    return modules_name


def get_cluster_redis_modules_detial(cluster_id: int) -> list:
    """
    获取集群的redis module详情信息
    """
    cluster = Cluster.objects.get(id=cluster_id)
    modules_name = get_cluster_redis_module_names(cluster_id)
    return get_redis_moudles_detail(cluster.major_version, modules_name)
