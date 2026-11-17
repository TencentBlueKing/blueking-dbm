"""单据流程配置的接口单位转换和部分更新校验。数据库中的超时时间单位为天。"""

import copy

from django.utils.translation import gettext_lazy as _

from backend.ticket.constants import FlowType, TicketExpireType

FLOW_CONFIG_CHECK_ERROR_DISPLAY = {
    "inactive": _("当前不生效"),
    "not_applicable": _("不适用"),
    "unchanged": _("无变更"),
    "preset": _("单据预设"),
}


def get_supported_expire_types(flow_desc):
    """根据接口展示的流程描述判断超时类型，无需在各个 FlowBuilder 维护额外属性。

    待确认修改、已失败、待继续始终提供；审批、人工确认和待补货跟随描述中的节点。
    同时兼容运维/产品审批、人工确认执行、定时执行(人工确认)等自定义描述。
    """
    supported = {TicketExpireType.CONFIRM_MODIFY, TicketExpireType.INNER_FLOW, TicketExpireType.FLOW_TODO}
    # 超时类型与 flow_desc 中的节点名称映射；同类节点在不同单据中可能使用不同描述。
    # 后续通过包含匹配判断描述中是否存在对应节点，任意名称匹配即可提供该超时配置。
    markers = {
        # 审批节点：普通单据审批，以及数据导出等单据中的运维/产品人员审批。
        TicketExpireType.ITSM: [
            str(FlowType.get_choice_label(FlowType.BK_ITSM)),  # 单据审批
            str(_("运维人员审批")),
            str(_("产品人员审批")),
        ],
        # 人工确认执行节点：兼容手动执行及定时/人工执行的可选分支描述。
        TicketExpireType.PAUSE: [
            str(FlowType.get_choice_label(FlowType.PAUSE)),  # 人工确认
            str(_("人工执行")),
            str(_("人工确认执行")),
            str(_("定时执行(人工确认)")),
            str(_("定时执行/人工执行")),
        ],
        # 资源申请节点：单次或批量申请资源不足时，可能产生待补货状态。
        TicketExpireType.RESOURCE_REPLENISH: [
            str(FlowType.get_choice_label(FlowType.RESOURCE_APPLY)),
            str(FlowType.get_choice_label(FlowType.RESOURCE_BATCH_APPLY)),
        ],
    }
    for expire_type, names in markers.items():
        if any(name.casefold() in str(description).casefold() for description in flow_desc for name in names):
            supported.add(expire_type)
    return [expire_type for expire_type in TicketExpireType.get_values() if expire_type in supported]


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


def flow_config_days_to_hours(configs):
    """将平台配置中保存的超时天数转换为接口展示的小时数。

    兼容历史整数天和不足一天的小数；-1 保持原值。
    返回深拷贝，避免查询回显时修改模型持有的原始配置。
    """
    result = copy.deepcopy(configs)
    for key, days in result.get("expire_config", {}).items():
        if key in TicketExpireType.get_values() and type(days) in (int, float) and days > 0:
            # 消除小时与天相互换算的浮点尾差，整小时以整数返回。
            hours = round(days * 24, 10)
            result["expire_config"][key] = int(hours) if hours == int(hours) else hours
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
    capability_config = {**merged, "need_itsm": True, "need_manual_confirm": True}
    capability_desc = builder.describe_ticket_flows({config.ticket_type: capability_config})
    supported = get_supported_expire_types(capability_desc)
    active_desc = builder.describe_ticket_flows({config.ticket_type: merged})
    active_types = get_supported_expire_types(active_desc)
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
