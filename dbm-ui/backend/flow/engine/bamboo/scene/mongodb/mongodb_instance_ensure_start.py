# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MongoDB 进程拉起（MONGODB_INSTANCE_ENSURE_START）
================================================
- 前置单据：仅由自愈链路触发——MONGODB_AUTOFIX_PRE triage 判定 process_bad 后自动创本单，
  不是工具箱手工提单；与「MongoDB 实例重启」(MONGODB_INSTANCE_RELOAD) 无关。
- 产品入口：不挂 MongoDB 工具箱菜单 / 前端路由；勿在 toolboxMenuList、routes 中注册。
- 行为：ensure_start（已监听则跳过，否则 start+wait）→ meta RUNNING → start_dbmon
  → service_status_check → fix_service_status（与节点状态修复对齐）。
  不屏蔽 dbmon；无 stop、无 UNAVAILABLE 闪断。
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceStatus
from backend.flow.consts import MongoDBActuatorActionEnum, MongoDBClusterRole, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.sub_task.instance_op import InstanceOpSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.plugins.components.collections.mongodb.change_instance_status_by_addrs import (
    ChangeInstanceStatusByAddrsComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.plugins.components.collections.mongodb.fix_instance_status import (
    ExecFixInstanceStatusOperationComponent,
)
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_util import MongoUtil
from backend.flow.utils.mongodb.restart_target_resolver import (
    INFO_KIND_EXPLICIT,
    ROLLING_RESTART_TIMEOUT_SECONDS,
    RestartTargetNode,
    batch_get_restart_node_credentials,
    collect_hosts,
    resolve_restart_targets_from_infos,
)

logger = logging.getLogger("flow")


class MongoDBInstanceEnsureFlow:
    """
    MongoDB 进程拉起 Flow。

    前置：MONGODB_AUTOFIX_PRE（autofix）process_bad 跟单；不提供工具箱入口。
    步骤：ensure_start → meta RUNNING → start_dbmon → service_status_check → fix_service_status。
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.payload = data or {}
        self._normalize_uid()

    def _normalize_uid(self):
        uid = self.payload.get("uid")
        if uid is None or (isinstance(uid, str) and not uid.strip()):
            self.payload["uid"] = (
                f"mongo-instance-ensure-{self.payload.get('bk_biz_id', 0)}-"
                f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-"
                f"{self.root_id[:8]}"
            )

    @staticmethod
    def _instance_type(target: RestartTargetNode) -> Optional[str]:
        if target.is_mongos or target.role == MongoDBClusterRole.Mongos.value:
            return MongoDBClusterRole.Mongos.value
        return "mongod"

    @staticmethod
    def _instance_kind(instance_type: Optional[str]) -> str:
        if instance_type == MongoDBClusterRole.Mongos.value:
            return "proxy"
        return "storage"

    def _add_instance_op_act(
        self,
        sb: SubBuilder,
        act_name: str,
        file_path: str,
        target: RestartTargetNode,
        op: str,
        admin_username: str,
        admin_password: str,
        **extra,
    ):
        sb.add_act(
            act_name=act_name,
            act_component_code=ExecJobComponent2.code,
            kwargs=InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=target.to_mongo_node(),
                op=op,
                instance_type=self._instance_type(target),
                admin_username=admin_username,
                admin_password=admin_password,
                **extra,
            ),
        )

    def _build_node_ensure_subflow(
        self,
        file_path: str,
        target: RestartTargetNode,
        credentials_map: dict,
    ):
        creds = credentials_map.get(target.node_key())
        if not creds:
            raise ValueError(_("missing credentials for {}:{}").format(target.ip, target.port))
        admin_username, admin_password = creds
        instance_kind = self._instance_kind(self._instance_type(target))

        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        self._add_instance_op_act(
            sb,
            _("MongoDB-进程拉起-{}:{}").format(target.ip, target.port),
            file_path,
            target,
            "ensure_start",
            admin_username,
            admin_password,
            start_timeout_seconds=ROLLING_RESTART_TIMEOUT_SECONDS,
        )
        sb.add_act(
            act_name=_("MongoDB-修改实例状态-{}-{}:{}").format(InstanceStatus.RUNNING.value, target.ip, target.port),
            act_component_code=ChangeInstanceStatusByAddrsComponent.code,
            kwargs={
                "addrs": [target.addr()],
                "status": InstanceStatus.RUNNING.value,
                "instance_kind": instance_kind,
            },
        )
        # 末尾尝试拉起 dbmon（不经 shield/unblock）；start.sh 幂等即可
        self._add_instance_op_act(
            sb,
            _("MongoDB-尝试拉起dbmon-{}:{}").format(target.ip, target.port),
            file_path,
            target,
            "start_dbmon",
            admin_username,
            admin_password,
        )
        # process_bad：拉起后再做与 FIX_STATUS 相同的探测与元数据修复
        sb.add_act(
            act_name=_("MongoDB-服务状态检查-{}:{}").format(target.ip, target.port),
            act_component_code=ExecJobComponent2.code,
            kwargs=InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=target.to_mongo_node(),
                op="service_status_check",
                username=MongoDBManagerUser.MonitorUser.value,
                instance_type=self._instance_type(target),
            ),
        )
        sb.add_act(
            act_name=_("MongoDB-节点状态修复-{}:{}").format(target.ip, target.port),
            act_component_code=ExecFixInstanceStatusOperationComponent.code,
            kwargs={
                "set_trans_data_dataclass": CommonContext.__name__,
                "get_trans_data_ip_var": None,
                "trans_data_var": {
                    "instance": {
                        "ip": target.ip,
                        "port": target.port,
                        "bk_cloud_id": target.bk_cloud_id,
                        "cluster_id": target.cluster_id,
                        "cluster_type": target.cluster_type,
                        "role": target.role,
                        "status": InstanceStatus.RUNNING.value,
                    }
                },
                "db_act_template": {
                    "action": MongoDBActuatorActionEnum.FixServiceStatus.value,
                    "payload": {
                        "ip": target.ip,
                        "port": target.port,
                        "op": "fix_service_status",
                    },
                },
            },
        )
        return sb.build_sub_process(sub_name=_("MongoDB-进程拉起-{}:{}").format(target.ip, target.port))

    def start(self):
        infos = self.payload.get("infos") or []
        if not infos:
            raise ValueError(_("infos cannot be empty"))

        # FlowParamBuilder / 自愈创单不经 InstanceRestartPayloadSerializer，需补 info_kind
        for info in infos:
            if info.get("info_kind"):
                continue
            if info.get("ip") and info.get("port") is not None and info.get("cluster_id") is not None:
                info["info_kind"] = INFO_KIND_EXPLICIT

        bk_cloud_id = self.payload.get("bk_cloud_id")
        if bk_cloud_id is None:
            cloud_ids = {info["bk_cloud_id"] for info in infos if info.get("bk_cloud_id") is not None}
            if len(cloud_ids) == 1:
                bk_cloud_id = cloud_ids.pop()
                self.payload["bk_cloud_id"] = bk_cloud_id
            else:
                raise ValueError(_("bk_cloud_id is required"))

        targets = resolve_restart_targets_from_infos(
            infos,
            bk_biz_id=self.payload["bk_biz_id"],
            bk_cloud_id=bk_cloud_id,
        )
        if not targets:
            raise ValueError(_("no MongoDB instances to ensure start"))

        credentials_map = batch_get_restart_node_credentials(targets)
        actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]
        file_list = GetFileList(db_type=DBType.MongoDB).mongodb_actuator_pkg()
        bk_host_list = collect_hosts(targets)

        pipeline = Builder(root_id=self.root_id, data=self.payload)
        if file_list and bk_host_list:
            pipeline.add_act(
                **SendMedia.act(
                    act_name=_("MongoDB-进程拉起介质下发"),
                    file_list=file_list,
                    bk_host_list=bk_host_list,
                    file_target_path=actuator_workdir,
                )
            )

        # 自愈单实例为主；多实例串行，避免同机并发启停干扰
        for target in sorted(targets, key=lambda n: (n.ip, n.port)):
            pipeline.add_sub_pipeline(
                sub_flow=self._build_node_ensure_subflow(actuator_workdir, target, credentials_map)
            )
        pipeline.run_pipeline()

    def multi_instance_ensure_start_flow(self):
        self.start()
