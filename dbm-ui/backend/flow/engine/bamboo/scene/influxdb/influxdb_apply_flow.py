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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import DEFAULT_IP, InfluxdbActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.influxdb.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.influxdb.influxdb_config import InfluxdbConfigComponent
from backend.flow.plugins.components.collections.influxdb.influxdb_db_meta import InfluxdbDBMetaComponent
from backend.flow.plugins.components.collections.influxdb.trans_flies import TransFileComponent
from backend.flow.utils.influxdb.influxdb_act_playload import InfluxdbActPayload
from backend.flow.utils.influxdb.influxdb_context_dataclass import ActKwargs, ApplyContext

logger = logging.getLogger("flow")


class InfluxdbApplyFlow(object):
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

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.data["nodes"]:
            return []
        return self.data["nodes"][role]

    def __get_all_node_ips(self) -> list:
        exec_ip = []
        for role in self.data["nodes"]:
            exec_ip.extend(self.__get_node_ips_by_role(role))
        return exec_ip

    def deploy_influxdb_flow(self):
        """
        定义部署Influxdb
        """
        influxdb_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.InfluxDB)
        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_kwargs.file_list = trans_files.influxdb_apply(db_version=self.data["db_version"])
        act_kwargs.bk_cloud_id = self.data["nodes"]["influxdb"][0]["bk_cloud_id"]
        act_payload = InfluxdbActPayload(ticket_data=self.data)

        # 下发influxdb介质
        act_kwargs.exec_ip = self.__get_all_node_ips()
        influxdb_pipeline.add_act(
            act_name=_("下发influxdb介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 初始化节点
        act_kwargs.template = act_payload.get_payload(action=InfluxdbActuatorActionEnum.init.value, host=DEFAULT_IP)
        influxdb_pipeline.add_act(
            act_name=_("初始化节点"), act_component_code=ExecuteDBActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 解压influxdb包
        act_kwargs.template = act_payload.get_payload(
            action=InfluxdbActuatorActionEnum.decompressPkg.value, host=DEFAULT_IP
        )
        influxdb_pipeline.add_act(
            act_name=_("解压influxdb包"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 安装supervisor
        act_kwargs.template = act_payload.get_payload(
            action=InfluxdbActuatorActionEnum.installSupervisor.value, host=DEFAULT_IP
        )
        influxdb_pipeline.add_act(
            act_name=_("安装supervisor"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 安装influxdb
        influxdb_act_list = []
        for influxdb in self.data["nodes"]["influxdb"]:
            act_kwargs.exec_ip = [influxdb]
            act_kwargs.template = act_payload.get_payload(
                action=InfluxdbActuatorActionEnum.installInfluxdb.value,
                host=influxdb["ip"],
            )
            ip = influxdb["ip"]
            influxdb_act = {
                "act_name": _("安装influxdb-{}").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            influxdb_act_list.append(influxdb_act)
        influxdb_pipeline.add_parallel_acts(acts_list=influxdb_act_list)

        # 配置账号
        user_act_list = []
        for influxdb in self.data["nodes"]["influxdb"]:
            act_kwargs.exec_ip = [influxdb]
            act_kwargs.template = act_payload.get_payload(
                action=InfluxdbActuatorActionEnum.initUser.value,
                host=influxdb["ip"],
            )
            ip = influxdb["ip"]
            user_act = {
                "act_name": _("{}-初始化User").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            user_act_list.append(user_act)
        influxdb_pipeline.add_parallel_acts(acts_list=user_act_list)

        telegraf_act_list = []
        for influxdb in self.data["nodes"]["influxdb"]:
            act_kwargs.exec_ip = [influxdb]
            act_kwargs.template = act_payload.get_telegraf_payload(
                action=InfluxdbActuatorActionEnum.InstallTelegraf.value,
                host=influxdb["ip"],
            )
            ip = influxdb["ip"]
            influxdb_act = {
                "act_name": _("安装telegraf-{}").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            telegraf_act_list.append(influxdb_act)
        influxdb_pipeline.add_parallel_acts(acts_list=telegraf_act_list)

        influxdb_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=InfluxdbDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        influxdb_pipeline.add_act(
            act_name=_("回写influxdb集群配置"), act_component_code=InfluxdbConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        influxdb_pipeline.run_pipeline()
