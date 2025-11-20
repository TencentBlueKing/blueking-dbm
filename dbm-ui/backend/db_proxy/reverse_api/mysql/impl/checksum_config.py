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
from typing import List, Optional, Union

from django.db.models import Q

from backend.components import DBConfigApi
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.flow.consts import ROLLBACK_DB_TAIL, STAGE_DB_HEADER, SYSTEM_DBS
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.mysql.mysql_bk_config import get_cluster_config, get_engine_from_bk_mysql_config


def checksum_config(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> List:
    m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
    q = Q()
    q |= Q(**{"machine": m})

    if port_list:
        q &= Q(**{"port__in": port_list})

    if m.access_layer == AccessLayer.PROXY:
        qs = ProxyInstance.objects.filter(q).prefetch_related("cluster")
    else:
        qs = StorageInstance.objects.filter(q).prefetch_related("cluster")

    usermap = PayloadHandler.get_mysql_static_account()

    res = []

    i: Union[StorageInstance, ProxyInstance]
    for i in qs.all():
        if not i.cluster.exists():
            continue

        cluster_obj = i.cluster.first()
        cluster_config = get_cluster_config(
            cluster_obj.immute_domain,
            cluster_obj.major_version,
            cluster_obj.db_module_id,
            cluster_obj.cluster_type,
            str(cluster_obj.bk_biz_id),
        )
        engine = get_engine_from_bk_mysql_config(cluster_config)

        checksum_yaml = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": f"{i.bk_biz_id}",
                "level_name": "cluster",
                "level_value": i.cluster.first().immute_domain,
                "conf_file": "checksum.yaml",
                "conf_type": "checksum",
                "namespace": i.cluster.first().cluster_type.lower(),
                "level_info": {"module": f"{i.db_module_id}"},
                "format": "map",
            }
        )["content"]

        res.append(
            {
                "bk_biz_id": i.bk_biz_id,
                "ip": ip,
                "port": i.port,
                "role": i.instance_inner_role,
                "cluster_id": i.cluster.first().id,
                "immute_domain": i.cluster.first().immute_domain,
                "db_module_id": i.db_module_id,
                "schedule": checksum_yaml.get("crond", "0 5 2 * * 1-5"),
                "api_url": "http://127.0.0.1:9999",
                "user": usermap["monitor_user"],
                "password": usermap["monitor_pwd"],
                "enable": engine.lower() not in ["rocksdb", "tokudb"] and checksum_yaml.get("enable", True),
                "filter": {
                    "databases": checksum_yaml.get("filter.databases", []),
                    "databases_regex": checksum_yaml.get("filter.databases_regex", []),
                    "tables": checksum_yaml.get("filter.tables", []),
                    "tables_regex": checksum_yaml.get("filter.tables_regex", []),
                    "ignore_databases": checksum_yaml.get("filter.ignore_databases", []) + SYSTEM_DBS,
                    "ignore_databases_regex": checksum_yaml.get("filter.ignore_databases_regex", [])
                    + [f"{STAGE_DB_HEADER}%", f"%{ROLLBACK_DB_TAIL}"],
                    "ignore_tables": checksum_yaml.get("filter.ignore_tables", []),
                    "ignore_tables_regex": checksum_yaml.get("filter.ignore_tables_regex", []),
                },
                "run-time": checksum_yaml.get("pt_checksum.args.run-time", "2h"),
            }
        )

    return res
