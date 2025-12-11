"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import List

from backend.components.mysql_partition.client import DBPartitionApi


def get_exec_domain_info(cluster_type):
    """
    获取具有分区配置的集群信息
    @return: List[Dict], e.g.:
        [
            {"cluster_id": 1001, "conf_cnt": 18},
            {"cluster_id": 2007, "conf_cnt": 5}
        ]
    """
    params = {"name": "get_domain_info", "cluster_type": cluster_type}
    try:
        resp = DBPartitionApi.partition_conf_query(params=params, raw=True)
    except Exception as e:
        raise Exception("partition service request exception. {}".format(e))

    if resp["code"] != 0:
        raise Exception("partition service request failed. {}".format(resp["message"]))

    domain_infos = resp["data"]

    return domain_infos


def get_partition_conf_by_domain(cluster_id: int, limit: int, offset: int, cluster_type: str) -> List:
    """
    根据cluster_id获取指定cluster_type的分区配置
    @return:
    {
        "cluster_id": cluster_id,
        "configs": [
            {
                ...
            },
        ]
    }
    """
    params = {
        "name": "get_conf_by_domain",
        "cluster_type": cluster_type,
        "query_args": {"cluster_id": cluster_id},
        "page_args": {"limit": limit, "offset": offset},
    }
    try:
        resp = DBPartitionApi.partition_conf_query(params=params, raw=True)
    except Exception as e:
        raise Exception("partition service request exception. {}".format(e))

    if resp["code"] != 0:
        raise Exception("partition service request failed. {}".format(resp["message"]))

    partition_confs = resp["data"]

    return partition_confs


def get_partition_by_config_id(cluster_id: int, config_id: int, cluster_type: str) -> List:
    """
    根据配置id获取tendbcluster分区配置
    @return:
    {
        "cluster_id": cluster_id,
        "configs": [
            {
                ...
            },
        ]
    }
    """
    params = {
        "name": "get_conf_by_id",
        "cluster_type": cluster_type,
        "query_args": {"cluster_id": cluster_id, "config_id": config_id},
    }
    try:
        resp = DBPartitionApi.partition_conf_query(params=params, raw=True)
    except Exception as e:
        raise Exception("partition service request exception. {}".format(e))

    if resp["code"] != 0:
        raise Exception("partition service request failed. {}".format(resp["message"]))

    partition_conf = resp["data"]

    return partition_conf
