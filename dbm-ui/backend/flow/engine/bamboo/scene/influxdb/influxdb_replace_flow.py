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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Group, GroupInstance, StorageInstance
from backend.flow.consts import DEFAULT_IP, InfluxdbActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.influxdb.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.influxdb.influxdb_db_meta import InfluxdbDBMetaComponent
from backend.flow.plugins.components.collections.influxdb.influxdb_replace_config import InfluxdbReplaceConfigComponent
from backend.flow.plugins.components.collections.influxdb.trans_flies import TransFileComponent
from backend.flow.utils.influxdb.influxdb_act_playload import InfluxdbActPayload, get_base_payload
from backend.flow.utils.influxdb.influxdb_context_dataclass import ActKwargs, ApplyContext

logger = logging.getLogger("flow")


class InfluxdbReplaceFlow(object):
    """
    构建influxdb申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data
        # 写入cluster_type，转模块会使用
        self.data["cluster_type"] = ClusterType.Influxdb.value

    def replace_influxdb_flow(self):
        """
        定义部署Influxdb
        """
        influxdb_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.InfluxDB)
        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_payload = InfluxdbActPayload(ticket_data=self.data)
        sub_pipelines = []
        for i, influxdb in enumerate(self.data["new_nodes"]["influxdb"]):

            old_node = self.data["old_nodes"]["influxdb"][i]
            storage = StorageInstance.find_storage_instance_by_ip([old_node["ip"]])[0]
            group_instance = GroupInstance.objects.get(instance_id=storage.id)
            group = Group.objects.get(id=group_instance.group_id)
            self.data["group_name"] = group.name
            self.data["new_nodes"]["influxdb"][i]["db_version"] = storage.version
            self.data["new_nodes"]["influxdb"][i]["port"] = storage.port
            self.data["new_nodes"]["influxdb"][i]["group_id"] = group.id
            self.data["new_nodes"]["influxdb"][i]["instance_id"] = storage.id

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            act_kwargs.file_list = trans_files.influxdb_apply(db_version=storage.version)
            act_kwargs.bk_cloud_id = influxdb["bk_cloud_id"]

            # 下发influxdb介质
            act_kwargs.exec_ip = [influxdb]
            sub_pipeline.add_act(
                act_name=_("下发influxdb介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 初始化节点
            act_kwargs.template = get_base_payload(action=InfluxdbActuatorActionEnum.init.value, host=DEFAULT_IP)
            sub_pipeline.add_act(
                act_name=_("初始化节点"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 解压influxdb包
            act_kwargs.template = act_payload.get_replace_payload(
                action=InfluxdbActuatorActionEnum.decompressPkg.value,
                host=DEFAULT_IP,
                port=storage.port,
                version=storage.version,
                group_id=group.id,
                group_name=group.name,
                instance_id=storage.id,
            )
            sub_pipeline.add_act(
                act_name=_("解压influxdb包"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 安装supervisor
            act_kwargs.template = get_base_payload(
                action=InfluxdbActuatorActionEnum.installSupervisor.value, host=DEFAULT_IP
            )
            sub_pipeline.add_act(
                act_name=_("安装supervisor"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            ip = influxdb["ip"]
            # 安装influxdb
            act_kwargs.template = act_payload.get_replace_payload(
                action=InfluxdbActuatorActionEnum.installInfluxdb.value,
                host=ip,
                port=storage.port,
                version=storage.version,
                group_id=group.id,
                group_name=group.name,
                instance_id=storage.id,
            )
            sub_pipeline.add_act(
                act_name=_("安装influxdb-{}").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 配置账号
            act_kwargs.template = act_payload.get_replace_payload(
                action=InfluxdbActuatorActionEnum.initUser.value,
                host=ip,
                port=storage.port,
                version=storage.version,
                group_id=group.id,
                group_name=group.name,
                instance_id=storage.id,
            )
            sub_pipeline.add_act(
                act_name=_("{}-初始化User").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 安装telegraf
            act_kwargs.template = act_payload.get_replace_payload(
                action=InfluxdbActuatorActionEnum.InstallTelegraf.value,
                host=ip,
                port=storage.port,
                version=storage.version,
                group_id=group.id,
                group_name=group.name,
                instance_id=storage.id,
            )
            sub_pipeline.add_act(
                act_name=_("安装telegraf-{}").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("安装Influxdb {}子流程").format(ip)))
        influxdb_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        sub_pipelines = []
        for influxdb in self.data["old_nodes"]["influxdb"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            # 停止进程
            ip = influxdb["ip"]
            act_kwargs.template = get_base_payload(action=InfluxdbActuatorActionEnum.StopProcess.value, host=ip)
            act_kwargs.exec_ip = [{"ip": ip}]
            sub_pipeline.add_act(
                act_name=_("停止进程-{}").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            # 清理数据
            ip = influxdb["ip"]
            act_kwargs.template = get_base_payload(action=InfluxdbActuatorActionEnum.CleanData.value, host=ip)
            act_kwargs.exec_ip = [{"ip": ip}]
            sub_pipeline.add_act(
                act_name=_("节点清理-{}").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("下架Influxdb {}子流程").format(ip)))
        # 并发执行所有子流程
        influxdb_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        influxdb_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=InfluxdbDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        influxdb_pipeline.add_act(
            act_name=_("回写influxdb集群配置"),
            act_component_code=InfluxdbReplaceConfigComponent.code,
            kwargs=asdict(act_kwargs),
        )

        influxdb_pipeline.run_pipeline()
