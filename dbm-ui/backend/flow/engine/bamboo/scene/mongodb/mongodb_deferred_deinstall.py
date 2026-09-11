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
import logging.config
from copy import deepcopy
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.consts import MongoDBInstanceType, MongoInstanceDbmonType
from backend.flow.engine.bamboo.scene.common.builder import Builder, Conditions, SubBuilder
from backend.flow.plugins.components.collections.common.empty_node import EmptyNodeComponent
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.fast_exec_script import MongoFastExecScriptComponent
from backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_check_meta import (
    MongoDeferredDeinstallCheckMetaComponent,
)
from backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta import (
    MongoDeferredDeinstallCleanupMetaComponent,
)
from backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_poll_gse import (
    MongoDeferredDeinstallPollGseComponent,
)
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")


def _normalize_instance_type(info: dict) -> str:
    raw = info.get("instance_type") or info.get("role") or ""
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    raw = str(raw).lower()
    if raw in (MongoDBInstanceType.MongoS.value, "mongos"):
        return MongoDBInstanceType.MongoS.value
    return MongoDBInstanceType.MongoD.value


def _build_reachable_deinstall_sub(root_id: str, ticket_data: dict, get_kwargs: ActKwargs, info: dict) -> SubBuilder:
    """GSE 可达后：介质下发 → 删 dbmon → 严格原子卸载。"""
    sub = SubBuilder(root_id=root_id, data=ticket_data)
    sub_kwargs = deepcopy(get_kwargs)
    sub_kwargs.payload["bk_cloud_id"] = info["bk_cloud_id"]
    sub_kwargs.payload["set_id"] = info.get("set_id") or ""
    sub_kwargs.payload["hosts"] = [{"ip": info["ip"], "bk_cloud_id": info["bk_cloud_id"]}]

    kwargs = sub_kwargs.get_send_media_kwargs(media_type="actuator")
    sub.add_act(act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs)

    kwargs = sub_kwargs.get_create_dir_kwargs()
    sub.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    kwargs_delete_dbmon = sub_kwargs.get_dbmon_operation_kwargs(
        node_info=info, operation_type=MongoInstanceDbmonType.DeleteDbmon
    )
    # 故障机 dbmon 配置可能已空/已删，延迟下架路径容忍失败（不阻断后续严格卸载）
    script_content = kwargs_delete_dbmon.get("script_content") or ""
    kwargs_delete_dbmon["script_content"] = script_content.replace(
        'echo "Error delete dbmon failed"; exit 1;',
        'echo "Warn delete dbmon failed (tolerate on deferred)"; exit 0;',
    )
    sub.add_act(
        act_name=_("MongoDB-{}:{}-删除dbmon".format(info["ip"], str(info["port"]))),
        act_component_code=MongoFastExecScriptComponent.code,
        kwargs=kwargs_delete_dbmon,
    )

    instance_type = _normalize_instance_type(info)
    kwargs = sub_kwargs.get_mongo_deferred_deinstall_kwargs(
        node_info=info, instance_type=instance_type, nodes_info=[info]
    )
    sub.add_act(
        act_name=_("MongoDB-延迟严格卸载-{}:{}".format(info["ip"], str(info["port"]))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )
    sub.add_act(
        act_name=_("MongoDB-清理残留Machine-{}".format(info["ip"])),
        act_component_code=MongoDeferredDeinstallCleanupMetaComponent.code,
        kwargs={"ip": info["ip"], "bk_cloud_id": info["bk_cloud_id"]},
    )
    return sub


class MongoDeferredDeInstallFlow(object):
    """MongoDB 延迟下架：meta 校验 → GSE 轮询 → 删 dbmon + 严格卸载。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data
        self.get_kwargs = ActKwargs()
        self.get_kwargs.payload = data
        self.get_kwargs.get_file_path()

    def multi_instance_deferred_deinstall_flow(self):
        pipeline = Builder(root_id=self.root_id, data=self.data)
        poll_interval_sec = int(self.data.get("poll_interval_sec") or 300)
        max_wait_hours = int(self.data.get("max_wait_hours") or 168)

        sub_pipelines = []
        for info in self.data["infos"]:
            sub = SubBuilder(root_id=self.root_id, data=self.data)

            check_act = sub.add_act(
                act_name=_("MongoDB-确认meta仍有主机-{}".format(info["ip"])),
                act_component_code=MongoDeferredDeinstallCheckMetaComponent.code,
                kwargs={"ip": info["ip"], "bk_cloud_id": info["bk_cloud_id"]},
                extend=False,
            )

            deinstall_branch = SubBuilder(root_id=self.root_id, data=self.data)
            deinstall_branch.add_act(
                act_name=_("MongoDB-GSE轮询可达-{}".format(info["ip"])),
                act_component_code=MongoDeferredDeinstallPollGseComponent.code,
                kwargs={
                    "ip": info["ip"],
                    "bk_cloud_id": info["bk_cloud_id"],
                    "poll_interval_sec": poll_interval_sec,
                    "max_wait_hours": max_wait_hours,
                },
            )
            reachable_sub = _build_reachable_deinstall_sub(self.root_id, self.data, self.get_kwargs, info)
            deinstall_branch.add_sub_pipeline(
                sub_flow=reachable_sub.build_sub_process(
                    sub_name=_("MongoDB-可达后下架-{}:{}".format(info["ip"], str(info["port"])))
                )
            )
            deinstall_act = deinstall_branch.build_sub_process(
                sub_name=_("MongoDB-等待并下架-{}:{}".format(info["ip"], str(info["port"])))
            )

            skip_act = sub.add_act(
                act_name=_("MongoDB-meta已无主机跳过-{}".format(info["ip"])),
                act_component_code=EmptyNodeComponent.code,
                kwargs={},
                extend=False,
            )

            sub.add_conditional_subs(
                source_act=check_act,
                conditions=[
                    Conditions(act_object=deinstall_act, express="==1"),
                    Conditions(act_object=skip_act, express="==0"),
                ],
                name=_("判断是否继续延迟下架"),
                conditions_param="machine_exists",
            )
            sub_pipelines.append(
                sub.build_sub_process(sub_name=_("MongoDB-延迟下架-{}:{}".format(info["ip"], str(info["port"]))))
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
