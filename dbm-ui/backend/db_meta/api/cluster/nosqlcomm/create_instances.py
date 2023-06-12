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

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api import machine, proxy_instance, storage_instance, storage_instance_tuple
from backend.db_meta.enums import InstanceRole

logger = logging.getLogger("flow")


@transaction.atomic
def create_mongo_instances(bk_biz_id, bk_cloud_id, machine_type, storages, spec_id: int = 0, spec_config: str = ""):
    """打包创建 MongoShard/MongoConfig 类型实例， 一主N从

    Args:
        bk_biz_id (_type_): _description_
        storages (_type_): _description_
          [{"ip":,"port":,"role":},{},{}]
    """
    try:
        machines, instances, tuple, primary = {}, [], [], {}
        for storage in storages:
            machines[storage["ip"]] = {
                "ip": storage["ip"],
                "bk_biz_id": bk_biz_id,
                "bk_cloud_id": bk_cloud_id,
                "machine_type": machine_type,
                "spec_id": spec_id,
                "spec_config": spec_config,
            }
            instances.append({"ip": storage["ip"], "port": storage["port"], "instance_role": storage["role"]})
            if storage["role"] == InstanceRole.MONGO_M1:
                primary = storage
        for storage in storages:
            if storage["role"] != InstanceRole.MONGO_M1:
                tuple.append(
                    {
                        "ejector": {"ip": primary["ip"], "port": primary["port"]},
                        "receiver": {"ip": storage["ip"], "port": storage["port"]},
                    }
                )
        machine.create(machines=list(machines.values()), bk_cloud_id=bk_cloud_id)
        storage_instance.create(instances=instances)
        storage_instance_tuple.create(tuple)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def create_proxies(bk_biz_id, bk_cloud_id, machine_type, proxies, spec_id: int = 0, spec_config: str = ""):
    """打包创建 Proxy 类型实例
        proxy 部署类型为单机单实例部署！！！
    Args:
        bk_biz_id (_type_): _description_
        proxies (_type_): _description_
          [{"ip":,"port":},{},{}]
    """
    try:
        machines = [
            {
                "ip": proxy["ip"],
                "bk_biz_id": bk_biz_id,
                "bk_cloud_id": bk_cloud_id,
                "machine_type": machine_type,
                "spec_id": spec_id,
                "spec_config": spec_config,
            }
            for proxy in proxies
        ]
        machine.create(machines=machines, bk_cloud_id=bk_cloud_id)
        proxy_instance.create(proxies=proxies)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def create_tendis_instances(bk_biz_id, bk_cloud_id, machine_type, storages, spec_id: int = 0, spec_config: str = ""):
    """打包创建 TendisCache/TendisSSD/TendisSingle 类型实例， 一主N从

    Args:
        bk_biz_id (_type_): _description_
        storages [{"master":{"ip":"","port":"","seg_range":""},"slave":{}}, {}]
    """
    try:
        machines, instances, tuple = {}, [], []
        for storage in storages:
            master = storage["master"]
            slave = storage["slave"]
            machines[master["ip"]] = {
                "ip": master["ip"],
                "bk_biz_id": bk_biz_id,
                "bk_cloud_id": bk_cloud_id,
                "machine_type": machine_type,
                "spec_id": spec_id,
                "spec_config": spec_config,
            }
            machines[slave["ip"]] = {
                "ip": slave["ip"],
                "bk_biz_id": bk_biz_id,
                "bk_cloud_id": bk_cloud_id,
                "machine_type": machine_type,
                "spec_id": spec_id,
                "spec_config": spec_config,
            }
            instances.append(
                {"ip": master["ip"], "port": master["port"], "instance_role": InstanceRole.REDIS_MASTER.value}
            )
            instances.append(
                {"ip": slave["ip"], "port": slave["port"], "instance_role": InstanceRole.REDIS_SLAVE.value}
            )
            tuple.append(
                {
                    "ejector": {"ip": master["ip"], "port": master["port"]},
                    "receiver": {"ip": slave["ip"], "port": slave["port"]},
                }
            )

        machine.create(machines=list(machines.values()), bk_cloud_id=bk_cloud_id)
        storage_instance.create(instances=instances)
        storage_instance_tuple.create(tuple)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e
