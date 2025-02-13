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
import itertools
import json
import logging
from collections import defaultdict
from typing import Dict, List

from django.db import transaction
from django.db.models import Prefetch, Q
from django.forms import model_to_dict
from django.utils.translation import ugettext as _

from backend import env
from backend.components import ItsmApi
from backend.configuration.constants import PLAT_BIZ_ID, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.models import Cluster
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.common.base import fetch_cluster_ids, fetch_instance_ids
from backend.ticket.constants import (
    FLOW_FINISHED_STATUS,
    RUNNING_FLOW__TICKET_STATUS,
    TODO_RUNNING_STATUS,
    FlowType,
    FlowTypeConfig,
    OperateNodeActionType,
    TicketFlowStatus,
    TicketStatus,
    TicketType,
    TodoType,
)
from backend.ticket.exceptions import TicketFlowsConfigException
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Flow, Ticket, TicketFlowsConfig, Todo
from backend.ticket.todos import BaseTodoContext, TodoActionType, TodoActorFactory
from backend.ticket.todos.itsm_todo import ItsmTodoContext

logger = logging.getLogger("root")


class TicketHandler:
    @classmethod
    def add_related_object(cls, ticket_data: List[Dict]) -> List[Dict]:
        """
        补充单据的关联对象
        - 针对集群操作，则补充集群域名
        - 针对实例操作，则补充集群 IP:PORT
        - ...
        """
        ticket_ids = [ticket["id"] for ticket in ticket_data]
        # 单据关联对象映射表
        ticket_id_obj_ids_map: Dict[int, Dict[str, List[int]]] = {}

        # 这里的快照数据需要以单据维度分割，因为不同单据的集群信息可能不同
        snapshot_cluster_domain_map = defaultdict(dict)
        snapshot_instance_ip_port_map = defaultdict(dict)

        # 查询单据对应的集群列表、实例列表等
        for ticket in Ticket.objects.filter(id__in=ticket_ids):
            clusters = ticket.details.get("clusters", {})
            snapshot_cluster_domain_map[ticket.id].update(
                {int(cluster_id): info["immute_domain"] for cluster_id, info in clusters.items()}
            )

            instances = ticket.details.get("instances", {})
            if isinstance(instances, dict):
                snapshot_instance_ip_port_map[ticket.id].update(
                    {int(inst_id): info["instance"] for inst_id, info in instances.items()}
                )

            ticket_id_obj_ids_map[ticket.id] = {
                "cluster_ids": fetch_cluster_ids(ticket.details),
                "instance_ids": fetch_instance_ids(ticket.details),
            }

        # 补充关联对象信息
        for item in ticket_data:
            ticket_id = item["id"]
            cluster_ids = ticket_id_obj_ids_map[ticket_id]["cluster_ids"]
            instance_ids = ticket_id_obj_ids_map[ticket_id]["instance_ids"]

            if cluster_ids:
                item["related_object"] = {
                    "title": _("集群"),
                    "objects": [
                        snapshot_cluster_domain_map[ticket_id][cluster_id]
                        for cluster_id in cluster_ids
                        if cluster_id in snapshot_cluster_domain_map[ticket_id]
                    ],
                }

            if instance_ids:
                item["related_object"] = {
                    "title": _("实例"),
                    "objects": [
                        snapshot_instance_ip_port_map[ticket_id][inst_id]
                        for inst_id in instance_ids
                        if inst_id in snapshot_instance_ip_port_map[ticket_id]
                    ],
                }

        return ticket_data

    @classmethod
    def fast_create_cloud_component_method(cls, bk_biz_id, bk_cloud_id, ips, user="admin"):
        # 默认agent城市为1(sg环境的集群默认逻辑城市ID都是1)
        default_agent_city_id: int = 1
        # gm异地部署即可
        default_gm_city_ids: tuple = (0, 1)

        def _get_base_info(host):
            return {
                "bk_host_id": host["host_id"],
                "ip": host["ip"],
                "bk_cloud_id": host["cloud_id"],
            }

        # 查询的机器的信息
        host_list = [{"cloud_id": bk_cloud_id, "ip": ip} for ip in ips]
        host_infos = HostHandler.details(scope_list=[{"bk_biz_id": bk_biz_id}], host_list=host_list)

        # 构造nginx部署信息
        nginx_host_infos = [
            {
                "bk_outer_ip": host_infos[1].get("bk_host_outerip") or host_infos[1]["ip"],
                **_get_base_info(host_infos[1]),
            }
        ]
        # 构造dns的部署信息
        dns_host_infos = [{**_get_base_info(host_infos[0])}, {**_get_base_info(host_infos[1])}]
        # 构造drs的部署信息
        drs_host_infos = [
            {**_get_base_info(host_infos[0]), "drs_port": env.DRS_PORT},
            {**_get_base_info(host_infos[1]), "drs_port": env.DRS_PORT},
        ]
        # 构造agent的部署信息
        agent_host_infos = [
            {
                **_get_base_info(host_infos[0]),
                "bk_city_code": host_infos[0].get("bk_idc_id") or default_agent_city_id,
                "bk_city_name": host_infos[0].get("bk_idc_city_name", ""),
            }
        ]
        # 构造gm的部署信息
        gm_host_infos = [
            {
                **_get_base_info(host_infos[0]),
                "bk_city_code": host_infos[0].get("bk_idc_id") or default_gm_city_ids[0],
                "bk_city_name": host_infos[0].get("bk_idc_city_name", ""),
            },
            {
                **_get_base_info(host_infos[1]),
                "bk_city_code": host_infos[1].get("bk_idc_id") or default_gm_city_ids[1],
                "bk_city_name": host_infos[1].get("bk_idc_city_name", ""),
            },
        ]

        # 创建单据进行部署
        details = {
            "bk_cloud_id": bk_cloud_id,
            "dns": {"host_infos": dns_host_infos},
            "nginx": {"host_infos": nginx_host_infos},
            "drs": {"host_infos": drs_host_infos},
            "dbha": {"gm": gm_host_infos, "agent": agent_host_infos},
        }
        Ticket.create_ticket(
            ticket_type=TicketType.CLOUD_SERVICE_APPLY,
            creator=user,
            bk_biz_id=bk_biz_id,
            remark=_("云区域组件快速部署单据"),
            details=details,
        )

    @classmethod
    def ticket_flow_config_init(cls):
        """初始化单据配置"""
        exist_flow_configs = TicketFlowsConfig.objects.all()
        exist_ticket_types = [config.ticket_type for config in exist_flow_configs]

        # 删除不存在的单据流程
        deleted_configs = [
            config.id for config in exist_flow_configs if config.ticket_type not in BuilderFactory.registry.keys()
        ]
        TicketFlowsConfig.objects.filter(id__in=deleted_configs).delete()

        # 创建新单据类型流程
        created_configs = [
            TicketFlowsConfig(
                bk_biz_id=PLAT_BIZ_ID,
                creator="admin",
                updater="admin",
                ticket_type=ticket_type,
                group=flow_class.group,
                editable=flow_class.editable,
                configs={
                    # 单据流程配置
                    FlowTypeConfig.NEED_MANUAL_CONFIRM: flow_class.default_need_manual_confirm,
                    FlowTypeConfig.NEED_ITSM: flow_class.default_need_itsm,
                    # 单据过期配置
                    FlowTypeConfig.EXPIRE_CONFIG: flow_class.default_expire_config,
                },
            )
            for ticket_type, flow_class in BuilderFactory.registry.items()
            if ticket_type not in exist_ticket_types
        ]
        TicketFlowsConfig.objects.bulk_create(created_configs)

    @classmethod
    def get_itsm_fields(cls, ticket_type):
        """获取单据审批需要的itsm字段"""
        # 根据单据类型决定审批模式
        approve_mode = str(TicketType.get_approve_mode_by_ticket(ticket_type))
        # 预先获取审批接口的field的审批意见和备注的key
        approval_key = SystemSettings.get_setting_value(key=SystemSettingsEnum.ITSM_APPROVAL_KEY)
        remark_key = SystemSettings.get_setting_value(key=SystemSettingsEnum.ITSM_REMARK_KEY)
        return approval_key[approve_mode], remark_key[approve_mode]

    @classmethod
    def operate_itsm_ticket(cls, ticket_id, action, operator, **kwargs):
        """操作itsm中的单据"""
        flow = Flow.objects.get(ticket_id=ticket_id, flow_type="BK_ITSM")
        sn = flow.flow_obj_id
        itsm_info = ItsmApi.get_ticket_info(params={"sn": sn})

        # 当前没有正在进行的步骤，退出
        if not itsm_info["current_steps"]:
            return
        state_id = itsm_info["current_steps"][0]["state_id"]

        act_msg_tpl = _("{}对单据{}操作: {}").format(operator, ticket_id, OperateNodeActionType.get_choice_label(action))
        act_msg = kwargs.get("action_message") or act_msg_tpl

        # 审批单据
        params = {
            "sn": sn,
            "action_message": act_msg,
            "action_type": action,
            "operator": operator,
            "bk_username": operator,
        }
        if action == OperateNodeActionType.TRANSITION:
            is_approved = kwargs["is_approved"]
            itsm_fields = cls.get_itsm_fields(flow.ticket.ticket_type)
            fields = [
                {"key": itsm_fields[0], "value": json.dumps(is_approved)},
                {"key": itsm_fields[1], "value": act_msg},
            ]
            params.update(state_id=state_id, fields=fields)
            ItsmApi.operate_node(params)
        # 终止/撤销单据
        elif action in [OperateNodeActionType.TERMINATE, OperateNodeActionType.WITHDRAW]:
            ItsmApi.operate_ticket(params)
        # 转单派给他人
        elif action == OperateNodeActionType.DELIVER:
            processors = kwargs["processors"]
            params.update(state_id=state_id, processors_type="PERSON", processors=processors)
            ItsmApi.operate_node(params)

        return sn

    @classmethod
    def operate_flow(cls, ticket_id, flow_id, func, *args, **kwargs):
        """进行flow操作，目前支持重试和终止"""
        ticket = Ticket.objects.get(pk=ticket_id)
        flow_instance = Flow.objects.get(ticket=ticket, id=flow_id)
        flow_cls = TicketFlowManager(ticket=ticket).get_ticket_flow_cls(flow_instance.flow_type)(flow_instance)
        getattr(flow_cls, func)(*args, **kwargs)

    @classmethod
    def revoke_ticket(cls, ticket_ids, operator):
        """
        终止单据
        - 单据状态本身设置为 终止
        - 找到第一个非成功的flow 设置为终止
        - 如果有关联正在运行的todos，也设置为终止
        """
        # 查询ticket，关联正在运行的flows(这里定义的"运行"指的就是非成功/终止/撤销)
        finished_status = [*FLOW_FINISHED_STATUS, TicketFlowStatus.TERMINATED, TicketFlowStatus.REVOKED]
        running_flows = Flow.objects.filter(ticket__in=ticket_ids).exclude(status__in=finished_status)
        tickets = Ticket.objects.prefetch_related(
            Prefetch("flows", queryset=running_flows, to_attr="running_flows")
        ).filter(id__in=ticket_ids)

        # 对每个单据进行终止
        for ticket in tickets:
            if not ticket.running_flows:
                continue

            first_running_flow = ticket.running_flows[0]
            cls.operate_flow(ticket.id, first_running_flow.id, func="revoke", operator=operator)
            logger.info(_("操作人[{}]终止了单据[{}]").format(operator, ticket.id))

    @classmethod
    def batch_process_todo(cls, user, action, operations):
        """
        批量操作todo
        @param user 用户
        @param action 动作
        @param operations: todo列表，每个item包含todo id和params
        """
        from backend.ticket.serializers import TodoSerializer

        results = []
        for operation in operations:
            todo_id, params = operation["todo_id"], operation["params"]
            todo = Todo.objects.get(id=todo_id)
            if action == TodoActionType.DELIVER:
                TodoActorFactory.actor(todo).deliver(user, action, params)
            else:
                TodoActorFactory.actor(todo).process(user, action, params)
            results.append(todo)
        return TodoSerializer(results, many=True).data

    @classmethod
    def batch_process_ticket(cls, username, action, ticket_ids, params):
        """
        批量操作单据的todo
        @param username 用户
        @param action 动作
        @param ticket_ids 单据ID列表
        @param params 操作额外参数
        """

        tickets = Ticket.objects.prefetch_related("todo_of_ticket").filter(id__in=ticket_ids)
        # 找到单据第一个代办（排除INNER_APPROVE，这是任务流程的人工确认节点产生的，不允许在单据维度操作）
        running_todos = [
            ticket.todo_of_ticket.exclude(type=TodoType.INNER_APPROVE).filter(status__in=TODO_RUNNING_STATUS).first()
            for ticket in tickets
        ]
        operations = [{"todo_id": todo.id, "params": params} for todo in running_todos if todo]
        return TicketHandler.batch_process_todo(user=username, action=action, operations=operations)

    @classmethod
    def create_ticket_flow_config(cls, bk_biz_id, cluster_ids, ticket_types, configs, operator):
        """
        创建单据流程
        @param bk_biz_id: 业务ID，为0表示平台业务
        @param cluster_ids: 集群ID列表，表示规则生效的集群范围
        @param ticket_types: 单据类型列表
        @param configs: 流程配置
        @param operator: 创建者
        """

        def check_create_config(ticket_type):
            if not bk_biz_id:
                raise TicketFlowsConfigException(_("不允许新增平台级别的流程设置"))

            global_config = TicketFlowsConfig.objects.get(bk_biz_id=0, ticket_type=ticket_type)
            biz_configs = TicketFlowsConfig.objects.filter(bk_biz_id=bk_biz_id, ticket_type=ticket_type)

            if configs["need_manual_confirm"] != global_config.configs["need_manual_confirm"]:
                raise TicketFlowsConfigException(_("业务级别不允许编辑[人工确认]设置"))

            biz_cfg = biz_configs.filter(cluster_ids=[]).first()
            cluster_cfg = biz_configs.exclude(cluster_ids=[]).first()

            # 不允许创建相同维度的流程
            if biz_cfg and not cluster_ids:
                raise TicketFlowsConfigException(_("业务[{}]已存在{}的流程配置").format(bk_biz_id, ticket_type))
            if cluster_cfg and cluster_ids:
                raise TicketFlowsConfigException(_("业务[{}]已存在{}的集群流程配置").format(bk_biz_id, ticket_type))
            # 新创建的流程，不能和生效流程的配置冲突
            effect_flows = [biz_cfg or global_config, cluster_cfg]
            for ef in effect_flows:
                if ef and ef.configs["need_itsm"] == configs["need_itsm"]:
                    raise TicketFlowsConfigException(_("业务[{}]已存在{}的相同范围配置").format(bk_biz_id, ticket_type))

        flows_config_list = []
        for type in ticket_types:
            # 校验创建单据流程配置是否合理
            check_create_config(type)
            # 创建流程规则
            group = TicketType.get_db_type_by_ticket(type)
            flows_config = TicketFlowsConfig(
                bk_biz_id=bk_biz_id,
                cluster_ids=cluster_ids,
                ticket_type=type,
                group=group,
                configs=configs,
                creator=operator,
                updater=operator,
            )
            flows_config_list.append(flows_config)

        TicketFlowsConfig.objects.bulk_create(flows_config_list)

    @classmethod
    def update_ticket_flow_config(cls, bk_biz_id, cluster_ids, ticket_types, configs, config_ids, operator):
        """
        更新单据流程
        @param bk_biz_id: 业务ID，为0表示平台业务
        @param cluster_ids: 集群ID列表，表示规则生效的集群范围
        @param ticket_types: 单据类型列表
        @param configs: 流程配置
        @param config_ids: 更新的流程ID列表
        @param operator: 更新人
        """
        cluster_ids = cluster_ids or []
        config_ids = config_ids or []

        config_qs = TicketFlowsConfig.objects.filter(bk_biz_id=bk_biz_id, ticket_type__in=ticket_types)
        # 平台全局配置直接更新
        if not bk_biz_id:
            config_qs.update(configs=configs)
            return

        # 业务级别先删除，再创建，可以复用校验流程
        with transaction.atomic():
            config_qs.filter(id__in=config_ids).delete()
            cls.create_ticket_flow_config(bk_biz_id, cluster_ids, ticket_types, configs, operator)

    @classmethod
    def query_ticket_flows_describe(cls, bk_biz_id, db_type, ticket_types=None):
        # 根据条件过滤单据配置
        config_filter = Q(bk_biz_id__in=[bk_biz_id, PLAT_BIZ_ID], group=db_type, editable=True)
        if ticket_types:
            config_filter &= Q(ticket_type__in=ticket_types)
        ticket_flow_configs = TicketFlowsConfig.objects.filter(config_filter)

        # 获得单据flow配置映射表和集群映射表
        biz_config_map = {cfg.ticket_type: cfg.configs for cfg in ticket_flow_configs if not cfg.cluster_ids}
        cluster_config_map = {cfg.ticket_type: cfg.configs for cfg in ticket_flow_configs if cfg.cluster_ids}

        # 获得集群映射表
        cluster_ids = list(itertools.chain(*ticket_flow_configs.values_list("cluster_ids", flat=True)))
        clusters_map = {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)}

        # 获取单据流程配置信息
        flow_desc_list: List[Dict] = []
        for flow_config in ticket_flow_configs:
            # 获取集群的描述
            cluster_info = [
                {"cluster_id": clusters_map[cluster_id].id, "immute_domain": clusters_map[cluster_id].immute_domain}
                for cluster_id in flow_config.cluster_ids
                if cluster_id in clusters_map
            ]
            # 获取当前单据的执行流程描述
            config_map = cluster_config_map if cluster_info else biz_config_map
            flow_desc = BuilderFactory.registry[flow_config.ticket_type].describe_ticket_flows(config_map)
            # 获取配置的基本信息
            flow_config_info = model_to_dict(flow_config)
            flow_config_info.update(
                ticket_type_display=flow_config.get_ticket_type_display(),
                flow_desc=flow_desc,
                clusters=cluster_info,
                update_at=flow_config.update_at,
            )
            flow_desc_list.append(flow_config_info)

        return flow_desc_list

    @classmethod
    def ticket_status_standardization(cls):
        """
        旧单据状态标准化。TODO: 迁移后此段代码可删除
        """

        # 标准化只针对running的单据，其他状态单据不影响
        running_tickets = list(Ticket.objects.filter(status=TicketStatus.RUNNING))
        for ticket in running_tickets:
            raw_status = ticket.status
            ticket.status = RUNNING_FLOW__TICKET_STATUS[ticket.current_flow().flow_type]
            ticket.save()
            print(f"ticket[{ticket.id}] status {raw_status} ---> {ticket.status}")

        # 失败的单据要增加一条todo关联
        failed_tickets = Ticket.objects.prefetch_related("flows__todo_of_flow").filter(status=TicketStatus.FAILED)
        for ticket in failed_tickets:
            inner_flow = ticket.flows.filter(flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.FAILED).first()
            if not inner_flow or inner_flow.todo_of_flow.exists():
                continue
            Todo.objects.create(
                name=_("【{}】单据任务执行失败，待处理").format(ticket.get_ticket_type_display()),
                flow=inner_flow,
                ticket=ticket,
                type=TodoType.INNER_FAILED,
                context=BaseTodoContext(inner_flow.id, ticket.id).to_dict(),
            )
            print(f"ticket[{ticket.id}] add a failed todo")

        # 待审批的单据要增加一条todo关联
        itsm_tickets = Ticket.objects.prefetch_related("flows").filter(status=TicketStatus.APPROVE)
        for ticket in itsm_tickets:
            itsm_flow = ticket.flows.filter(flow_type=FlowType.BK_ITSM, status=TicketFlowStatus.RUNNING).first()
            if not itsm_flow or itsm_flow.todo_of_flow.exists():
                continue
            Todo.objects.create(
                name=_("【{}】单据等待审批").format(ticket.get_ticket_type_display()),
                flow=itsm_flow,
                ticket=ticket,
                type=TodoType.ITSM,
                context=ItsmTodoContext(itsm_flow.id, ticket.id).to_dict(),
            )
            print(f"ticket[{ticket.id}] add a itsm todo")
