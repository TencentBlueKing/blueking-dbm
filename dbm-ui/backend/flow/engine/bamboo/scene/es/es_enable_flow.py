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
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.es.es_flow import EsFlow
from backend.flow.plugins.components.collections.es.es_db_meta import EsMetaComponent
from backend.flow.plugins.components.collections.es.exec_es_actuator_script import ExecuteEsActuatorScriptComponent
from backend.flow.plugins.components.collections.es.get_es_payload import GetEsActPayloadComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.utils.es.es_act_payload import EsActPayload
from backend.flow.utils.es.es_context_dataclass import EsActKwargs, EsApplyContext

logger = logging.getLogger("flow")


class EsEnableFlow(EsFlow):
    """
    构建ES启用流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)

    def enable_es_flow(self):
        """
        定义启用ES集群
        :return:
        """
        es_pipeline = Builder(root_id=self.root_id, data=self.get_flow_base_data())
        trans_files = GetFileList(db_type=DBType.Es)
        act_kwargs = EsActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = EsApplyContext.__name__
        act_kwargs.file_list = trans_files.es_enable()

        es_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetEsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        all_ips = self.get_all_node_ips_in_dbmeta()
        act_kwargs.exec_ip = all_ips
        es_pipeline.add_act(
            act_name=_("下发actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        start_acts = []
        for ip in all_ips:
            # 启动进程
            act_kwargs.get_es_payload_func = EsActPayload.get_start_process_payload.__name__
            act_kwargs.exec_ip = ip
            start_act = {
                "act_name": _("启动进程-{}").format(ip),
                "act_component_code": ExecuteEsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            start_acts.append(start_act)
        # 并发执行所有节点
        es_pipeline.add_parallel_acts(acts_list=start_acts)

        # 修改DBMeta
        es_pipeline.add_act(act_name=_("修改Meta"), act_component_code=EsMetaComponent.code, kwargs=asdict(act_kwargs))

        es_pipeline.run_pipeline()
