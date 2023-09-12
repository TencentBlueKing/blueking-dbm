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
from typing import Dict, List

from django.db.models import Q, QuerySet

from backend import env
from backend.components import CCApi

logger = logging.getLogger("root")


def in_another_cluster(instances: QuerySet) -> List[Dict]:
    return list(instances.filter(cluster__isnull=False))


def filter_out_instance_obj(instances: List[Dict], qs: QuerySet) -> QuerySet:
    queries = Q()
    for i in instances:
        queries |= Q(**{"machine__ip": i["ip"], "port": i["port"]})

    return qs.filter(queries)


def not_exists(instances: List[Dict], qs: QuerySet) -> List[Dict]:
    ne = set(map(lambda e: (e["ip"], e["port"]), instances)) - set(qs.values_list("machine__ip", "port"))
    return list(map(lambda e: {"ip": e[0], "port": e[1]}, ne))


def equ_list_of_dict(a, b: List) -> bool:
    d1 = [e for e in a if e not in b]
    d2 = [e for e in b if e not in a]
    logger.debug("{} {} {} {}".format(a, b, d1, d2))
    if d1 or d2:
        return False
    return True


def remain_instance_obj(instances: List[Dict], qs: QuerySet) -> List[Dict]:
    ne = set(qs.values_list("machine__ip", "port")) - set(map(lambda e: (e["ip"], e["port"]), instances))
    return list(map(lambda e: {"ip": e[0], "port": e[1]}, ne))
