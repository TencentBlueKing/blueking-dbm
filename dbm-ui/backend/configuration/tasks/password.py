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

import logging

from django.utils.translation import gettext as _

from backend.components import DBPrivManagerApi
from backend.configuration.constants import DB_ADMIN_USER_MAP, DBM_PASSWORD_SECURITY_NAME, AdminPasswordRole, DBType
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.models import DBPeriodicTask
from backend.exceptions import ApiResultError

logger = logging.getLogger("root")


def randomize_admin_password(db_type: str, if_async: bool, range_type: str, clusters: list):
    """密码随机化定时任务"""
    try:
        DBPrivManagerApi.modify_admin_password(
            params={  # 管理用户
                "component": db_type,
                "username": DB_ADMIN_USER_MAP[db_type],  # 管理用户
                "operator": range_type,
                "clusters": clusters,
                "security_rule_name": DBM_PASSWORD_SECURITY_NAME,  # 用于生成随机化密码的安全规则
                "async": if_async,  # 异步执行，避免占用资源
                "range": range_type,  # 被锁定的密码到期，需要被随机化
            },
            raw=True,
        )
    except ApiResultError as e:
        # 捕获接口返回结果异常
        logger.error(_("「接口modify_mysql_admin_password返回结果异常」{}").format(e.message))
    except Exception as e:
        # 捕获接口其他未知异常
        logger.error(_("「接口modify_mysql_admin_password调用异常」{}").format(e))
    return


def randomize_mysql_admin_password(if_async: bool, range_type: str):
    """密码随机化定时任务，只随机化mysql数据库"""
    randomize_admin_password(DBType.MySQL, if_async, range_type, clusters=get_all_mysql_clusters())


def randomize_sqlserver_admin_password(if_async: bool, range_type: str):
    """密码随机化定时任务，只随机化sqlserver数据库"""
    randomize_admin_password(DBType.Sqlserver, if_async, range_type, clusters=get_all_sqlserver_clusters())


def get_mysql_instance(cluster: Cluster):
    def _get_instances(_role, _instances):
        if _role == AdminPasswordRole.TDBCTL.value:
            instance_info = {
                "role": _role,
                "addresses": [{"ip": instance.machine.ip, "port": instance.admin_port} for instance in _instances],
            }
            return instance_info
        instance_info = {
            "role": _role,
            "addresses": [{"ip": instance.machine.ip, "port": instance.port} for instance in _instances],
        }
        return instance_info

    instances = [_get_instances(AdminPasswordRole.STORAGE.value, cluster.storageinstance_set.all())]
    # spider节点和tdbctl节点修改密码指令不同，需区别
    if cluster.cluster_type == ClusterType.TenDBCluster:
        spiders = cluster.proxyinstance_set.all()
        dbctls = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )
        instances.append(_get_instances(AdminPasswordRole.SPIDER.value, spiders))
        instances.append(_get_instances(AdminPasswordRole.TDBCTL.value, dbctls))

    return {"bk_cloud_id": cluster.bk_cloud_id, "cluster_type": cluster.cluster_type, "instances": instances}


def get_all_mysql_clusters():
    """
    获取mysql所有集群的实例信息
    """
    cluster_types = [ClusterType.TenDBCluster.value, ClusterType.TenDBHA.value, ClusterType.TenDBSingle.value]
    clusters = Cluster.objects.prefetch_related("storageinstance_set", "proxyinstance_set").filter(
        cluster_type__in=cluster_types
    )
    cluster_infos = [get_mysql_instance(cluster) for cluster in clusters]
    return cluster_infos


def get_all_sqlserver_clusters():
    """
    获取sqlserver所有集群的实例信息
    """
    cluster_infos = []
    clusters = Cluster.objects.filter(
        cluster_type__in=[ClusterType.SqlserverHA.value, ClusterType.SqlserverSingle.value]
    )
    for cluster in clusters:
        storages = cluster.storageinstance_set.all()
        cluster_infos.append(
            {
                "bk_cloud_id": cluster.bk_cloud_id,
                "cluster_type": cluster.cluster_type,
                "instances": [
                    {
                        "role": AdminPasswordRole.STORAGE.value,
                        "addresses": [{"ip": s.machine.ip, "port": s.port} for s in storages],
                    }
                ],
            }
        )
    return cluster_infos


def get_periodic_task_run_every(func_name):
    """获取定时任务的运行周期"""
    db_task = DBPeriodicTask.objects.get(name__contains=func_name)
    return db_task.task.crontab.schedule
