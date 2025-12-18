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
import math
from typing import Dict

from blueapps.core.celery.celery import app
from celery.schedules import crontab

from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models.cluster import Cluster
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.mysql_partition.execute_partition_task import (
    execute_tendbcluster_partition_task,
    execute_tendbha_partition_task,
)
from backend.db_periodic_task.local_tasks.mysql_partition.get_partition_conf import (
    get_exec_domain_info,
    get_partition_by_config_id,
    get_partition_conf_by_domain,
)

logger = logging.getLogger("flow")


@register_periodic_task(run_every=crontab(minute=3, hour="3"))
def tendbha_partition_task():
    logger.info("start tendbha partition task v2!")
    # 异步执行，执行前以集群为单位生成参数 集群内根据分区配置量再进行切分
    domain_infos = get_exec_domain_info(ClusterType.TenDBHA.value)
    for info in domain_infos:
        execute_one_tendbha_domain_task.apply_async(args=[info])


@register_periodic_task(run_every=crontab(minute=3, hour="3"))
def tendbcluster_partition_task():
    logger.info("start tendbcluste partition task v2!")
    domain_infos = get_exec_domain_info(ClusterType.TenDBCluster.value)
    for info in domain_infos:
        execute_one_tendbcluster_domain_task.apply_async(args=[info])


def get_rate_limit(group_cnt: int):
    """
    相同集群 每分钟执行1个，每个100个配置
    """
    return "1/m"


@app.task(rate_limit="50/m")
def execute_one_tendbha_domain_task(info: Dict):
    """
    tendbha集群维度执行分区
    @return:
    """

    group_size = 100
    conf_cnt = info["conf_cnt"]
    group_cnt = math.ceil(conf_cnt / group_size)

    rate = get_rate_limit(group_cnt)

    if conf_cnt < 100:
        limit = conf_cnt
        execute_one_tendbha_task(cluster_id=info["cluster_id"], limit=limit)
    else:
        # 设置异步执行速度
        app.control.rate_limit(execute_tendbha_partition_task.name, rate_limit=rate)
        for n in range(group_cnt):
            limit = group_size
            offset = n * group_size
            execute_one_tendbha_task(cluster_id=info["cluster_id"], limit=limit, offset=offset)


def execute_one_tendbha_task(cluster_id: int, limit: int, offset: int = 0):
    """
    正式发起分区任务执行
    @return:
    """
    partition_confs = get_partition_conf_by_domain(cluster_id, limit, offset, ClusterType.TenDBHA.value)
    execute_tendbha_partition_task.apply_async(args=[partition_confs])


@app.task(rate_limit="50/m")
def execute_one_tendbcluster_domain_task(info: Dict):
    """
    tendbcluster集群维度执行分区
    @return:
    """

    group_size = 100
    conf_cnt = info["conf_cnt"]
    group_cnt = math.ceil(conf_cnt / group_size)

    rate = get_rate_limit(group_cnt)

    if conf_cnt < 100:
        limit = conf_cnt
        execute_one_tendbcluster_task(cluster_id=info["cluster_id"], limit=limit)
    else:
        # 设置异步执行速度
        app.control.rate_limit(execute_tendbcluster_partition_task.name, rate_limit=rate)
        for n in range(group_cnt):
            limit = group_size
            offset = n * group_size
            execute_one_tendbcluster_task(cluster_id=info["cluster_id"], limit=limit, offset=offset)


def execute_one_tendbcluster_task(cluster_id: int, limit: int, offset: int = 0):
    """
    正式发起分区任务执行
    @return:
    """
    partition_confs = get_partition_conf_by_domain(cluster_id, limit, offset, ClusterType.TenDBCluster.value)
    execute_tendbcluster_partition_task.apply_async(args=[partition_confs])


def execute_one_task_by_config_id(infos: Dict, cluster_type: str, force: bool = False):
    """
    根据配置id执行分区任务
    infos:
    {
        "domain": [config_id1, config_id2, ...],
        "domain2": [config_id1, config_id2, ...],
        ...
    }
    cluster_type: 集群类型
    force: 是否强制执行
    @return:
    """
    for domain, config_ids in infos.items():
        try:
            cluster_id = Cluster.objects.get(immute_domain=domain).id
        except Cluster.DoesNotExist:
            continue
        for config_id in config_ids:
            execute_one_config_task(cluster_id, config_id, cluster_type, force)


def execute_one_config_task(cluster_id: int, config_id: int, cluster_type: str, force: bool = False):
    partition_conf = get_partition_by_config_id(cluster_id, config_id, cluster_type)
    if cluster_type == ClusterType.TenDBCluster.value:
        execute_tendbcluster_partition_task.apply_async(
            args=[{"cluster_id": partition_conf["cluster_id"], "configs": partition_conf["configs"], "force": force}]
        )
    elif cluster_type == ClusterType.TenDBHA.value:
        execute_tendbha_partition_task.apply_async(
            args=[{"cluster_id": partition_conf["cluster_id"], "configs": partition_conf["configs"], "force": force}]
        )
    else:
        raise Exception("cluster type not supported")
