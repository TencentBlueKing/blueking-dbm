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
from typing import Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceStatus
from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.instance_op import InstanceOpSubTask
from backend.flow.plugins.components.collections.mongodb.change_instance_status_by_addrs import (
    ChangeInstanceStatusByAddrsComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.utils.mongodb.restart_target_resolver import ROLLING_RESTART_TIMEOUT_SECONDS, RestartTargetNode

RestartNodeCredentials = Dict[Tuple[int, str, int], Tuple[str, str]]


class MongoRollingRestartSubTask:
    """Rolling restart: mongod graceful 时先 RS 检查，再 shield → status→stop → start→status → unblock。"""

    @classmethod
    def _instance_type(cls, target: RestartTargetNode) -> Optional[str]:
        if target.is_mongos or target.role == MongoDBClusterRole.Mongos.value:
            return MongoDBClusterRole.Mongos.value
        return "mongod"

    @classmethod
    def _instance_kind(cls, instance_type: Optional[str]) -> str:
        if instance_type == MongoDBClusterRole.Mongos.value:
            return "proxy"
        return "storage"

    @classmethod
    def _node_credentials(cls, target: RestartTargetNode, credentials_map: RestartNodeCredentials) -> Tuple[str, str]:
        creds = credentials_map.get(target.node_key())
        if not creds:
            raise ValueError(_("missing credentials for {}:{}").format(target.ip, target.port))
        return creds

    @classmethod
    def _add_instance_op_act(
        cls,
        sb: SubBuilder,
        act_name: str,
        file_path: str,
        exec_node,
        op: str,
        instance_type: Optional[str],
        admin_username: str,
        admin_password: str,
        **extra,
    ):
        sb.add_act(
            act_name=act_name,
            act_component_code=ExecJobComponent2.code,
            kwargs=InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=exec_node,
                op=op,
                instance_type=instance_type,
                admin_username=admin_username,
                admin_password=admin_password,
                **extra,
            ),
        )

    @classmethod
    def _add_change_status_act(cls, sb: SubBuilder, target: RestartTargetNode, status: str, instance_kind: str):
        sb.add_act(
            act_name=_("MongoDB-修改实例状态-{}-{}:{}").format(status, target.ip, target.port),
            act_component_code=ChangeInstanceStatusByAddrsComponent.code,
            kwargs={
                "addrs": [target.addr()],
                "status": status,
                "instance_kind": instance_kind,
            },
        )

    @classmethod
    def _append_node_restart_acts(
        cls,
        sb: SubBuilder,
        file_path: str,
        target: RestartTargetNode,
        force: bool,
        credentials_map: RestartNodeCredentials,
    ) -> SubBuilder:
        exec_node = target.to_mongo_node()
        instance_type = cls._instance_type(target)
        instance_kind = cls._instance_kind(instance_type)
        admin_username, admin_password = cls._node_credentials(target, credentials_map)

        if not force and instance_type != MongoDBClusterRole.Mongos.value:
            cls._add_instance_op_act(
                sb,
                _("MongoDB-RS可用性检查-{}:{}").format(target.ip, target.port),
                file_path,
                exec_node,
                "check_rs_availability",
                instance_type,
                admin_username,
                admin_password,
            )

        cls._add_instance_op_act(
            sb,
            _("MongoDB-屏蔽dbmon-{}:{}").format(target.ip, target.port),
            file_path,
            exec_node,
            "shield_dbmon",
            instance_type,
            admin_username,
            admin_password,
        )

        # stop 前将 meta status 置为非 running，避免巡检/HA 误判
        cls._add_change_status_act(sb, target, InstanceStatus.UNAVAILABLE.value, instance_kind)

        stop_extra = {
            "graceful_stop": not force,
            "stop_timeout_seconds": ROLLING_RESTART_TIMEOUT_SECONDS,
        }
        if not force and instance_type != MongoDBClusterRole.Mongos.value:
            stop_extra["skip_rs_availability_check"] = True
        cls._add_instance_op_act(
            sb,
            _("MongoDB-停实例-{}:{}").format(target.ip, target.port),
            file_path,
            exec_node,
            "stop",
            instance_type,
            admin_username,
            admin_password,
            **stop_extra,
        )

        cls._add_instance_op_act(
            sb,
            _("MongoDB-启实例-{}:{}").format(target.ip, target.port),
            file_path,
            exec_node,
            "start",
            instance_type,
            admin_username,
            admin_password,
            start_timeout_seconds=ROLLING_RESTART_TIMEOUT_SECONDS,
        )

        # start 成功后恢复 RUNNING
        cls._add_change_status_act(sb, target, InstanceStatus.RUNNING.value, instance_kind)

        cls._add_instance_op_act(
            sb,
            _("MongoDB-解除屏蔽dbmon-{}:{}").format(target.ip, target.port),
            file_path,
            exec_node,
            "unblock_dbmon",
            instance_type,
            admin_username,
            admin_password,
        )
        return sb

    @classmethod
    def build_node_restart_subflow(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        file_path: str,
        target: RestartTargetNode,
        force: bool,
        credentials_map: RestartNodeCredentials,
    ):
        sb = SubBuilder(root_id=root_id, data=ticket_data)
        cls._append_node_restart_acts(
            sb,
            file_path=file_path,
            target=target,
            force=force,
            credentials_map=credentials_map,
        )
        return sb.build_sub_process(sub_name=_("MongoDB-滚动重启-{}:{}").format(target.ip, target.port))


def build_rs_restart_subflow(
    root_id: str,
    ticket_data: Optional[Dict],
    file_path: str,
    rs_name: str,
    members: List[RestartTargetNode],
    force: bool,
    credentials_map: RestartNodeCredentials,
):
    sb = SubBuilder(root_id=root_id, data=ticket_data)
    for target in members:
        sb.add_sub_pipeline(
            sub_flow=MongoRollingRestartSubTask.build_node_restart_subflow(
                root_id=root_id,
                ticket_data=ticket_data,
                file_path=file_path,
                target=target,
                force=force,
                credentials_map=credentials_map,
            )
        )
    if members:
        probe = members[0]
        exec_node = probe.to_mongo_node()
        admin_username, admin_password = MongoRollingRestartSubTask._node_credentials(probe, credentials_map)
        sb.add_act(
            act_name=_("MongoDB-RS全员就绪检查-{}").format(rs_name),
            act_component_code=ExecJobComponent2.code,
            kwargs=InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=exec_node,
                op="check_rs_all_members_ready",
                instance_type="mongod",
                admin_username=admin_username,
                admin_password=admin_password,
            ),
        )
    return sb.build_sub_process(sub_name=_("MongoDB-RS滚动重启-{}").format(rs_name))


def build_mongos_restart_subflow(
    root_id: str,
    ticket_data: Optional[Dict],
    file_path: str,
    target: RestartTargetNode,
    force: bool,
    credentials_map: RestartNodeCredentials,
):
    return MongoRollingRestartSubTask.build_node_restart_subflow(
        root_id=root_id,
        ticket_data=ticket_data,
        file_path=file_path,
        target=target,
        force=force,
        credentials_map=credentials_map,
    )
