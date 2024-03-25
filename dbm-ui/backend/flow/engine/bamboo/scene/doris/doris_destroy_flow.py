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
from backend.flow.consts import DnsOpType, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.doris.doris_base_flow import DorisBaseFlow
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.doris_dns_manage import DorisDnsManageComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.doris.trans_files import TransFileComponent
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DnsKwargs, DorisActKwargs, DorisApplyContext
from backend.flow.utils.extension_manage import BigdataManagerKwargs

logger = logging.getLogger("flow")


class DorisDestroyFlow(DorisBaseFlow):
    """
    构建Doris集群删除流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.root_id = root_id
        self.data = data

    def destroy_doris_flow(self):
        """
        删除Doris集群
        """
        # Builder 传参 为封装好角色IP的数据结构
        destroy_data = self.get_flow_base_data()
        doris_pipeline = Builder(root_id=self.root_id, data=destroy_data)
        trans_files = GetFileList(db_type=DBType.Doris)

        # 拼接活动节点需要的私有参数
        act_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__
        act_kwargs.file_list = trans_files.doris_actuator()

        doris_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetDorisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        all_ips = self.get_all_node_ips_in_dbmeta()
        act_kwargs.exec_ip = all_ips
        doris_pipeline.add_act(
            act_name=_("下发doris actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        all_ip_acts = []
        for ip in all_ips:
            # 节点清理
            act_kwargs.get_doris_payload_func = DorisActPayload.get_clean_data_payload.__name__
            act_kwargs.exec_ip = ip
            act = {
                "act_name": _("Doris集群节点清理-{}").format(ip),
                "act_component_code": ExecuteDorisActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            all_ip_acts.append(act)

        doris_pipeline.add_parallel_acts(acts_list=all_ip_acts)

        # 清理域名
        dns_kwargs = DnsKwargs(bk_cloud_id=self.bk_cloud_id, dns_op_type=DnsOpType.CLUSTER_DELETE)
        doris_pipeline.add_act(
            act_name=_("删除域名"),
            act_component_code=DorisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 清理haproxy
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.DELETE,
            db_type=DBType.Doris,
            service_type=ManagerServiceType.DORIS_WEB_UI,
        )
        doris_pipeline.add_act(
            act_name=_("删除PULSAR_MANAGER实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )
        # 修改DBMeta + 将机器挪到空闲机模块
        doris_pipeline.add_act(
            act_name=_("修改Meta"), act_component_code=DorisMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        doris_pipeline.run_pipeline()
