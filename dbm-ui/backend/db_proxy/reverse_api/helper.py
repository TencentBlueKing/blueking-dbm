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
import ipaddress
import logging

from rest_framework.request import Request

from backend.db_meta.models import Machine
from backend.db_proxy.constants import DB_CLOUD_MACHINE_EXPIRE_TIME
from backend.db_proxy.reverse_api import mcache_lock, registered_machines_mcache
from backend.utils.redis import check_set_member_in_redis

logger = logging.getLogger("root")


def get_client_ip(request: Request):
    ip = request.query_params.get("ip")
    logger.info("read client ip from request query param: '{}'".format(ip))
    if not ip:
        logger.info("client ip not found in request query param, try in XFF")
        ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        logger.info("read client ip from XFF: '{}'".format(ip))

    logger.info("finally client ip: '{}'".format(ip))

    if not ip:
        raise Exception("client ip not found in request")

    return ip


def validate_machine_ip(bk_cloud_id: int, request: Request):
    client_ip = get_client_ip(request)
    client_ip_int = int(ipaddress.IPv4Address(client_ip))
    if client_ip_int in registered_machines_mcache[bk_cloud_id]:
        return True
    else:
        cache_key = f"cache_cloud_machine_{bk_cloud_id}"
        check_machine = lambda *args: Machine.objects.get(ip=client_ip, bk_cloud_id=bk_cloud_id)  # noqa: E731
        try:
            check_set_member_in_redis(cache_key, client_ip, check_machine, DB_CLOUD_MACHINE_EXPIRE_TIME)
            with mcache_lock:
                registered_machines_mcache[bk_cloud_id].add(client_ip_int)
        except Machine.DoesNotExist:
            raise Machine.DoesNotExist(f"Machine not found for ip {client_ip}, bk_cloud_id {bk_cloud_id}")
