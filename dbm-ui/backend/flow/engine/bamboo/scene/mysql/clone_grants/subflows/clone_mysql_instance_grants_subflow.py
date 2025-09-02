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
__all__ = ["clone_mysql_instance_grants_subflow", "clone_mysql_grants_relate_cluster_ids"]

import copy
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, List, Tuple

from django.utils.translation import ugettext as _

from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.consts import DBA_SYSTEM_USER, LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.mysql.clone_grants.exceptions import MySQLCloneGrantsValidateException
from backend.flow.engine.bamboo.scene.mysql.clone_grants.payload import CloneGrantsPayload
from backend.flow.engine.bamboo.scene.mysql.clone_grants.subflows.helpers import __build_trans_actuator_acts
from backend.flow.engine.bamboo.scene.mysql.clone_grants.validator.clone_mysql_grants_flow_validator import (
    CloneMySQLGrantsFlowValidator,
)
from backend.flow.plugins.components.collections.mysql.clone_grants import TransGrantsFileComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs


def clone_mysql_instance_grants_subflow(
    root_id: str,
    data: Dict,
    infos: List,
    with_actuator: bool = True,
) -> SubProcess:
    """
    bk_biz_id: int,
    infos: [
      {
        "bk_cloud_id": int,
        "machine_type": str,
        "source_address": str,
        "dest_addresses": [str]
      }
    ]
    1. 每一个 info 的 source 和 dest 必须同云区域
    2. 需要按 source 聚合下

    相关实例必须先完成临时账号授权

    引用环境的上下文
    必须兼容  backend.flow.engine.bamboo.scene.mysql.clone_grants.context.MySQLCloneGrantsContext
    """
    if not data.get("validated", False):
        v = CloneMySQLGrantsFlowValidator(ticket_data=data)
        if v:
            raise MySQLCloneGrantsValidateException(msg=v)

    cloud_ip_map, aggregated_infos = __aggregate_info(infos)

    pipe = SubBuilder(root_id=root_id, data=data)

    if with_actuator:
        pipe.add_parallel_acts(acts_list=__build_trans_actuator_acts(cloud_ip_map=cloud_ip_map))

    clone_subpipes = []
    for info in aggregated_infos:
        clone_subpipes.append(__clone_one_grants_info(root_id=root_id, data=data, info=info))

    pipe.add_parallel_sub_pipeline(sub_flow_list=clone_subpipes)

    return pipe.build_sub_process(sub_name=_("权限克隆"))


def __aggregate_info(infos: List) -> Tuple[Dict, List]:
    cloud_ip_map = defaultdict(set)  # 集中分发 dbactuator 用
    aggregated_infos_dict = defaultdict(set)  # 克隆子流程用

    for info in infos:
        bk_cloud_id = int(info["bk_cloud_id"])
        machine_type = info["machine_type"]
        source_address = info["source_address"]
        dest_addresses = info["dest_addresses"]

        k = f"{bk_cloud_id}-{source_address}-{machine_type}"
        aggregated_infos_dict[k].update(dest_addresses)

        cloud_ip_map[bk_cloud_id].add(source_address.split(":")[0])
        cloud_ip_map[bk_cloud_id].update([d.split(":")[0] for d in dest_addresses])

    aggregated_infos = []
    for k, v in aggregated_infos_dict.items():
        bk_cloud_id, source_address, machine_type = k.split("-")
        aggregated_infos.append(
            {
                "bk_cloud_id": int(bk_cloud_id),
                "machine_type": machine_type,
                "source_address": source_address,
                "dest_addresses": list(v),
            }
        )

    return cloud_ip_map, aggregated_infos


def __clone_one_grants_info(root_id: str, data: Dict, info: Dict) -> SubProcess:
    bk_cloud_id = int(info["bk_cloud_id"])
    source_address = info["source_address"]
    dest_addresses = info["dest_addresses"]

    source_ip, source_port = source_address.split(":")

    pipe = SubBuilder(root_id=root_id, data=copy.deepcopy(data))

    if info["machine_type"] in [MachineType.SINGLE, MachineType.BACKEND, MachineType.REMOTE]:
        inst_role = StorageInstance.objects.get(
            machine__ip=source_ip, port=int(source_port), machine__bk_cloud_id=bk_cloud_id
        ).instance_role
    else:
        inst_role = ProxyInstance.objects.get(
            machine__ip=source_ip, port=int(source_port), machine__bk_cloud_id=bk_cloud_id
        ).tendbclusterspiderext.spider_role

    pipe.add_act(
        act_name=_("导出 {} 权限".format(source_address)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                job_timeout=LONG_JOB_TIMEOUT,
                bk_cloud_id=bk_cloud_id,
                run_as_system_user=DBA_SYSTEM_USER,
                exec_ip=source_address.split(":")[0],
                payload_class=CloneGrantsPayload.payload_class_path(),
                get_mysql_payload_func=CloneGrantsPayload.dump_mysql_grants.__name__,
                cluster={
                    "host": source_ip,
                    "port": int(source_port),
                    "role": inst_role,
                    "bill_id": data["uid"],
                },
            )
        ),
        write_payload_var="report_result",
    )

    pipe.add_act(
        act_name=_("传输权限文件"),
        act_component_code=TransGrantsFileComponent.code,
        kwargs={
            "run_as_system_user": DBA_SYSTEM_USER,
            "exec_ip": [ele.split(":")[0] for ele in dest_addresses],
            "bk_cloud_id": bk_cloud_id,
            "source_ip_list": [source_ip],
            "bill_id": data["uid"],
        },
    )

    import_grants_acts = []
    for dest in dest_addresses:
        import_grants_acts.append(
            {
                "act_name": _("{} 导入权限文件".format(dest)),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": {
                    "bk_cloud_id": bk_cloud_id,
                    "run_as_system_user": DBA_SYSTEM_USER,
                    "exec_ip": dest.split(":")[0],
                    "payload_class": CloneGrantsPayload.payload_class_path(),
                    "get_mysql_payload_func": CloneGrantsPayload.import_grants_file.__name__,
                    "cluster": {
                        "machine_type": info["machine_type"],
                        "source_address": source_address,
                        "dest_address": dest,
                    },
                },
            }
        )

    pipe.add_parallel_acts(acts_list=import_grants_acts)

    return pipe.build_sub_process(sub_name=_("克隆 {} 权限".format(source_address)))


def clone_mysql_grants_relate_cluster_ids(infos: List) -> List:
    relate_cluster_ids = set()  # 临时账号授权用
    for info in infos:
        for inst_address in info["dest_addresses"] + [info["source_address"]]:
            ip, port = inst_address.split(":")

            if info["machine_type"] in [MachineType.BACKEND, MachineType.REMOTE, MachineType.SINGLE]:
                inst = StorageInstance.objects.get(
                    machine__bk_cloud_id=info["bk_cloud_id"], machine__ip=ip, port=int(port)
                )
                cluster_obj = Cluster.objects.get(storageinstance=inst)
            # elif info["machine_type"] == MachineType.SPIDER:
            else:  # 只能是 spider
                inst = ProxyInstance.objects.get(
                    machine__bk_cloud_id=info["bk_cloud_id"], machine__ip=ip, port=int(port)
                )
                cluster_obj = Cluster.objects.get(proxyinstance=inst)
            # else:
            #     pass

            relate_cluster_ids.add(cluster_obj.pk)

    return list(relate_cluster_ids)
