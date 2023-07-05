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
from collections import defaultdict
from typing import Dict, List

from django.db.models import QuerySet

from backend.db_meta.enums import MachineType
from backend.db_meta.models import ProxyInstance

from .machine import _machine_prefetch, _single_machine_cc_info, _single_machine_city_info

logger = logging.getLogger("root")


def proxy_instance(proxies: QuerySet) -> List[Dict]:
    proxies_list: List[ProxyInstance] = list(
        proxies.prefetch_related(
            *_machine_prefetch(),
            "storageinstance",
            "storageinstance__machine",
            "bind_entry",
        )
    )
    res = []
    for ins in proxies_list:
        info = {
            **_single_machine_city_info(ins.machine),
            **_single_machine_cc_info(ins.machine),
            "admin_port": ins.admin_port,
            "port": ins.port,
            "ip": ins.machine.ip,
            "db_module_id": ins.db_module_id,
            "bk_biz_id": ins.bk_biz_id,
            "cluster": "",
            "access_layer": ins.access_layer,
            "machine_type": ins.machine_type,
            "cluster_type": ins.cluster_type,
            "status": ins.status,
        }

        if ins.machine_type == MachineType.SPIDER.value:
            info["spider_role"] = ins.tendbclusterspiderext.spider_role

        storageinstance = []
        for s in ins.storageinstance.all():
            sinfo = {"ip": s.machine.ip, "port": s.port, "is_stand_by": s.is_stand_by}
            storageinstance.append(sinfo)
        info["storageinstance"] = storageinstance

        bind_entry = defaultdict(list)
        for be in ins.bind_entry.all():
            bind_entry[be.cluster_entry_type].append(be.entry)

        info["bind_entry"] = dict(bind_entry)

        res.append(info)

        cluster_qs = ins.cluster.all()
        if cluster_qs.exists():
            info["cluster"] = cluster_qs.first().immute_domain

    return res
