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
import random
from datetime import datetime, timedelta
from typing import Dict

from blueapps.core.celery.celery import app
from celery.schedules import crontab
from django.utils import timezone

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

    # rate = get_rate_limit(group_cnt)

    if conf_cnt < 100:
        limit = conf_cnt
        execute_one_tendbha_task(cluster_id=info["cluster_id"], limit=limit)
    else:
        # 设置异步执行速度
        # app.control.rate_limit(execute_tendbha_partition_task.name, rate_limit=rate)
        start_time = timezone.now()
        for n in range(group_cnt):
            limit = group_size
            offset = n * group_size
            eta = start_time + timedelta(seconds=n * 50 + random.randint(1, 10))  # 每隔约50秒+1~10秒执行一个任务
            execute_one_tendbha_task(cluster_id=info["cluster_id"], limit=limit, offset=offset, eta=eta)


def execute_one_tendbha_task(cluster_id: int, limit: int, offset: int = 0, eta: datetime = None):
    """
    正式发起分区任务执行
    @return:
    """
    # 使用eta的年月日小时（如果eta存在）作为task_id的一部分
    if eta:
        time_str = eta.strftime("%Y%m%d%H%M%S")
    else:
        time_str = timezone.now().strftime("%Y%m%d%H%M%S")
    task_id = f"mysql_partition_task_{cluster_id}_{limit}_{offset}_{time_str}"
    partition_confs = get_partition_conf_by_domain(cluster_id, limit, offset, ClusterType.TenDBHA.value)
    execute_tendbha_partition_task.apply_async(args=[partition_confs], eta=eta, task_id=task_id)


@app.task(rate_limit="50/m")
def execute_one_tendbcluster_domain_task(info: Dict):
    """
    tendbcluster集群维度执行分区
    @return:
    """

    # 一组100个配置
    group_size = 100
    conf_cnt = info["conf_cnt"]
    group_cnt = math.ceil(conf_cnt / group_size)

    # 每批执行10个任务 也就是同时段会有1000个配置在执行
    batch_size = 10
    # 计算批次数 向上取整 保证都执行
    batch_cnt = math.ceil(group_cnt / batch_size)
    # 计算每批任务的间隔时间 向下取整 保证不超时
    # celery默认超时1小时的任务会重复执行，所以需要保证不超时
    batch_interval = max(math.floor(3500 / batch_cnt), 30)

    # rate = get_rate_limit(group_cnt)

    if conf_cnt < 100:
        limit = conf_cnt
        execute_one_tendbcluster_task(cluster_id=info["cluster_id"], limit=limit)
    else:
        # 设置异步执行速度
        # 修改会影响所有任务，这里使用eta参数控制执行速度
        # app.control.rate_limit(execute_tendbcluster_partition_task.name, rate_limit=rate)
        start_time = timezone.now()  # 使用utc时间
        for n in range(group_cnt):
            limit = group_size
            offset = n * group_size
            eta = start_time + timedelta(seconds=(n % batch_cnt) * batch_interval + random.randint(5, 10))
            execute_one_tendbcluster_task(cluster_id=info["cluster_id"], limit=limit, offset=offset, eta=eta)


def execute_one_tendbcluster_task(cluster_id: int, limit: int, offset: int = 0, eta: datetime = None):
    """
    正式发起分区任务执行
    @return:
    """
    # 使用eta的年月日小时（如果eta存在）作为task_id的一部分
    if eta:
        time_str = eta.strftime("%Y%m%d%H%M%S")
    else:
        time_str = timezone.now().strftime("%Y%m%d%H%M%S")

    task_id = f"mysql_partition_task_{cluster_id}_{limit}_{offset}_{time_str}"

    partition_confs = get_partition_conf_by_domain(cluster_id, limit, offset, ClusterType.TenDBCluster.value)
    execute_tendbcluster_partition_task.apply_async(args=[partition_confs], eta=eta, task_id=task_id)


def execute_one_task_by_config_id(infos: Dict, cluster_type: str, force: bool = False, partial_force: bool = False):
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
    partial_force: 是否部分强制执行 适用于tendbcluster集群，部分分片未执行初始化
    @return:
    """
    for domain, config_ids in infos.items():
        try:
            cluster_id = Cluster.objects.get(immute_domain=domain).id
        except Cluster.DoesNotExist:
            continue
        for config_id in config_ids:
            execute_one_config_task(cluster_id, config_id, cluster_type, force, partial_force)


def execute_one_config_task(
    cluster_id: int, config_id: int, cluster_type: str, force: bool = False, partial_force: bool = False
):
    partition_conf = get_partition_by_config_id(cluster_id, config_id, cluster_type)
    if cluster_type == ClusterType.TenDBCluster.value:
        execute_tendbcluster_partition_task.apply_async(
            args=[
                {
                    "cluster_id": partition_conf["cluster_id"],
                    "configs": partition_conf["configs"],
                    "force": force,
                    "partial_force": partial_force,
                }
            ]
        )
    elif cluster_type == ClusterType.TenDBHA.value:
        execute_tendbha_partition_task.apply_async(
            args=[{"cluster_id": partition_conf["cluster_id"], "configs": partition_conf["configs"], "force": force}]
        )
    else:
        raise Exception("cluster type not supported")
