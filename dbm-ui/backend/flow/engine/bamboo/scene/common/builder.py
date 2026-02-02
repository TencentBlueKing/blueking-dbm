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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Self

from bamboo_engine import api, builder
from bamboo_engine.builder import (
    ConditionalParallelGateway,
    ConvergeGateway,
    Data,
    EmptyEndEvent,
    EmptyStartEvent,
    NodeOutput,
    ParallelGateway,
    Params,
    RewritableNodeOutput,
    ServiceActivity,
    SubProcess,
    Var,
)
from django.utils import translation
from django.utils.translation import gettext as _
from pipeline.eri.runtime import BambooDjangoRuntime

from backend.env import ENABLE_DBM_AI
from backend.flow.engine.exceptions import PipelineError
from backend.flow.models import FlowNode, FlowTree, StateType
from backend.flow.plugins.components.collections.common.check_cluster_alarm_for_ai import (
    CheckClusterAlarmForAIComponent,
)
from backend.flow.plugins.components.collections.common.create_random_job_user import AddTempUserForClusterComponent
from backend.flow.plugins.components.collections.common.drop_random_job_user import DropTempUserForClusterComponent
from backend.flow.plugins.components.collections.common.empty_node import EmptyNodeComponent
from backend.ticket.constants import TicketType

logger = logging.getLogger("json")


@dataclass
class Conditions:
    act_object: Any
    express: str


class Builder(object):
    """
    构建bamboo流程的抽象类，解决开发人员在编排流程的学习成本，减少代码重复率
    规范参数命名(dict属性)：global_data 流程全局参数; trans_data 流程上下文参数；params 活动节点私有参数
    Attributes:
        root_id: 根流程id
        data: 单据所传递数据,默认存入全局参数{global_data}

    """

    def __init__(
        self,
        root_id: str,
        data: Optional[Dict] = None,
        need_random_pass_cluster_ids: list = None,
        need_random_pass_instances: list = None,
    ):
        """
        声明builder类的属性
        @param root_id: 流程id
        @param data: 流程的全局只读参数，默认不是不会同步到各个子流程当中的
        @param need_random_pass_cluster_ids: 是否按照集群维度添加临时账号，目前针对mysql/spider组件场景
        """
        self.root_id = root_id
        self.data = data
        self.need_random_pass_cluster_ids = need_random_pass_cluster_ids
        self.need_random_pass_instances = need_random_pass_instances

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

        # 定义条件网关的上下文参数
        self.node_output_list = []

        # 定义旁路act节点列表
        self.sidecar_acts = []

        # 判断是否添加临时账号的流程逻辑
        if self.need_random_pass_cluster_ids:
            self.create_random_pass_act()

    def add_sidecar_acts(self, sidecar_acts: List):
        """
        支持开发者拓展flow的自定义的单据值守的节点
        @param sidecar_acts: 待加进去的值守节点
        """
        self.sidecar_acts.extend(sidecar_acts)

    def default_sidecar_act(self, check_cluster_ids: List[int]):
        """
        流程默认单据值守节点列表的活动节点
        @param check_cluster_ids：需要监听的集群列表
        """
        self.sidecar_acts.append(
            {
                "act_name": _("分析运行期间的集群风险"),
                "act_component_code": CheckClusterAlarmForAIComponent.code,
                "kwargs": {"cluster_ids": check_cluster_ids},
            },
        )

    def with_sidecar_acts(self, worker_name: str, sidecar_acts: List) -> Self:
        if sidecar_acts and isinstance(sidecar_acts, list) and len(sidecar_acts) > 0:
            sidecar_subpipe = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            sidecar_subpipe.add_parallel_acts(acts_list=sidecar_acts)

            pipe = Builder(
                root_id=self.root_id,
                data=copy.deepcopy(self.data),
                need_random_pass_cluster_ids=self.need_random_pass_cluster_ids,
                need_random_pass_instances=self.need_random_pass_instances,
            )

            pipe.add_parallel_sub_pipeline(
                sub_flow_list=[
                    sidecar_subpipe.build_sub_process(_("旁路子流程")),
                    SubBuilder.from_builder(self).build_sub_process(worker_name),
                ]
            )
            return pipe
        else:
            return self

    def create_random_pass_act(self):
        """
        流程串联添加临时账号的活动节点
        """
        act = self.add_act(
            act_name="create temp job account",
            act_component_code=AddTempUserForClusterComponent.code,
            kwargs={"cluster_ids": self.need_random_pass_cluster_ids, "instances": self.need_random_pass_instances},
        )
        # 提出上下文的映射，这里存在bamboo的 bug
        self.rewritable_node_source_keys = [i for i in self.rewritable_node_source_keys if i["source_act"] != act.id]

    def reduce_random_pass_act(self):
        """
        流程串联回收临时账号的活动节点
        """
        act = self.add_act(
            act_name="drop temp job account",
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
        is_remote_rewritable: bool = False,
        skippable: bool = True,
        retryable: bool = True,
        timeout: int = None,
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
        @param is_remote_rewritable, 目前版本有bug，在有设置上下文的流程中，部分场景加入上下文交互列表会有导致上下文失效，参数设置为了避免出现这个bug，默认False即可
        @param skippable：节点是否可以跳过，默认可跳过
        @param retryable：节点是否可以重试，默认可以重试
        @param timeout：节点超时时间，默认不设置
        """

        act = ServiceActivity(
            name=act_name,
            component_code=act_component_code,
            error_ignorable=error_ignorable,
            skippable=skippable,
            retryable=retryable,
            timeout=timeout,
        )
        kwargs.update({"root_id": self.root_id, "node_id": act.id, "node_name": act_name})
        act.component.inputs.kwargs = Var(type=Var.PLAIN, value=kwargs)
        act.component.inputs.trans_data = Var(type=Var.SPLICE, value="${trans_data}")
        act.component.inputs.global_data = Var(type=Var.SPLICE, value="${global_data}")
        act.component.inputs.splice_payload_var = Var(type=Var.PLAIN, value=splice_payload_var)
        act.component.inputs.write_payload_var = Var(type=Var.PLAIN, value=write_payload_var)

        if not is_remote_rewritable:
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
            if isinstance(act_info, SubProcess):
                acts.append(act_info)
                continue
            act = ServiceActivity(
                name=act_info["act_name"],
                component_code=act_info["act_component_code"],
                error_ignorable=act_info.get("error_ignorable", False),
                retryable=act_info.get("retryable", True),
                skippable=act_info.get("skippable", True),
                timeout=act_info.get("timeout", None),
            )
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

    def add_conditional_subs(self, source_act, conditions: List[Conditions], name: str, conditions_param: str):
        """
        add_conditional_subs：给流程添加条件分支节点，控制执行节点或者子流程
        @param source_act: 控制添加源节点
        @param conditions: 表达式
        @param name: 表达式名称
        @param conditions_param: 表达式变量名称
        """
        real_conditions = {}
        connect_list = []
        for index, info in enumerate(conditions):
            real_conditions[index] = f"${{{conditions_param}}} {info.express}"
            connect_list.append(info.act_object)

        # 添你默认节点
        connect_list.append(
            self.add_act(act_name="default_node", act_component_code=EmptyNodeComponent.code, kwargs={}, extend=False)
        )
        real_conditions[len(connect_list) - 1] = "1==1"

        cpg = ConditionalParallelGateway(
            conditions=real_conditions, name=name, default_condition_outgoing=len(connect_list) - 1
        )
        cg = ConvergeGateway()
        self.pipe = self.pipe.extend(source_act).extend(cpg).connect(*connect_list).to(cpg).converge(cg)

        # 拼接有可能条件网关需要的上下文变量
        self.node_output_list.append({"conditions_param": conditions_param, "source_act_id": source_act.id})

    def _build_sidecar_sub_pipeline(self):
        """
        定义创建旁路子流程的过程
        """
        sidecar_subpipe = SubBuilder(root_id=self.root_id, data=self.data)
        sidecar_subpipe.add_parallel_acts(acts_list=self.sidecar_acts)
        return sidecar_subpipe.build_sub_process(sub_name=_("单据值守"))

    def run_pipeline_with_sidecar(
        self,
        check_ai_monitor_cluster_list: List[int] = None,
        init_trans_data_class: Optional[Any] = None,
        is_drop_random_user: bool = True,
    ):
        """
        定义已注册单据值守的形态，运行pipeline
        @param 传入需要监听的集群列表
        @param check_ai_monitor_cluster_list 传入需要AI智能体监控的集群Id列表，只有环境开启AI才能操作。默认是空
        @param init_trans_data_class: trans_data变量上下文初始化的值，默认""
        @param is_drop_random_user: 控制是否最后回收临时账号，需要跟need_random_pass_cluster_ids不为空才能操作，针对集群下架场景
        """
        if ENABLE_DBM_AI:
            # 需要判断系统环境是否开启AI
            # 接入单据值守框架，整个任务流程会下降成子流程， 同时生成监听单据的子流程
            # 比如： 【开始】-----【任务流程】-----【结束】
            # 接入后：
            #          | --[单据值守] --|
            # 【开始】---|--【任务流程】--|---【结束】
            if not isinstance(check_ai_monitor_cluster_list, list) or len(check_ai_monitor_cluster_list) == 0:
                # 不符合注入单据值守子流程的条件，报错
                raise Exception(
                    _(
                        "不满足启动单据值守子流程的条件，请联系系统管理员： "
                        "参数check_ai_monitor_cluster_list:{}, self.sidecar_acts:{}".format(
                            check_ai_monitor_cluster_list, self.sidecar_acts
                        )
                    )
                )
            # 设置默认的值守节点
            self.default_sidecar_act(check_cluster_ids=check_ai_monitor_cluster_list)

        # 判断值守旁路节点列表是否为空
        if len(self.sidecar_acts) == 0:
            # 不符合注入单据值守子流程的条件，不报错处理，只是进入普通模式启动pipeline
            return self.run_pipeline(
                init_trans_data_class=init_trans_data_class, is_drop_random_user=is_drop_random_user
            )

        # 判断是否回收临时账号的流程逻辑
        if self.need_random_pass_cluster_ids and is_drop_random_user:
            self.reduce_random_pass_act()

        # 将整体任务设置子任务流程
        sub_process = self.build_sub_process(sub_name=_("任务流程"))
        # 添加单据值守子流程
        ai_monitor_sub_process = self._build_sidecar_sub_pipeline()

        # 重新声明一个流程对象
        pipeline = Builder(root_id=self.root_id, data=self.data)
        pipeline.add_parallel_sub_pipeline(sub_flow_list=[ai_monitor_sub_process, sub_process])
        pipeline.run_pipeline(init_trans_data_class=init_trans_data_class)

        return True

    def run_pipeline(
        self,
        init_trans_data_class: Optional[Any] = None,
        is_drop_random_user: bool = True,
    ) -> bool:
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
        # 声明NodeOutput变量
        for i in self.node_output_list:
            self.global_data.inputs[f"${{{i['conditions_param']}}}"] = NodeOutput(
                type=Var.SPLICE, source_act=i["source_act_id"], source_key=f"{i['conditions_param']}"
            )
        # 接入流程中结束节点
        self.pipe.extend(self.end_act)

        # 构建pipeline流程树
        pipeline = builder.build_tree(self.start_act, id=self.root_id, data=self.global_data)

        # 传入参数进行脱敏
        pipeline_copy = copy.deepcopy(pipeline)
        insensitive_data = self.hide_sensitive_data(pipeline_copy)

        # 考虑到有些任务没有单据关联，因此uid一般为root_id，此时创建FlowTree的时候uid应该为null
        # 讲流程信息录入到FLowTree表
        uid = self.data.get("uid") if isinstance(self.data.get("uid"), int) else None
        FlowTree.objects.create(
            uid=uid,
            ticket_type=self.data["ticket_type"],
            root_id=self.root_id,
            tree=insensitive_data,
            bk_biz_id=self.data["bk_biz_id"],
            status=StateType.CREATED,
            created_by=self.data["created_by"],
            db_type=TicketType.get_db_type_by_ticket(self.data["ticket_type"]),
        )
        # 尝试运行流程
        result = api.run_pipeline(runtime=BambooDjangoRuntime(), pipeline=pipeline)

        # 确认流程是否运行正常
        if not result.result:
            raise PipelineError(_("部署bamboo流程任务创建失败: {}").format(result.exc_trace))

        return True

    def hide_sensitive_data(self, copy_data: Optional[Dict]) -> Optional[Dict]:
        """隐藏pipeline中敏感数据"""
        for key, value in list(copy_data.items()):
            if key == "inputs":
                copy_data.pop(key)
                continue
            if isinstance(value, dict):
                self.hide_sensitive_data(value)
        return copy_data

    @staticmethod
    def get_ip_list(ips: list) -> list:
        return [{"bk_cloud_id": 0, "ip": ip} for ip in ips]

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
        # 声明NodeOutput变量
        for i in self.node_output_list:
            sub_data.inputs[f"${{{i['conditions_param']}}}"] = NodeOutput(
                type=Var.SPLICE, source_act=i["source_act_id"], source_key=f"{i['conditions_param']}"
            )
        sub_params = Params({"${trans_data}": Var(type=Var.SPLICE, value="${trans_data}")})
        self.pipe.extend(self.end_act)
        return SubProcess(start=self.start_act, data=sub_data, params=sub_params, name=sub_name)


class SubBuilder(Builder):
    """
    SubBuilder：创建bamboo子流程的对象，活动节点所有的需要参数都是通过流程上下文传递，
    流程上下文只要一个dict参数
    """

    def build_sub_process(self, sub_name) -> Optional[SubProcess]:
        return super().build_sub_process(sub_name=sub_name)

    @classmethod
    def from_builder(cls, b: Builder) -> Self:
        sb = SubBuilder(root_id=b.root_id, data=b.data)
        sb.need_random_pass_cluster_ids = None
        sb.need_random_pass_instances = None

        sb.start_act = b.start_act
        # worker 子流程删除原有的临时账号部分
        if b.need_random_pass_instances or b.need_random_pass_cluster_ids:
            sb.start_act.outgoing = b.start_act.outgoing[0].outgoing

        sb.end_act = b.end_act
        sb.global_data = b.global_data
        sb.pipe = b.pipe
        sb.rewritable_node_source_keys = b.rewritable_node_source_keys
        sb.node_output_list = b.node_output_list
        return sb


class RewritableNode(RewritableNodeOutput):
    """
    重新定义RewritableNode类型的变量，让流程的上下文变量初始化有意义的值
    """

    def __init__(self, source_act, *args, **kwargs):
        super().__init__(source_act, *args, **kwargs)
        self.value = kwargs["value"]
