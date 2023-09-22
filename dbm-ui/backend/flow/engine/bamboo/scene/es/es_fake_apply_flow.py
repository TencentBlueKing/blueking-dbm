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
from backend.flow.consts import ES_DEFAULT_INSTANCE_NUM, ManagerDefaultPort, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.es.es_flow import EsFlow, get_node_in_ticket_preferred_hot
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.es.es_db_meta import EsMetaComponent
from backend.flow.plugins.components.collections.es.get_es_payload import GetEsActPayloadComponent
from backend.flow.plugins.components.collections.es.get_es_resource import GetEsResourceComponent
from backend.flow.plugins.components.collections.es.rewrite_es_config import WriteBackEsConfigComponent
from backend.flow.utils.es.es_context_dataclass import EsActKwargs, EsApplyContext
from backend.flow.utils.extension_manage import BigdataManagerKwargs

logger = logging.getLogger("flow")


class EsFakeApplyFlow(EsFlow):
    """
    构建ES申请流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.cluster_alias = data.get("cluster_alias")

        # 定义证书文件分发的目标路径
        self.cer_target_path = f"/data/install/"
        self.file_list = ["/tmp/es_cerfiles.tar.gz"]

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["cluster_alias"] = self.cluster_alias
        flow_data["nodes"] = self.nodes
        return flow_data

    def fake_deploy_es_flow(self):
        """
        定义部署ES集群
        :return:
        """

        es_deploy_data = self.__get_flow_data()
        es_pipeline = Builder(root_id=self.root_id, data=es_deploy_data)

        trans_files = GetFileList(db_type=DBType.Es)

        act_kwargs = EsActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = EsApplyContext.__name__
        act_kwargs.file_list = trans_files.es_apply(db_version=self.db_version)
        es_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetEsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        es_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetEsResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 安装kibana
        kibana_ip = get_node_in_ticket_preferred_hot(data=es_deploy_data)

        # 插入kibana实例信息
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.CREATE,
            db_type=DBType.Es,
            service_type=ManagerServiceType.KIBANA,
            manager_ip=kibana_ip,
            manager_port=ManagerDefaultPort.KIBANA,
        )
        es_pipeline.add_act(
            act_name=_("插入kibana实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        # 回写DBConfig
        es_pipeline.add_act(
            act_name=_("回写集群配置信息"), act_component_code=WriteBackEsConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        # 添加到DBMeta并转模块
        es_pipeline.add_act(
            act_name=_("添加到DBMeta"), act_component_code=EsMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        es_pipeline.run_pipeline()
