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

from backend.db_meta.enums import ClusterType
from backend.flow.consts import InfluxdbActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.influxdb.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.influxdb.influxdb_db_meta import InfluxdbDBMetaComponent
from backend.flow.utils.influxdb.influxdb_act_playload import get_base_payload
from backend.flow.utils.influxdb.influxdb_context_dataclass import ActKwargs, ApplyContext

logger = logging.getLogger("flow")


class InfluxdbDestroyFlow(object):
    """
    构建Influx下架流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.data = data

        # 写入cluster_type，转模块会使用
        self.data["cluster_type"] = ClusterType.Influxdb.value

    def __get_all_node_ips(self) -> list:
        return self.data["instance_list"]

    def destroy_influxdb_flow(self):
        """
        定义删除Influxdb实例
        :return:
        """
        influxdb_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_kwargs.bk_cloud_id = self.data["instance_list"][0]["bk_cloud_id"]
        sub_pipelines = []
        for instance in self.__get_all_node_ips():
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            # 清理数据
            ip = instance["ip"]
            act_kwargs.template = get_base_payload(action=InfluxdbActuatorActionEnum.CleanData.value, host=ip)
            act_kwargs.exec_ip = [{"ip": ip}]
            sub_pipeline.add_act(
                act_name=_("节点清理-{}").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("清理Influxdb {}子流程").format(ip)))
        # 并发执行所有子流程
        influxdb_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 清理DBMeta
        influxdb_pipeline.add_act(
            act_name=_("清理Meta"), act_component_code=InfluxdbDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        influxdb_pipeline.run_pipeline()
