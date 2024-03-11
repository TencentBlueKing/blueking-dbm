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
import logging
from typing import Any, Dict, Optional

from bamboo_engine import api, builder
from bamboo_engine.builder import (
    ConvergeGateway,
    Data,
    EmptyEndEvent,
    EmptyStartEvent,
    ParallelGateway,
    Params,
    RewritableNodeOutput,
    ServiceActivity,
    SubProcess,
    Var,
)
from django.utils import translation
from django.utils.translation import ugettext as _
from pipeline.eri.runtime import BambooDjangoRuntime

from backend.flow.models import FlowNode, FlowTree, StateType
from backend.flow.plugins.components.collections.common.create_random_job_user import AddTempUserForClusterComponent
from backend.flow.plugins.components.collections.common.drop_random_job_user import DropTempUserForClusterComponent

logger = logging.getLogger("json")


class Builder(object):
    """
    构建bamboo流程的抽象类，解决开发人员在编排流程的学习成本，减少代码重复率
    规范参数命名(dict属性)：global_data 流程全局参数; trans_data 流程上下文参数；params 活动节点私有参数
    Attributes:
        root_id: 根流程id
        data: 单据所传递数据,默认存入全局参数{global_data}

    """

    def __init__(self, root_id: str, data: Optional[Dict] = None, need_random_pass_cluster_ids: list = None):
        """
        声明builder类的属性
        @param root_id: 流程id
        @param data: 流程的全局只读参数，默认不是不会同步到各个子流程当中的
        @param need_random_pass_cluster_ids: 是否按照集群维度添加临时账号，目前针对mysql/spider组件场景
        """
        self.root_id = root_id
        self.data = data
        self.need_random_pass_cluster_ids = need_random_pass_cluster_ids
        self.start_act = EmptyStartEvent()
        self.end_act = EmptyEndEvent()
        if not self.data:
            self.data = {}

        # 添加当前系统语言到到全局参数中
        self.data["blueking_language"] = translation.get_language()

        # 下传job的root_id
        self.data["job_root_id"] = self.root_id

        # 定义流程数据全局参数global_data, dict属性
        self.global_data = Data()
        self.global_data.inputs["${global_data}"] = Var(type=Var.PLAIN, value=self.data)
        self.pipe = self.start_act

        # 定义流程数据上下文参数trans_data
        self.rewritable_node_source_keys = []

        # 判断是否添加临时账号的流程逻辑
        if self.need_random_pass_cluster_ids:
            self.create_random_pass_act()

    def create_random_pass_act(self):
        """
        流程串联添加临时账号的活动节点
        """
        act = self.add_act(
            act_name="create job user",
            act_component_code=AddTempUserForClusterComponent.code,
            kwargs={"cluster_ids": self.need_random_pass_cluster_ids},
        )
        # 提出上下文的映射，这里存在bamboo的 bug
        self.rewritable_node_source_keys = [i for i in self.rewritable_node_source_keys if i["source_act"] != act.id]

    def reduce_random_pass_act(self):
        """
        流程串联回收临时账号的活动节点
        """
        act = self.add_act(
            act_name="reduce job user",
            act_component_code=DropTempUserForClusterComponent.code,
            kwargs={"cluster_ids": self.need_random_pass_cluster_ids},
        )
        # 提出上下文的映射，这里存在bamboo的 bug
        self.rewritable_node_source_keys = [i for i in self.rewritable_node_source_keys if i["source_act"] != act.id]

    def add_act(
        self,
        act_name: str,
        act_component_code: str,
        kwargs: dict,
        splice_payload_var: str = None,
        write_payload_var: str = None,
        error_ignorable: bool = False,
        extend: bool = True,
    ):
        """
        add_act 方法：为流程加入活动节点，并加入流程数字典
        @param act_name: 自定义活动节点名称，最好定义可读性高的名称，方便前端查询
        @param act_component_code: 指定的活动节点的原子名称，原子需要事先创建完成，并且按照规范引入对应参数
        @param kwargs: 传递活动节点的私有变量, 内部元素为dict, 每个act节点只能定义一个私有内部变量
        @param splice_payload_var: 控制节点 拼接 上下文变量名称到act的payload，默认不拼接
        @param write_payload_var：节点是否写入上下文变量到trans_data类的变量名称中，默认不写
        todo  后续这里废弃splice_payload_var 这个变量，通过传入上下文trans_data文本到 act的payload， 然后用户按需拼接
        todo  write_payload_var 变量名称变更为 write_context_var 这样表达清晰点
        @param error_ignorable：节点是否忽略错误继续往下执行
        @param extend: extend
        """

        act = ServiceActivity(name=act_name, component_code=act_component_code, error_ignorable=error_ignorable)
        kwargs.update({"root_id": self.root_id, "node_id": act.id, "node_name": act_name})
        act.component.inputs.kwargs = Var(type=Var.PLAIN, value=kwargs)
        act.component.inputs.trans_data = Var(type=Var.SPLICE, value="${trans_data}")
        act.component.inputs.global_data = Var(type=Var.SPLICE, value="${global_data}")
        act.component.inputs.splice_payload_var = Var(type=Var.PLAIN, value=splice_payload_var)
        act.component.inputs.write_payload_var = Var(type=Var.PLAIN, value=write_payload_var)

        self.rewritable_node_source_keys.append({"source_act": act.id, "source_key": "trans_data"})

        FlowNode.objects.create(uid=self.data.get("uid"), root_id=self.root_id, node_id=act.id)
        if extend:
            self.pipe = self.pipe.extend(act)
        return act

    def add_parallel_acts(self, acts_list: list):
        """
        add_parallel_acts 方法：为流程加入并行网关活动节点，并加入流程数字典
        @param：acts_list : 定义并行节点中每个节点的添加内容，格式dict。每个活动内容参数参考add_act定义
        """
        pg = ParallelGateway()
        cg = ConvergeGateway()
        acts = []
        flow_node_list = []

        # 增加对传入的acts_list做合法判断
        if not isinstance(acts_list, list) or len(acts_list) == 0:
            raise Exception(_("传入的acts_list参数不合法，请检测"))

        for act_info in acts_list:
            if type(act_info) == SubProcess:
                acts.append(act_info)
                continue
            act = ServiceActivity(name=act_info["act_name"], component_code=act_info["act_component_code"])
            act_info["kwargs"].update({"root_id": self.root_id, "node_id": act.id, "node_name": act_info["act_name"]})
            act.component.inputs.kwargs = Var(type=Var.PLAIN, value=act_info["kwargs"])
            act.component.inputs.trans_data = Var(type=Var.SPLICE, value="${trans_data}")
            act.component.inputs.global_data = Var(type=Var.SPLICE, value="${global_data}")
            act.component.inputs.splice_payload_var = Var(
                type=Var.PLAIN, value=act_info.get("splice_payload_var", False)
            )
            act.component.inputs.write_payload_var = Var(
                type=Var.PLAIN, value=act_info.get("write_payload_var", False)
            )

            self.rewritable_node_source_keys.append({"source_act": act.id, "source_key": "trans_data"})

            flow_node_list.append(FlowNode(uid=self.data["uid"], root_id=self.root_id, node_id=act.id))
            acts.append(act)

        FlowNode.objects.bulk_create(flow_node_list)
        self.pipe = self.pipe.extend(pg).connect(*acts).to(pg).converge(cg)

    def add_sub_pipeline(self, sub_flow):
        """
        add_sub_pipeline 方法： 为主流程加入子流程
        @param sub_flow: 子流程
        """

        self.pipe = self.pipe.extend(sub_flow)
        # return self

    def add_parallel_sub_pipeline(self, sub_flow_list: list):
        """
        add_parallel_sub_pipeline 方法： 为主流程并发加入子流程
        @param sub_flow_list: 子流程列表
        """
        # 增加对传入的acts_list做合法判断
        if not isinstance(sub_flow_list, list) or len(sub_flow_list) == 0:
            raise Exception(_("传入的sub_flow_list参数不合法，请检测"))

        pg = ParallelGateway()
        cg = ConvergeGateway()
        self.pipe = self.pipe.extend(pg).connect(*sub_flow_list).to(pg).converge(cg)

    def run_pipeline(self, init_trans_data_class: Optional[Any] = None, is_drop_random_user: bool = True) -> bool:
        """
        开始运行 pipeline
        @param init_trans_data_class: trans_data变量上下文初始化的值，默认""
        @param is_drop_random_user: 控制是否最后回收临时账号，需要跟need_random_pass_cluster_ids不为空才能操作，针对集群下架场景
        """

        # 判断是否回收临时账号的流程逻辑
        if self.need_random_pass_cluster_ids and is_drop_random_user:
            self.reduce_random_pass_act()

        # 拼接流程的RewritableNodeOutput属性
        self.global_data.inputs["${trans_data}"] = RewritableNode(
            source_act=self.rewritable_node_source_keys, type=Var.SPLICE, value=init_trans_data_class
        )
        self.pipe.extend(self.end_act)
        pipeline = builder.build_tree(self.start_act, id=self.root_id, data=self.global_data)
        pipeline_copy = copy.deepcopy(pipeline)
        insensitive_data = self.hide_sensitive_data(pipeline_copy)
        # 考虑到有些任务没有单据关联，因此uid一般为root_id，此时创建FlowTree的时候uid应该为null
        uid = self.data.get("uid") if isinstance(self.data.get("uid"), int) else None
        FlowTree.objects.create(
            uid=uid,
            ticket_type=self.data["ticket_type"],
            root_id=self.root_id,
            tree=insensitive_data,
            bk_biz_id=self.data["bk_biz_id"],
            status=StateType.CREATED,
            created_by=self.data["created_by"],
        )

        if not api.run_pipeline(runtime=BambooDjangoRuntime(), pipeline=pipeline).result:
            logger.error(_("部署bamboo流程任务创建失败，任务结束"))
            return False

        return True

    def hide_sensitive_data(self, copy_data: Optional[Dict]) -> Optional[Dict]:
        """隐藏pipeline中敏感数据"""
        for key, value in list(copy_data.items()):
            if key == "inputs":
                copy_data.pop(key)
                continue
            if type(value) == dict:
                self.hide_sensitive_data(value)
        return copy_data

    @staticmethod
    def get_ip_list(ips: list) -> list:
        return [{"bk_cloud_id": 0, "ip": ip} for ip in ips]


class SubBuilder(Builder):
    """
    SubBuilder：创建bamboo子流程的对象，活动节点所有的需要参数都是通过流程上下文传递，
    流程上下文只要一个dict参数
    """

    def build_sub_process(self, sub_name) -> Optional[SubProcess]:
        """
        build_sub_bamboo方法: 建立子流程树
        """
        sub_data = Data()
        # 拼接流程的RewritableNode属性
        sub_data.inputs["${global_data}"] = Var(type=Var.PLAIN, value=self.data)
        sub_data.inputs["${trans_data}"] = RewritableNode(
            source_act=self.rewritable_node_source_keys, type=Var.SPLICE, value=None
        )
        # sub_data.inputs['${trans_data}'] = DataInput(type=Var.SPLICE, value='${trans_data}')
        sub_params = Params({"${trans_data}": Var(type=Var.SPLICE, value="${trans_data}")})
        self.pipe.extend(self.end_act)
        return SubProcess(start=self.start_act, data=sub_data, params=sub_params, name=sub_name)


class RewritableNode(RewritableNodeOutput):
    """
    重新定义RewritableNode类型的变量，让流程的上下文变量初始化有意义的值
    """

    def __init__(self, source_act, *args, **kwargs):
        super().__init__(source_act, *args, **kwargs)
        self.value = kwargs["value"]
