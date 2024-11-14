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

import json
import logging

import requests

from backend import env
from backend.components import CCApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.api.cluster.tendbha import decommission
from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("celery")

if env.SYNC_META_ENABLE:

    def test_sync_depend_bk_db():
        """
        同步 DBM 核心依赖的蓝鲸平台的数据库，目前已知以下：
        1. CMDB（MongoDB）
        2. JOB（MySQL，Redis，MongoDB）
        3. APIGW（MySQL，Redis）
        """

        tendbha_cluster = SystemSettings.get_setting_value(SystemSettingsEnum.SYNC_TENDBHA_CLUSTERS.value)

        charset = "utf8mb4"
        for cluster in tendbha_cluster:
            cluster_id = cluster["cluster_id"]
            url = "{}dbbase/filter_clusters/?bk_biz_id={}&cluster_ids={}".format(
                env.SYNC_META_DBM_APIGW_DOMAIN, cluster["bk_biz_id"], cluster_id
            )
            headers = {
                "Content-Type": "application/json",
                "X-Bkapi-Authorization": json.dumps(
                    {
                        "bk_app_code": env.SYNC_META_APP_CODE,
                        "bk_app_secret": env.SYNC_META_APP_TOKEN,
                        "bk_username": "admin",
                    }
                ),
            }
            # 从另一套蓝鲸中获取集群信息
            cluster_info = requests.get(url, headers=headers).json()["data"][0]
            master = {
                "ip": cluster_info["masters"][0]["ip"],
                "port": cluster_info["masters"][0]["port"],
                "Charset": charset,
                "Version": cluster_info["masters"][0]["version"],
            }
            slaves = [
                {"ip": slave["ip"], "port": slave["port"], "Charset": charset, "Version": slave["version"]}
                for slave in cluster_info["slaves"]
            ]
            proxies = [
                {"ip": proxy["ip"], "port": proxy["port"], "Charset": charset, "Version": proxy["version"]}
                for proxy in cluster_info["proxies"]
            ]

            # 判断元数据是否一致，若一致，则跳过
            # 否则删除元数据，重新导入
            try:
                cluster_obj = Cluster.objects.get(id=cluster_id)
            except Cluster.DoesNotExist:
                logger.info("Cluster {} does not exist. Continue to sync".format(cluster_id))
            else:
                master_exist = StorageInstance.objects.filter(
                    cluster__id=cluster_id, machine__ip=master["ip"], instance_role=InstanceRole.BACKEND_MASTER.value
                ).count()
                slave_count = StorageInstance.objects.filter(
                    cluster__id=cluster_id,
                    machine__ip__in=[slave["ip"] for slave in slaves],
                    instance_role=InstanceRole.BACKEND_SLAVE.value,
                ).count()
                proxy_count = ProxyInstance.objects.filter(
                    cluster__id=cluster_id,
                    machine__ip__in=[proxy["ip"] for proxy in proxies],
                    machine_type=MachineType.PROXY.value,
                ).count()
                if master_exist and slave_count == len(slaves) and proxy_count == len(proxies):
                    logger.info("Cluster {} has no changes. Skip!".format(cluster_id))
                    continue
                else:
                    logger.warning("Cluster {} has changes. Decommission it and resync!".format(cluster_id))
                    decommission(cluster_obj)

            # 导入元数据
            ips = [host["ip"] for host in cluster_info["masters"] + cluster_info["slaves"] + cluster_info["proxies"]]

            data = {
                "host_property_filter": {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_host_innerip", "operator": "in", "value": ips},
                    ],
                },
            }

            machines = CCApi.list_hosts_without_biz(data)["info"]

            data = {
                "bk_biz_id": env.SYNC_META_BIZ_ID,
                "db_module_id": env.SYNC_META_TENDBHA_MODULE_ID,
                "json_content": [
                    {
                        "name": cluster_info["cluster_name"],
                        "master": master,
                        "slaves": slaves,
                        "charset": charset,
                        "entries": [
                            {
                                "domain": cluster_info["master_domain"],
                                "instance": proxies,
                                "entry_role": "master_entry",
                            },
                            {"domain": cluster_info["slave_domain"], "instance": slaves, "entry_role": "slave_entry"},
                        ],
                        "proxies": proxies,
                        "version": cluster_info["masters"][0]["version"],
                        "machines": [
                            {
                                "IP": machine["bk_host_innerip"],
                                "Cpu": machine["bk_cpu"],
                                "Mem": machine["bk_mem"],
                                "City": machine["idc_city_name"],
                                "Disks": json.dumps({"/data": {"size": machine["bk_disk"], "disk_type": "SSD"}}),
                                "CCInfo": json.dumps(machine),
                                "CityID": 0,
                                "SubZone": "",
                                "BkHostID": machine["bk_host_id"],
                                "SubZoneID": 0,
                            }
                            for machine in machines
                        ],
                        "cluster_id": cluster_id,
                        "cluster_type": "tendbha",
                        "immute_domain": cluster_info["master_domain"],
                        "disaster_level": cluster_info["disaster_tolerance_level"],
                        "stand_by_slave": slaves[0],
                    }
                ],
                "proxy_spec_id": env.SYNC_META_TENDBHA_PROXY_SPEC_ID,
                "storage_spec_id": env.SYNC_META_TENDBHA_BACKEND_SPEC_ID,
            }

            Ticket.create_ticket(
                ticket_type=TicketType.MYSQL_HA_METADATA_IMPORT,
                creator=env.SYNC_META_CREATOR,
                bk_biz_id=data["bk_biz_id"],
                remark="auto sync metadata",
                details=data,
            )
