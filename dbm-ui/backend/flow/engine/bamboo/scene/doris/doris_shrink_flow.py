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
from backend.db_meta.enums import InstanceRole
from backend.flow.consts import DnsOpType, DorisRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.doris.doris_base_flow import (
    DorisBaseFlow,
    be_exists_in_ticket,
    fe_exists_in_ticket,
    get_all_node_ips_in_ticket,
    get_node_ips_in_ticket_by_role,
)
from backend.flow.engine.bamboo.scene.doris.exceptions import (
    FollowerScaleUpUnsupportedException,
    RoleMachineCountException,
    RoleMachineCountMustException,
)
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.doris_dns_manage import DorisDnsManageComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.doris.get_doris_resource import GetDorisResourceComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.utils.doris.consts import DORIS_FOLLOWER_MUST_COUNT, DORIS_OBSERVER_NOT_COUNT
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DnsKwargs, DorisActKwargs, DorisApplyContext

logger = logging.getLogger("flow")


class DorisShrinkFlow(DorisBaseFlow):
    """
    Doris缩容流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["nodes"] = self.nodes
        follower_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_FOLLOWER)
        # 增加follower 数量 判断(不判断严格等于，兼容替换场景)
        if len(follower_ips) < DORIS_FOLLOWER_MUST_COUNT:
            logger.error("get follower ips from dbmeta, count is {}, invalid".format(len(follower_ips)))
            raise RoleMachineCountMustException(
                doris_role=DorisRoleEnum.FOLLOWER, must_count=DORIS_FOLLOWER_MUST_COUNT
            )

        # 随机选取follower 作为添加元数据的操作IP
        flow_data["master_fe_ip"] = follower_ips[0]

        return flow_data

    def shrink_doris_flow(self):
        """
        定义缩容Doris集群
        :return:
        """
        shrink_data = self.__get_flow_data()
        # 检查 缩容表单角色机器数量是否合法
        self.check_shrink_role_ip_count(shrink_data)

        doris_pipeline = Builder(root_id=self.root_id, data=shrink_data)

        trans_files = GetFileList(db_type=DBType.Doris)

        act_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__
        act_kwargs.file_list = trans_files.doris_actuator()

        doris_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetDorisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        doris_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetDorisResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 更新dbactor介质包
        act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=shrink_data)
        doris_pipeline.add_act(
            act_name=_("下发DORIS介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 更新域名
        dns_kwargs = DnsKwargs(
            bk_cloud_id=shrink_data["bk_cloud_id"],
            dns_op_type=DnsOpType.UPDATE,
            domain_name=self.domain,
            dns_op_exec_port=self.http_port,
        )
        doris_pipeline.add_act(
            act_name=_("更新域名"),
            act_component_code=DorisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 缩容FE节点子流程
        if fe_exists_in_ticket(data=shrink_data):
            del_fe_pipeline = self.build_del_fe_sub_flow(data=shrink_data)
            doris_pipeline.add_sub_pipeline(del_fe_pipeline.build_sub_process(sub_name=_("缩容管理节点FE")))

        # 缩容BE节点子流程
        if be_exists_in_ticket(data=shrink_data):
            del_be_pipeline = self.build_del_be_sub_flow(data=shrink_data)
            doris_pipeline.add_sub_pipeline(del_be_pipeline.build_sub_process(sub_name=_("缩容数据节点BE")))

        shrink_ips = get_all_node_ips_in_ticket(shrink_data)
        shrink_ip_acts = []
        for ip in shrink_ips:
            # 节点清理
            act_kwargs.get_doris_payload_func = DorisActPayload.get_clean_data_payload.__name__
            act_kwargs.exec_ip = ip
            act = {
                "act_name": _("Doris集群节点清理-{}").format(ip),
                "act_component_code": ExecuteDorisActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            shrink_ip_acts.append(act)

        doris_pipeline.add_parallel_acts(acts_list=shrink_ip_acts)
        # 添加到DBMeta并转模块
        doris_pipeline.add_act(
            act_name=_("更新DBMeta"), act_component_code=DorisMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        doris_pipeline.run_pipeline()

    def check_shrink_role_ip_count(self, data: dict):
        # 扩容无需检查数据节点数量

        # 检查 follower 数量
        follower_count = len(get_node_ips_in_ticket_by_role(data, DorisRoleEnum.FOLLOWER))
        if follower_count > 0:
            logger.error(_("DorisFollower不支持缩容,当前选择缩容机器数量为{}".format(follower_count)))
            raise FollowerScaleUpUnsupportedException(machine_count=follower_count)

        # 检查 observer 数量
        del_observer_cnt = len(get_node_ips_in_ticket_by_role(data, DorisRoleEnum.OBSERVER))
        former_observer_cnt = len(self.get_role_ips_in_dbmeta(InstanceRole.DORIS_OBSERVER))
        if former_observer_cnt - del_observer_cnt == DORIS_OBSERVER_NOT_COUNT:
            logger.error(_("DorisObserver主机数不能为{}".format(DORIS_OBSERVER_NOT_COUNT)))
            raise RoleMachineCountException(doris_role=DorisRoleEnum.OBSERVER, machine_count=DORIS_OBSERVER_NOT_COUNT)
