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

from backend.db_meta.enums import ClusterEntryType, MachineType
from backend.db_meta.flatten.machine import _machine_prefetch, _single_machine_cc_info, _single_machine_city_info
from backend.db_meta.models import ProxyInstance

logger = logging.getLogger("root")


def proxy_instance(proxies: QuerySet) -> List[Dict]:
    proxies_list: List[ProxyInstance] = list(
        proxies.prefetch_related(
            *_machine_prefetch(),
            "storageinstance",
            "storageinstance__machine",
            "bind_entry",
            "bind_entry__clbentrydetail_set",
            "bind_entry__polarisentrydetail_set",
            "bind_entry__proxyinstance_set",
            "bind_entry__proxyinstance_set__machine",
            "cluster"
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
            proxy_instance_list = list(be.proxyinstance_set.all())
            bind_ips = list(set([ele.machine.ip for ele in proxy_instance_list]))
            try:
                bind_port = proxy_instance_list[0].port
            except (IndexError, AttributeError):
                bind_port = 0
            if be.cluster_entry_type == ClusterEntryType.DNS:
                bind_entry[be.cluster_entry_type].append(
                    {
                        "domain": be.entry,
                        "entry_role": be.role,
                        "forward_entry_id": be.forward_to_id,
                        "bind_ips": bind_ips,
                        "bind_port": bind_port,
                    }
                )
            elif be.cluster_entry_type == ClusterEntryType.CLB:
                dt = be.clbentrydetail_set.get()
                bind_entry[be.cluster_entry_type].append(
                    {
                        "clb_ip": dt.clb_ip,
                        "clb_id": dt.clb_id,
                        "listener_id": dt.listener_id,
                        "clb_region": dt.clb_region,
                        "bind_ips": bind_ips,
                        "bind_port": bind_port,
                    }
                )
            elif be.cluster_entry_type == ClusterEntryType.POLARIS:
                dt = be.polarisentrydetail_set.get()
                bind_entry[be.cluster_entry_type].append(
                    {
                        "polaris_name": dt.polaris_name,
                        "polaris_l5": dt.polaris_l5,
                        "polaris_token": dt.polaris_token,
                        "alias_token": dt.alias_token,
                        "bind_ips": bind_ips,
                        "bind_port": bind_port,
                    }
                )
            else:
                bind_entry[be.cluster_entry_type].append(be.entry)

        info["bind_entry"] = dict(bind_entry)
        # 理论上集群 id 不可能是 0
        # 但是当元数据异常的时候, 某些实例可能不属于任何集群
        # 这里默认为 0 可以增加代码兼容性
        info["cluster_id"] = 0
        for cluster in ins.cluster.all():
            info["cluster"] = cluster.immute_domain
            info["cluster_id"] = cluster.id
            # 只取第一个即可退出
            break

        res.append(info)

    return res
