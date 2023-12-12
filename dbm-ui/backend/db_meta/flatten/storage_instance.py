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

from backend.db_meta.enums import ClusterEntryType, ClusterPhase
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.flatten.machine import _machine_prefetch, _single_machine_cc_info, _single_machine_city_info
from backend.db_meta.models import StorageInstance
from backend.db_meta.models.extra_process import ExtraProcessInstance

logger = logging.getLogger("root")


def storage_instance(storages: QuerySet) -> List[Dict]:
    storages_list: List[StorageInstance] = list(
        storages.prefetch_related(
            *_machine_prefetch(),
            "as_ejector",
            "as_ejector__receiver__machine",
            "as_receiver",
            "as_receiver__ejector__machine",
            "proxyinstance_set",
            "proxyinstance_set__machine",
            "bind_entry",
            "bind_entry__clbentrydetail_set",
            "bind_entry__polarisentrydetail_set",
            "bind_entry__storageinstance_set",
            "bind_entry__storageinstance_set__machine",
            "cluster"
        )
    )
    # 提前查询出 dumper 的信息,目前只过滤出online状态的dumper实例信息
    cluster_ids = [cluster.id for ins in storages_list for cluster in ins.cluster.all()]
    dumper_infos: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
    for dumper in ExtraProcessInstance.objects.filter(
        cluster_id__in=cluster_ids, proc_type=ExtraProcessType.TBINLOGDUMPER, phase=ClusterPhase.ONLINE.value
    ):
        dumper_infos[dumper.cluster_id][dumper.extra_config.get("source_data_ip", "")].append(dumper)
    res = []
    for ins in storages_list:
        info = {
            **_single_machine_city_info(ins.machine),
            **_single_machine_cc_info(ins.machine),
            "port": ins.port,
            "ip": ins.machine.ip,
            "db_module_id": ins.db_module_id,
            "bk_biz_id": ins.bk_biz_id,
            "cluster": "",
            "access_layer": ins.access_layer,
            "machine_type": ins.machine_type,
            "instance_role": ins.instance_role,
            "instance_inner_role": ins.instance_inner_role,
            "cluster_type": ins.cluster_type,
            "status": ins.status,
        }

        receiver = []
        for e in ins.as_ejector.all():
            rinfo = {
                "ip": e.receiver.machine.ip,
                "port": e.receiver.port,
                "status": e.receiver.status,
                "is_stand_by": e.receiver.is_stand_by,
            }
            receiver.append(rinfo)
        info["receiver"] = receiver

        ejector = []
        for r in ins.as_receiver.all():
            einfo = {
                "ip": r.ejector.machine.ip,
                "port": r.ejector.port,
                "status": r.ejector.status,
                "is_stand_by": r.ejector.is_stand_by,
            }
            ejector.append(einfo)
        info["ejector"] = ejector

        bind_entry = defaultdict(list)
        for be in ins.bind_entry.all():
            storage_instance_list = list(be.storageinstance_set.all())
            bind_ips = list(set([ele.machine.ip for ele in storage_instance_list]))
            try:
                bind_port = storage_instance_list[0].port
            except (IndexError, AttributeError):
                bind_port = 0
            if be.cluster_entry_type == ClusterEntryType.DNS:
                bind_entry[be.cluster_entry_type].append(
                    {
                        "domain": be.entry,
                        "entry_role": be.role,
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

        proxyinstance_set = []
        for p in ins.proxyinstance_set.all():
            pinfo = {"ip": p.machine.ip, "port": p.port, "admin_port": p.admin_port, "status": p.status}
            proxyinstance_set.append(pinfo)
        info["proxyinstance_set"] = proxyinstance_set

        for cluster in ins.cluster.all():
            info["cluster"] = cluster.immute_domain
            info["cluster_id"] = cluster.id
            info["tbinlogdumpers"] = [
                {"ip": dumper.ip, "port": dumper.listen_port}
                for dumper in dumper_infos.get(cluster.id, {}).get(ins.machine.ip, [])
            ]
            # 只取第一个即可退出
            break
        res.append(info)

    return res
