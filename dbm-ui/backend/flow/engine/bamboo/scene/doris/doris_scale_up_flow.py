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
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.doris.doris_base_flow import (
    DorisBaseFlow,
    be_exists_in_ticket,
    fe_exists_in_ticket,
    get_all_node_ips_in_ticket,
)
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.doris_dns_manage import DorisDnsManageComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.doris.get_doris_resource import GetDorisResourceComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DnsKwargs, DorisActKwargs, DorisApplyContext

logger = logging.getLogger("flow")


class DorisScaleUpFlow(DorisBaseFlow):
    """
    Doris扩容流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        return flow_data

    def scale_up_doris_flow(self):
        """
        定义扩容Doris集群
        :return:
        """
        scale_up_data = self.__get_flow_data()
        doris_pipeline = Builder(root_id=self.root_id, data=scale_up_data)

        trans_files = GetFileList(db_type=DBType.Doris)

        act_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__
        act_kwargs.file_list = trans_files.doris_apply(db_version=self.db_version)

        doris_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetDorisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        doris_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetDorisResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=scale_up_data)
        doris_pipeline.add_act(
            act_name=_("下发DORIS介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 新节点统一初始化流程
        sub_common_pipelines = self.new_common_sub_flows(
            act_kwargs=act_kwargs,
            data=scale_up_data,
        )
        # 并发执行所有子流程
        doris_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_common_pipelines)

        act_kwargs.get_doris_payload_func = DorisActPayload.get_add_nodes_metadata_payload.__name__
        doris_pipeline.add_act(
            act_name=_("集群元数据更新"),
            act_component_code=ExecuteDorisActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 扩容FE节点子流程
        if fe_exists_in_ticket(data=scale_up_data):
            sub_new_fe_pipelines = self.new_fe_sub_flows(act_kwargs=act_kwargs, data=scale_up_data)
            doris_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_new_fe_pipelines)

        # 扩容BE节点子流程
        if be_exists_in_ticket(data=scale_up_data):
            sub_new_be_acts = self.new_bew_sub_acts(act_kwargs=act_kwargs, data=scale_up_data)
            doris_pipeline.add_parallel_acts(acts_list=sub_new_be_acts)

        # 添加到DBMeta并转模块
        doris_pipeline.add_act(
            act_name=_("添加到DBMeta"), act_component_code=DorisMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 添加域名
        dns_kwargs = DnsKwargs(
            bk_cloud_id=scale_up_data["bk_cloud_id"],
            dns_op_type=DnsOpType.UPDATE,
            domain_name=self.domain,
            dns_op_exec_port=self.http_port,
        )
        doris_pipeline.add_act(
            act_name=_("添加域名"),
            act_component_code=DorisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        doris_pipeline.run_pipeline()
