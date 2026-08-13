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
import json
import logging
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch, Q
from django.forms import model_to_dict
from django.utils.translation import gettext as _

from backend import env
from backend.components import ItsmApiAdapter as ItsmApi
from backend.configuration.constants import PLAT_BIZ_ID, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.enums.comm import TagType
from backend.db_meta.models import ClusterEntry, Tag
from backend.db_meta.models.db_module import DBModule
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.common.base import fetch_cluster_ids, fetch_instance_ids
from backend.ticket.constants import (
    CLUSTER_TAG_WILDCARD_VALUE,
    FLOW_FINISHED_STATUS,
    SPECIAL_APPROVE_TICKETS,
    TODO_RUNNING_STATUS,
    FlowType,
    FlowTypeConfig,
    OperateNodeActionType,
    TicketFlowStatus,
    TicketType,
    TodoType,
)
from backend.ticket.exceptions import AppBaseException, TicketFlowsConfigException
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Flow, Ticket, TicketFlowsConfig, Todo
from backend.ticket.todos import TodoActionType, TodoActorFactory

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
    def get_itsm_approvers(cls, flow):
        """获取flow审批节点的审批人"""
        if flow.flow_type != FlowType.BK_ITSM:
            return []
        itsm_fields = {field["key"]: field["value"] for field in flow.details["fields"]}
        approvers = itsm_fields["approver"].split(",")
        return approvers

    @classmethod
    def get_itsm_todo_operators(cls, flow):
        approvers = cls.get_itsm_approvers(flow)
        # 对于特殊审批单据，所有人均是处理者
        if flow.ticket.ticket_type in SPECIAL_APPROVE_TICKETS:
            return approvers, []
        # 审批首人是处理人，剩下是协助者
        return approvers[:1], approvers[1:]

    @classmethod
    def operate_itsm_ticket(cls, ticket_id, action, operator, **kwargs):
        """操作itsm中的单据"""
        flow = Flow.objects.get(ticket_id=ticket_id, flow_type="BK_ITSM", status=TicketFlowStatus.RUNNING)
        sn = flow.flow_obj_id
        itsm_info = ItsmApi.get_ticket_info(params={"sn": sn})

        # 当前没有正在进行的步骤，退出
        if not itsm_info["current_steps"]:
            return
        current_step = itsm_info["current_steps"][0]
        state_id = current_step["state_id"]

        act_msg_tpl = _("{}对单据{}操作: {}").format(operator, ticket_id, OperateNodeActionType.get_choice_label(action))
        act_msg = kwargs.get("action_message") or act_msg_tpl

        # 审批单据
        params = {
            "sn": sn,
            "remark": act_msg,
            "action_message": act_msg,
            "action_type": action,
            "operator": operator,
            "bk_username": operator,
        }
        if current_step.get("task_id"):
            params["task_id"] = current_step["task_id"]
        if current_step.get("activity_key"):
            params["activity_key"] = current_step["activity_key"]
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
    def revoke_ticket(cls, ticket_ids, operator, remark):
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
            cls.operate_flow(ticket.id, first_running_flow.id, func="revoke", operator=operator, remark=remark)
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

        locks = defaultdict(threading.Lock)
        results = []

        def process_single(operation):
            todo_id, params = operation["todo_id"], operation["params"]
            with locks[todo_id]:  # 相同todo 串行化
                todo = Todo.objects.get(id=todo_id)
                if action == TodoActionType.DELIVER:
                    TodoActorFactory.actor(todo).deliver(user, action, params)
                else:
                    TodoActorFactory.actor(todo).process(user, action, params)
                return todo

        with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as executor:
            future_to_op = {executor.submit(process_single, op): op for op in operations}

            for future in as_completed(future_to_op):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    logger.error(_("操作todo任务失败: {}").format(e))
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
    def check_ticket_flow_config_cluster_repeat(cls, bk_biz_id, cluster_ids, ticket_type, config_id=None):
        """给前端预校验使用，返回每个集群是否已命中已有流程配置。"""
        current_cluster_ids = set(cluster_ids)
        if not current_cluster_ids:
            return []

        cluster_configs = TicketFlowsConfig.objects.filter(bk_biz_id=bk_biz_id, ticket_type=ticket_type).exclude(
            cluster_ids=[]
        )
        if config_id is not None:
            cluster_configs = cluster_configs.exclude(id=config_id)

        existed_cluster_ids = set()
        for cluster_config in cluster_configs:
            existed_cluster_ids.update(cluster["id"] for cluster in cluster_config.cluster_ids)

        duplicate_cluster_ids = current_cluster_ids & existed_cluster_ids

        return [
            {
                "id": cluster_id,
                "validate": cluster_id in duplicate_cluster_ids,
            }
            for cluster_id in cluster_ids
        ]

    @classmethod
    def build_ticket_flow_config_tag_rules(cls, cluster_tags):
        """将标签列表整理成 {tag_key: {tag_value}}，用于判断两个标签条件是否存在命中范围交集。"""
        tag_rules = defaultdict(set)
        for tag in cluster_tags:
            tag_rules[tag.get("tag_key")].add(tag.get("tag_value"))
        return tag_rules

    @classmethod
    def is_ticket_flow_config_tag_scope_overlap(cls, left_rules, right_rules):
        """判断拟保存标签条件(left)是否命中已有标签条件(right)。"""
        # 没有共同 tag_key 时，普通标签条件不存在冲突可能。
        common_keys = set(left_rules) & set(right_rules)
        if not common_keys:
            return False

        # 所有共同 tag_key 都必须存在取值交集，才认为两组条件覆盖范围有交集。
        for tag_key in common_keys:
            left_values = left_rules[tag_key]
            right_values = right_rules[tag_key]
            right_has_wildcard = CLUSTER_TAG_WILDCARD_VALUE in right_values
            if not right_has_wildcard and not (left_values & right_values):
                return False
        return True

    @classmethod
    def check_ticket_flow_config_cluster_tag_repeat(cls, bk_biz_id, cluster_tags, ticket_type, config_id=None):
        """给前端预校验使用，返回每个集群标签是否已命中已有流程配置。"""
        if not cluster_tags:
            return []

        current_tag_rules = cls.build_ticket_flow_config_tag_rules(cluster_tags)
        tag_configs = TicketFlowsConfig.objects.filter(bk_biz_id=bk_biz_id, ticket_type=ticket_type).exclude(
            cluster_tags=[]
        )
        if config_id is not None:
            tag_configs = tag_configs.exclude(id=config_id)

        conflict_tag_pairs = set()
        for tag_config in tag_configs:
            existed_tag_rules = cls.build_ticket_flow_config_tag_rules(tag_config.cluster_tags)
            if cls.is_ticket_flow_config_tag_scope_overlap(current_tag_rules, existed_tag_rules):
                # 只在同一个 tag_key 下处理“任意值”通配，避免不同 key 之间被误报为重复。
                for tag_key in set(current_tag_rules) & set(existed_tag_rules):
                    current_values = current_tag_rules[tag_key]
                    existed_values = existed_tag_rules[tag_key]
                    existed_has_wildcard = CLUSTER_TAG_WILDCARD_VALUE in existed_values
                    conflict_values = current_values if existed_has_wildcard else current_values & existed_values
                    for tag_value in conflict_values:
                        conflict_tag_pairs.add((tag_key, tag_value))

        return [
            {
                **tag,
                "validate": (tag.get("tag_key"), tag.get("tag_value")) in conflict_tag_pairs,
            }
            for tag in cluster_tags
        ]

    @classmethod
    def create_ticket_flow_config(
        cls, bk_biz_id, cluster_ids, ticket_types, configs, operator, remark, cluster_tags=None
    ):
        """
        创建单据流程
        @param bk_biz_id: 业务ID，为0表示平台业务
        @param cluster_ids: 集群范围列表，表示规则生效的集群范围，格式:
            [{"id": 1, "immute_domain": "mysql.example.com"}]
        @param cluster_tags: 集群标签范围列表，表示规则生效的标签范围，格式:
            [{"id": 14, "tag_key": "dbresource", "tag_value": "xxx"}]
        @param ticket_types: 单据类型列表
        @param configs: 流程配置
        @param operator: 创建者
        @param remark: 备注
        """

        cluster_tags = cluster_tags or []

        def check_create_config(ticket_type):
            if not bk_biz_id:
                raise TicketFlowsConfigException(_("不允许新增平台级别的流程设置"))

            global_config = TicketFlowsConfig.objects.get(bk_biz_id=0, ticket_type=ticket_type)
            biz_configs = TicketFlowsConfig.objects.filter(bk_biz_id=bk_biz_id, ticket_type=ticket_type)

            if configs.get("need_manual_confirm") and configs.get("need_manual_confirm") != global_config.configs.get(
                "need_manual_confirm"
            ):
                raise TicketFlowsConfigException(_("业务级别不允许编辑[人工确认]设置"))

            biz_cfg = biz_configs.filter(cluster_ids=[], cluster_tags=[]).first()

            # 不允许创建相同维度的流程
            if biz_cfg and not cluster_ids and not cluster_tags:
                raise TicketFlowsConfigException(_("业务[{}]已存在{}的流程配置").format(bk_biz_id, ticket_type))
            if cluster_ids:
                checking_cluster_ids = [
                    cluster.get("id") if isinstance(cluster, dict) else cluster for cluster in cluster_ids
                ]
                duplicate_cluster_ids = [
                    cluster["id"]
                    for cluster in cls.check_ticket_flow_config_cluster_repeat(
                        bk_biz_id=bk_biz_id, cluster_ids=checking_cluster_ids, ticket_type=ticket_type
                    )
                    if cluster["validate"]
                ]
                if duplicate_cluster_ids:
                    raise TicketFlowsConfigException(
                        _("业务[{}]已存在{}的集群流程配置，重复集群ID: {}").format(
                            bk_biz_id, ticket_type, sorted(duplicate_cluster_ids)
                        )
                    )
            if cluster_tags:
                duplicate_tags = [
                    tag
                    for tag in cls.check_ticket_flow_config_cluster_tag_repeat(
                        bk_biz_id=bk_biz_id, cluster_tags=cluster_tags, ticket_type=ticket_type
                    )
                    if tag["validate"]
                ]
                if duplicate_tags:
                    raise TicketFlowsConfigException(
                        _("业务[{}]已存在{}的集群标签流程配置，冲突标签: {}").format(bk_biz_id, ticket_type, duplicate_tags)
                    )

        flows_config_list = []
        for type in ticket_types:
            # 校验创建单据流程配置是否合理
            check_create_config(type)
            # 创建流程规则
            group = TicketType.get_db_type_by_ticket(type)
            flows_config = TicketFlowsConfig(
                bk_biz_id=bk_biz_id,
                cluster_ids=cluster_ids,
                cluster_tags=cluster_tags,
                ticket_type=type,
                group=group,
                configs=configs,
                creator=operator,
                updater=operator,
                remark=remark,
            )
            flows_config_list.append(flows_config)

        TicketFlowsConfig.objects.bulk_create(flows_config_list)

    @classmethod
    def update_ticket_flow_config(
        cls, bk_biz_id, cluster_ids, ticket_types, configs, config_ids, operator, remark, cluster_tags=None
    ):
        """
        更新单据流程
        @param bk_biz_id: 业务ID，为0表示平台业务
        @param cluster_ids: 集群范围列表，表示规则生效的集群范围，格式:
            [{"id": 1, "immute_domain": "mysql.example.com"}]
        @param cluster_tags: 集群标签范围列表，表示规则生效的标签范围，格式:
            [{"id": 14, "tag_key": "dbresource", "tag_value": "xxx"}]
        @param ticket_types: 单据类型列表
        @param configs: 流程配置
        @param config_ids: 更新的流程ID列表
        @param operator: 更新人
        @param remark: 备注
        """
        cluster_ids = cluster_ids or []
        cluster_tags = cluster_tags or []
        config_ids = config_ids or []

        config_qs = TicketFlowsConfig.objects.filter(bk_biz_id=bk_biz_id, ticket_type__in=ticket_types)

        def check_editable_configs(configs_qs):
            uneditable_configs = list(configs_qs.filter(editable=False).values_list("id", "ticket_type"))
            if uneditable_configs:
                raise TicketFlowsConfigException(_("流程配置不允许编辑，配置ID和单据类型: {}").format(uneditable_configs))

        # 平台全局配置直接更新
        if not bk_biz_id:
            check_editable_configs(config_qs)
            config_qs.update(configs=configs)
            return

        # 业务级别先删除，再创建，可以复用校验流程
        with transaction.atomic():
            update_config_qs = config_qs.filter(id__in=config_ids).exclude(bk_biz_id=PLAT_BIZ_ID)
            check_editable_configs(update_config_qs)
            update_config_qs.delete()
            cls.create_ticket_flow_config(
                bk_biz_id, cluster_ids, ticket_types, configs, operator, remark, cluster_tags
            )

    @classmethod
    def query_ticket_flows_describe(cls, bk_biz_id, db_type, ticket_types=None):
        # 根据条件过滤单据配置
        config_filter = Q(bk_biz_id__in=[bk_biz_id, PLAT_BIZ_ID], group=db_type)
        if ticket_types:
            config_filter &= Q(ticket_type__in=ticket_types)
        candidate_flow_configs = TicketFlowsConfig.objects.filter(config_filter)

        # 同一个 ticket_type 的时候 cluster_ids/cluster_tags 为空的是父配置，非空的是子配置；子配置返回时带上父配置 ID。
        ticket_flow_config_map = defaultdict(list)
        for config in candidate_flow_configs:
            ticket_flow_config_map[config.ticket_type].append(config)

        ticket_flow_configs = []
        for configs in ticket_flow_config_map.values():
            # 平台父配置作为兜底配置，业务未创建父配置时使用平台配置展示。
            plat_parent_config = next(
                (config for config in configs if config.bk_biz_id == PLAT_BIZ_ID),
                None,
            )
            # 业务父配置只包含业务维度配置，不包含集群子策略和标签子策略。
            biz_parent_config = next(
                (
                    config
                    for config in configs
                    if config.bk_biz_id != PLAT_BIZ_ID and not config.cluster_ids and not config.cluster_tags
                ),
                None,
            )
            # 集群子策略和标签子策略都作为子配置返回，前端通过 is_child_config 区分。
            biz_child_configs = [config for config in configs if config.cluster_ids or config.cluster_tags]

            # 有业务父配置时(自定义策略)，使用业务父配置；否则使用平台父配置。
            parent_config = biz_parent_config or plat_parent_config
            ticket_flow_configs.extend([config for config in [parent_config] if config] + biz_child_configs)
        # 记录每种 ticket_type 的父配置，后续给子配置补充 parent_id 和重复配置标记。
        parent_config_map = {
            config.ticket_type: config
            for config in ticket_flow_configs
            if not config.cluster_ids and not config.cluster_tags
        }
        # 记录存在子配置的 ticket_type，父配置返回时标记 has_child_config。
        child_config_ticket_types = {
            config.ticket_type for config in ticket_flow_configs if config.cluster_ids or config.cluster_tags
        }

        # 获得单据flow配置映射表和集群映射表
        biz_config_map = {
            cfg.ticket_type: cfg.configs for cfg in ticket_flow_configs if not cfg.cluster_ids and not cfg.cluster_tags
        }

        # 批量查询标签是否仍然存在；标签被删除后，返回时标记 is_invalid，用作前端展示。
        # 根据 tag_key/tag_value，判断有效性。
        tag_pairs = {
            (tag["tag_key"], tag["tag_value"])
            for cfg in ticket_flow_configs
            for tag in cfg.cluster_tags
            if isinstance(tag, dict)
            and tag.get("tag_key")
            and tag.get("tag_value")
            and tag.get("tag_value") != CLUSTER_TAG_WILDCARD_VALUE
        }
        if tag_pairs:
            tag_keys = {tag_key for tag_key, __ in tag_pairs}
            tag_values = {tag_value for __, tag_value in tag_pairs}
            valid_tag_pairs = set(
                Tag.objects.filter(
                    bk_biz_id__in=[bk_biz_id, PLAT_BIZ_ID],
                    key__in=tag_keys,
                    value__in=tag_values,
                    type=TagType.CLUSTER,
                ).values_list("key", "value")
            )
        else:
            valid_tag_pairs = set()

        flow_desc_list: List[Dict] = []
        for flow_config in ticket_flow_configs:
            is_child_config = bool(flow_config.cluster_ids or flow_config.cluster_tags)
            # 获取集群的描述
            cluster_info = [
                {"cluster_id": cluster["id"], "immute_domain": cluster["immute_domain"]}
                for cluster in flow_config.cluster_ids
            ]
            # 获取当前单据的执行流程描述
            # 子配置只用自身 configs 生成描述；父配置使用同组父配置映射生成完整描述。
            config_map = {flow_config.ticket_type: flow_config.configs} if is_child_config else biz_config_map
            flow_desc = BuilderFactory.registry[flow_config.ticket_type].describe_ticket_flows(config_map)
            # 获取配置的基本信息
            flow_config_info = model_to_dict(flow_config)

            # 给标签范围追加失效标记，兼容标签表数据已被删除的场景。
            def append_tag_invalid_mark(tag):
                if not isinstance(tag, dict):
                    return tag

                tag_key = tag.get("tag_key")
                tag_value = tag.get("tag_value")
                is_invalid = (
                    not tag_key
                    or not tag_value
                    or (tag_value != CLUSTER_TAG_WILDCARD_VALUE and (tag_key, tag_value) not in valid_tag_pairs)
                )
                return {**tag, "is_invalid": is_invalid}

            flow_config_info["cluster_tags"] = [
                append_tag_invalid_mark(tag) for tag in flow_config_info["cluster_tags"]
            ]
            parent_config = parent_config_map.get(flow_config.ticket_type)
            # model_to_dict 返回的 configs 可能直接引用原对象，这里复制后再追加展示字段。
            flow_config_info["configs"] = dict(flow_config_info["configs"])
            if is_child_config and parent_config:
                # 子配置的 need_itsm 与父配置一致时，标记为重复配置，便于前端提示用户。
                flow_config_info["configs"]["need_itsm_duplicated"] = flow_config.configs.get(
                    FlowTypeConfig.NEED_ITSM
                ) == parent_config.configs.get(FlowTypeConfig.NEED_ITSM)
            flow_config_info.update(
                parent_id=parent_config.id if is_child_config and parent_config else 0,
                is_child_config=is_child_config,
                has_child_config=not is_child_config and flow_config.ticket_type in child_config_ticket_types,
                ticket_type_display=flow_config.get_ticket_type_display(),
                flow_desc=flow_desc,
                clusters=cluster_info,
                update_at=flow_config.update_at,
            )
            flow_desc_list.append(flow_config_info)

        return flow_desc_list


class CheckDomainRepeatHandler:
    def __init__(self, cluster_type):
        self.cluster_type = cluster_type

    def get_has_model_domain(self, db_module_id, domains, db_app_abbr):
        """
        db_app_abbr 的值如果没有就按biz-{bk_biz_id}传
        """
        domain_info = []
        db_module = DBModule.objects.filter(db_module_id=db_module_id).first()
        db_module_name = db_module.alias_name if db_module else f"db-module-{db_module_id}"
        for domain in domains:
            domain_temp = ClusterType.get_domain_template_map().get(self.cluster_type)
            if not domain_temp:
                raise AppBaseException(_("当前集群类型暂未设置域名模板映射， 请联系管理员"))
            full_domain = domain_temp.format(
                db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain
            )
            domain_info.append(
                {
                    "prefix": f"{db_module_name}db.",
                    "suffix": f".{db_app_abbr}.db",
                    "domain": full_domain,
                }
            )
        return domain_info

    def get_common_domain(self, domains, db_app_abbr):
        domain_prefix_map = ClusterType.get_domain_prefix_map()
        domain_prefix = domain_prefix_map.get(self.cluster_type)
        if not domain_prefix:
            raise AppBaseException(_("未获取到对应集群类型的域名前缀, 请联系管理员"))

        return [
            {
                "prefix": f"{domain_prefix}.",
                "suffix": f".{db_app_abbr}.db",
                "domain": "{}.{}.{}.db".format(domain_prefix, domain, db_app_abbr),
            }
            for domain in domains
        ]

    def check_domain(self, domains, db_app_abbr, db_module_id=None):
        # 带db_module_id的集群域名需要module相关信息拼接域名，分场景处理
        if db_module_id:
            domain_info = self.get_has_model_domain(db_module_id, domains, db_app_abbr)
        else:
            domain_info = self.get_common_domain(domains, db_app_abbr)

        if self.cluster_type in ClusterType.k8s_container_cluster_type_values():
            cluster_entry_type = ClusterEntryType.CLBDNS.value
        else:
            cluster_entry_type = ClusterEntryType.DNS.value

        entries = [domain["domain"] for domain in domain_info]
        has_entries = ClusterEntry.objects.filter(cluster_entry_type=cluster_entry_type, entry__in=entries)
        entry_domain_map = {entry.entry: entry for entry in has_entries}

        for domain in domain_info:
            if entry_domain_map.get(domain["domain"]):
                domain["validate"] = True
            else:
                domain["validate"] = False

        return domain_info
