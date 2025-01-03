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

from celery.schedules import crontab

from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.local_tasks.check_expired_job_users.check_expired_job_user_mysql import (
    CheckExpiredJobUserForMysql,
)
from backend.db_periodic_task.local_tasks.check_expired_job_users.check_expired_job_user_sqlserver import (
    CheckExpiredJobUserForSqlserver,
)
from backend.db_periodic_task.local_tasks.register import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute=00, hour=6))
def check_expired_job_users_for_mysql():
    """
    mysql 临时账号巡检
    每条凌晨6点执行
    """
    # 单节点、HA、TenDB Cluster集群
    CheckExpiredJobUserForMysql(
        mysql_cluster_types=[ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster]
    ).do_check()


@register_periodic_task(run_every=crontab(minute=00, hour=7))
def check_expired_job_users_for_sqlserver():
    """
    sqlserver临时账号巡检
    每条凌晨7点执行
    """
    # 单节点集群
    CheckExpiredJobUserForSqlserver(sqlserver_cluster_type=ClusterType.SqlserverSingle).do_check()

    # HA集群
    CheckExpiredJobUserForSqlserver(sqlserver_cluster_type=ClusterType.SqlserverHA).do_check()
