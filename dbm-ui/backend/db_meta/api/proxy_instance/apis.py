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

from django.db import transaction
from django.utils.translation import ugettext as _

from backend.constants import DEFAULT_TIME_ZONE
from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.api.cluster.nosqlcomm.cc_ops import cc_del_service_instances, cc_transfer_idle
from backend.db_meta.enums import AccessLayer, InstanceStatus
from backend.db_meta.models import Machine, ProxyInstance

logger = logging.getLogger("flow")


@transaction.atomic
def create(
    proxies,
    creator: str = "",
    status: str = "",
    time_zone: str = DEFAULT_TIME_ZONE,
):
    """
    ToDo: 冗余属性校验
    """
    proxies = request_validator.validated_proxy_list(proxies, allow_empty=False, allow_null=False)

    for proxy in proxies:
        proxy_ip = proxy["ip"]
        proxy_port = proxy["port"]
        version = proxy.get("version", "")

        machine_obj = Machine.objects.get(ip=proxy_ip)
        if machine_obj.access_layer != AccessLayer.PROXY:
            raise Exception("{} is not proxy layer".format(proxy_ip))

        real_status = status if status != "" else InstanceStatus.RUNNING

        ProxyInstance.objects.create(
            machine=machine_obj,
            port=proxy_port,
            admin_port=proxy_port + 1000,
            db_module_id=machine_obj.db_module_id,
            bk_biz_id=machine_obj.bk_biz_id,
            access_layer=machine_obj.access_layer,
            machine_type=machine_obj.machine_type,
            cluster_type=machine_obj.cluster_type,
            status=real_status,
            creator=creator,
            time_zone=time_zone,
            version=version,
        )


@transaction.atomic
def update(proxies):
    proxies = request_validator.validated_proxy_update(data=proxies)

    for proxy in proxies:
        ip = proxy["ip"]
        port = proxy["port"]

        proxy_obj = ProxyInstance.objects.get(machine__ip=ip, port=port)

        new_status = proxy.get("status", proxy_obj.status)

        proxy_obj.status = new_status
        proxy_obj.save()


@transaction.atomic
def decommission(instances: List[Dict]):
    """
    1. 仅支持 下架实例不在任何一个集群
    必要条件：
        1. 不属于任何一个集群 ;属于集群的实例，需要走集群内下架接口

    场景：
        1. 上架了，但未添加到集群
        2. 从集群内清理掉了 ；调用了 delete_proxies()
    """
    logger.info("user request decmmission instances {}".format(instances))
    proxy_objs = common.filter_out_instance_obj(instances, ProxyInstance.objects.all())

    _t = common.in_another_cluster(proxy_objs)
    if _t:
        raise Exception(_("proxy {} 在集群里边").format(_t))

    _t = common.not_exists(instances, ProxyInstance.objects.all())
    if _t:
        raise Exception(_("proxy {} 不存在").format(_t))

    for proxy_obj in proxy_objs:
        logger.info("remove proxy {} ".format(proxy_obj))
        cc_del_service_instances(proxy_obj)
        proxy_obj.delete()

        # 需要检查， 是否该机器上所有实例都已经清理干净，
        if len(ProxyInstance.objects.filter(machine__ip=proxy_obj.machine.ip).all()) > 0:
            logger.info("ignore storage machine {} , another instance existed.".format(proxy_obj.machine))
        else:
            logger.info("proxy machine {}".format(proxy_obj.machine))
            cc_transfer_idle(proxy_obj.machine)
            proxy_obj.machine.delete()
