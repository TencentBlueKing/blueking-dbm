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
from backend.flow.consts import DorisRoleEnum, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.rewrite_doris_config import WriteBackDorisConfigComponent
from backend.flow.utils.doris.doris_context_dataclass import DorisActKwargs, DorisApplyContext
from backend.flow.utils.extension_manage import BigdataManagerKwargs

logger = logging.getLogger("flow")


class DorisFakeApplyFlow(object):
    """
    构建doris虚拟申请流程类，用于迁移集群/IP等元数据
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
         @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        # 写入cluster_type，转模块会使用
        self.data["cluster_type"] = ClusterType.Doris.value
        # 设置master_fe_ip，用于WebUI实例信息插入
        if not self.data.get("master_fe_ip"):
            followers = self.data["nodes"].get(DorisRoleEnum.FOLLOWER, [])
            if not followers:
                raise ValueError(_("nodes.follower 不能为空，无法确定 master_fe_ip"))
            self.data["master_fe_ip"] = followers[0]["ip"]
        # 若未提供 admin_password / root_password，使用 password 作为默认值
        # 回写密码服务(WriteBackDorisConfigService)会读取这两个字段
        if not self.data.get("admin_password"):
            self.data["admin_password"] = self.data["password"]
        if not self.data.get("root_password"):
            self.data["root_password"] = self.data["password"]

    def fake_deploy_doris_flow(self):
        """
        定义部署doris集群参数
        """
        # Builder 传参 为封装好角色IP的数据结构
        doris_pipeline = Builder(root_id=self.root_id, data=self.data)

        # 拼接活动节点需要的私有参数
        act_kwargs = DorisActKwargs(bk_cloud_id=self.data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

        # 更新DBMeta元信息
        doris_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=DorisMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 回写集群配置信息
        doris_pipeline.add_act(
            act_name=_("回写集群配置信息"), act_component_code=WriteBackDorisConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        # 插入Doris WebUI实例信息
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.CREATE,
            db_type=DBType.Doris,
            service_type=ManagerServiceType.DORIS_WEB_UI,
            manager_ip=self.data["master_fe_ip"],
            manager_port=self.data["http_port"],
        )
        doris_pipeline.add_act(
            act_name=_("插入Doris WebUI实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        doris_pipeline.run_pipeline()
