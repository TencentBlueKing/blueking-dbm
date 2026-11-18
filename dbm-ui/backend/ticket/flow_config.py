"""单据流程配置的接口单位转换和部分更新校验。数据库中的超时时间单位为天。"""

import copy
from dataclasses import dataclass

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from backend.ticket.constants import FlowType, TicketExpireType

FLOW_CONFIG_CHECK_ERROR_DISPLAY = {
    "inactive": _("当前不生效"),
    "not_applicable": _("不适用"),
    "unchanged": _("无变更"),
    "preset": _("单据预设"),
}


@dataclass(frozen=True)
class FlowNodeDescription:
    """为流程描述保留稳定的节点类型，使超时配置判断不受翻译或文案修改影响。

    查询、预检查和更新接口根据 flow_type 判断支持的超时类型，查询接口用 label 生成 flow_desc。
    重写 describe_ticket_flows() 时，每个步骤都使用本类，并传入对应的 FlowType。
    审批、人工确认和资源申请节点的类型用于判断相应的超时配置项。
    例如 FlowNodeDescription(FlowType.PAUSE, _("人工确认执行"))。
    """

    # 超时配置根据节点类型判断，避免受翻译和文案变更影响。
    flow_type: FlowType
    # 用于接口的 flow_desc 展示，支持普通字符串和 Django 延迟翻译对象。
    label: str | Promise


def get_supported_expire_types(flow_types):
    supported = {TicketExpireType.CONFIRM_MODIFY, TicketExpireType.INNER_FLOW, TicketExpireType.FLOW_TODO}
    expire_type_by_flow_type = {
        FlowType.BK_ITSM: TicketExpireType.ITSM,
        FlowType.PAUSE: TicketExpireType.PAUSE,
        FlowType.RESOURCE_APPLY: TicketExpireType.RESOURCE_REPLENISH,
        FlowType.RESOURCE_BATCH_APPLY: TicketExpireType.RESOURCE_REPLENISH,
    }
    supported.update(
        expire_type_by_flow_type[flow_type] for flow_type in flow_types if flow_type in expire_type_by_flow_type
    )
    return [expire_type for expire_type in TicketExpireType.get_values() if expire_type in supported]


def get_described_flow_types(nodes):
    return {node.flow_type for node in nodes}


def get_configurable_expire_types(builder, ticket_type, config_map):
    """计算可配置的超时类型，包含打开开关后可启用的节点。"""
    capability_map = {
        **config_map,
        ticket_type: {**config_map[ticket_type], "need_itsm": True, "need_manual_confirm": True},
    }
    nodes = builder.describe_ticket_flows(capability_map)
    return get_supported_expire_types(get_described_flow_types(nodes))


def flow_config_hours_to_days(configs):
    """将平台接口提交的超时小时数转换为数据库保存的天数。

    configs 是已完成参数校验的更新配置；正整数除以 24，允许保存不足一天的小数。
    -1 表示关闭超时控制，保持原值。返回深拷贝，避免修改调用方的请求参数。
    """
    result = copy.deepcopy(configs)
    for key, hours in result.get("expire_config", {}).items():
        if key in TicketExpireType.get_values() and type(hours) is int and hours > 0:
            result["expire_config"][key] = hours / 24
    return result


def expire_days_to_hours(days):
    """将天数转为小时，消除浮点尾差，保留 -1 等特殊值。"""
    if type(days) not in (int, float) or days <= 0:
        return days
    hours = round(days * 24, 10)
    return int(hours) if hours == int(hours) else hours


def flow_config_days_to_hours(configs):
    """将平台配置中保存的超时天数转换为接口展示的小时数。

    兼容历史整数天和不足一天的小数；-1 保持原值。
    返回深拷贝，避免查询回显时修改模型持有的原始配置。
    """
    result = copy.deepcopy(configs)
    for key, days in result.get("expire_config", {}).items():
        if key in TicketExpireType.get_values():
            result["expire_config"][key] = expire_days_to_hours(days)
    return result


def plan_flow_config_update(config, update_configs, builder):
    """仅用于平台配置：生成部分更新方案，并检查配置是否适用、生效。

    config 为待更新的 TicketFlowsConfig，update_configs 为接口提交的更新配置（超时单位为小时），
    builder 为该单据类型对应的流程构造类。
    返回 (merged, errors)：merged 中的超时已转换为天；errors 包含字段、原因编码和中文提示。
    本方法不修改模型、不写数据库；调用方完成整批校验后再统一保存。
    """
    merged = copy.deepcopy(config.configs)
    for key, value in update_configs.items():
        if key == "expire_config":
            # 只覆盖本次提交的超时类型，保留旧配置中未提交的其他超时设置。
            merged[key] = {**merged.get(key, {}), **flow_config_hours_to_days({key: value})[key]}
        else:
            merged[key] = value
    errors = []

    def error(field, code, message):
        """收集当前配置的字段错误，由调用方关联配置 ID 后统一返回。"""
        errors.append({"field": field, "code": code, "message": str(message)})

    # 单据预设允许调整适用的超时时间，但不允许提交审批和人工确认开关。
    switches = {"need_itsm", "need_manual_confirm"} & update_configs.keys()
    if switches and not config.editable:
        for field in sorted(switches):
            error(field, "preset", _("单据预设：不允许修改审批或人工确认配置"))

    # 能力判断与是否启用分开：免审批/免确认属于当前不生效，而非不支持该节点。
    supported = get_configurable_expire_types(builder, config.ticket_type, {config.ticket_type: merged})
    active_desc = builder.describe_ticket_flows({config.ticket_type: merged})
    active_types = get_supported_expire_types(get_described_flow_types(active_desc))
    for expire_type, hours in update_configs.get("expire_config", {}).items():
        field = f"expire_config.{expire_type}"
        if expire_type not in supported:
            error(field, "not_applicable", _("不适用：该单据流程不支持此超时类型"))
            continue
        # -1 是关闭超时控制
        if hours == -1:
            continue
        # 使用合并后的开关判断，支持同一次请求开启节点并设置其超时时间。
        if expire_type == TicketExpireType.ITSM:
            if TicketExpireType.ITSM not in active_types:
                error(field, "inactive", _("当前不生效：该单据已设置免审批"))
        elif expire_type == TicketExpireType.PAUSE:
            if TicketExpireType.PAUSE not in active_types:
                error(field, "inactive", _("当前不生效：该单据已设置免确认"))
    return merged, errors
