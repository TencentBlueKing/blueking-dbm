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

from backend.components import DRSApi
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
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
            "cmds": ["select name from [master].[sys].[databases] where database_id > 4 and name != 'Monitor'"],
            "force": False,
        }
    )
    if ret[0]["error_msg"]:
        raise Exception(f"[{master_instance.ip_port}] get dbs failed: {ret[0]['error_msg']}")
    # 获取所有db名称
    all_dbs = [i["name"] for i in ret[0]["cmd_results"][0]["table_data"]]

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
