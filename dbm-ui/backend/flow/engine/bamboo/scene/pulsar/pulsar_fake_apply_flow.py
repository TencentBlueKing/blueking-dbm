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
import copy
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DnsOpType, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.pulsar.pulsar_base_flow import PulsarBaseFlow
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_db_meta import PulsarDBMetaComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_set_token import PulsarSetTokenContextComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_zk_dns_manage import PulsarZkDnsManageComponent
from backend.flow.plugins.components.collections.pulsar.rewrite_pulsar_config import WriteBackPulsarConfigComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.pulsar.consts import PULSAR_ZOOKEEPER_SERVICE_PORT
from backend.flow.utils.pulsar.pulsar_context_dataclass import PulsarActKwargs, PulsarApplyContext, ZkDnsKwargs

logger = logging.getLogger("flow")


class PulsarFakeApplyFlow(PulsarBaseFlow):
    """
    构建Pulsar虚假申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)

        self.data = data

    def fake_deploy_pulsar_flow(self):
        """
        定义部署Pulsar集群
        """
        pulsar_flow_data = self.__get_apply_flow_data(self.data)

        pulsar_pipeline = Builder(root_id=self.root_id, data=pulsar_flow_data)

        # 拼接活动节点需要的私有参数
        act_kwargs = PulsarActKwargs(bk_cloud_id=self.base_flow_data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = PulsarApplyContext.__name__

        # 绑定域名与ZK_IP
        zk_dns_kwargs = ZkDnsKwargs(
            bk_cloud_id=pulsar_flow_data["bk_cloud_id"],
            dns_op_type=DnsOpType.CREATE,
            domain_name=pulsar_flow_data["domain"],
            dns_op_exec_port=PULSAR_ZOOKEEPER_SERVICE_PORT,
            zk_host_map=pulsar_flow_data["zk_host_map"],
        )
        pulsar_pipeline.add_act(
            act_name=_("添加ZK域名"),
            act_component_code=PulsarZkDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(zk_dns_kwargs)},
        )

        # 插入pulsar manager实例信息
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.CREATE,
            db_type=DBType.Pulsar,
            service_type=ManagerServiceType.PULSAR_MANAGER,
            manager_ip=pulsar_flow_data["manager_ip"],
            manager_port=pulsar_flow_data["manager_port"],
        )
        pulsar_pipeline.add_act(
            act_name=_("插入pulsar manager实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        # 写入token
        pulsar_pipeline.add_act(
            act_name=_("写入token"), act_component_code=PulsarSetTokenContextComponent.code, kwargs=asdict(act_kwargs)
        )

        # 写入元数据
        pulsar_pipeline.add_act(
            act_name=_("添加元数据到DBMeta"), act_component_code=PulsarDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 回写配置
        pulsar_pipeline.add_act(
            act_name=_("回写集群配置信息"), act_component_code=WriteBackPulsarConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        pulsar_pipeline.run_pipeline()

    def __get_apply_flow_data(self, data) -> dict:
        flow_data = copy.deepcopy(data)
        # 写入配置 数据保留时间 单位为 分钟
        flow_data["retention_time"] = data["retention_minutes"]

        zk_host_map = self.make_zk_host_map()
        flow_data["zk_host_map"] = zk_host_map
        # 定义zk_host字符串
        flow_data["zk_hosts_str"] = ",".join(zk_host_map.values())
        return flow_data
