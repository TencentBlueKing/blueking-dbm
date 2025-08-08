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
from typing import Dict

from blueapps.core.celery.celery import app
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models.cluster import Cluster
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket.constants import TicketType
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


@app.task(rate_limit="20/m")
def execute_tendbha_partition_task(info: Dict):
    """
    执行tendbha类型分区任务
    @return:
    """
    root_id = generate_root_id()
    data = {
        "uid": generate_root_id(),
        "ticket_type": TicketType.MYSQL_PARTITION_V2,
        "root_id": generate_root_id(),
        "bk_biz_id": get_bk_biz_id(info["cluster_id"]),
        "created_by": "partition",
        "cluster_type": ClusterType.TenDBHA.value,
        "cluster_id": info["cluster_id"],
        "configs": info["configs"],
    }
    MySQLController(root_id=root_id, ticket_data=data).mysql_partition_scene_v2()


@app.task(rate_limit="20/m")
def execute_tendbcluster_partition_task(info: Dict):
    """
    执行tendbcluster类型分区任务
    @return:
    """
    root_id = generate_root_id()
    data = {
        "uid": root_id,
        "ticket_type": TicketType.MYSQL_PARTITION_V2,
        "root_id": root_id,
        "bk_biz_id": get_bk_biz_id(info["cluster_id"]),
        "created_by": "partition",
        "cluster_type": ClusterType.TenDBCluster.value,
        "cluster_id": info["cluster_id"],
        "configs": info["configs"],
    }
    MySQLController(root_id=root_id, ticket_data=data).mysql_partition_scene_v2()


def get_bk_biz_id(cluster_id: int):
    """
    获取集群的bk_biz_id
    @return:
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        raise ClusterNotExistException(cluster_id=cluster_id, message=_("集群不存在"))
    return cluster.bk_biz_id
