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
import traceback
from typing import List, Optional

from backend.db_meta import flatten
from backend.db_meta.models import Cluster

logger = logging.getLogger("flow")


def get_cluster_detail(cluster_id: int):
    try:
        return flatten.tendis_cluster(Cluster.objects.filter(id=cluster_id))

    except Exception as e:  # pylint: disable=broad-except
        logger.error(traceback.format_exc())
        raise Exception("get cluster detail failed {}".format(e))


def get_cluster_proxies(cluster_id: int):
    try:
        cluster_obj = Cluster.objects.get(id=cluster_id)
        return [
            {"ip": proxy_obj.machine.ip, "port": proxy_obj.port, "admin_port": proxy_obj.admin_port}
            for proxy_obj in cluster_obj.proxyinstance_set.all()
        ]

    except Cluster.DoesNotExist as e:
        logger.error(traceback.format_exc())
        raise Exception("get cluster detail failed {}".format(e))


def get_clusters_details(cluster_ids: List):
    try:
        return flatten.tendis_cluster(Cluster.objects.filter(id__in=cluster_ids))
    except Exception as e:  # pylint: disable=broad-except
        logger.error(traceback.format_exc())
        raise Exception("get clusters detail failed {}".format(e))
