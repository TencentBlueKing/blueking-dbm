"""部分更新、小时单位及批量原子校验，不依赖真实数据库。"""

import copy
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.constants import DEFAULT_SYSTEM_USER
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.constants import FlowContext, FlowErrCode, FlowType, TicketStatus
from backend.ticket.exceptions import TicketFlowsConfigException
from backend.ticket.flow_config import flow_config_days_to_hours, flow_config_hours_to_days, plan_flow_config_update
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.handler import TicketHandler
from backend.ticket.models import Ticket
from backend.ticket.serializers import (
    CheckUpdateTicketFlowConfigSerializer,
    TicketFlowConfigCheckResultSerializer,
    UpdateTicketFlowConfigSerializer,
)


class ConfigFlowBuilder(TicketFlowBuilder):
    ticket_type = "MYSQL_SINGLE_APPLY"


def test_system_termination_records_pause_timeout_in_hours():
    flow = SimpleNamespace(flow_type=FlowType.PAUSE, context={}, save=MagicMock())
    ticket = SimpleNamespace(ticket_type="MYSQL_SINGLE_APPLY", save=MagicMock())
    manager = SimpleNamespace(flow_obj=flow, ticket=ticket)
    manager.get_current_config_expire_time = lambda: BaseTicketFlow.get_current_config_expire_time(manager)
    config = SimpleNamespace(configs={"expire_config": {"pause": 2 / 24, "flow_todo_expire": 7}})
    with patch("backend.ticket.flow_manager.base.TicketFlowsConfig.get_config", return_value=config):
        BaseTicketFlow.flush_revoke_status_handler(manager, DEFAULT_SYSTEM_USER)

    assert flow.context[FlowContext.EXPIRE_TIME_HOURS] == 2


@pytest.mark.parametrize(
    "context, expected_duration",
    [
        ({FlowContext.EXPIRE_TIME_HOURS: 2}, "2小时"),
        ({FlowContext.EXPIRE_TIME: 3}, "72小时"),
        ({FlowContext.EXPIRE_TIME: 1 / 12}, "2小时"),
        ({FlowContext.EXPIRE_TIME: 3, FlowContext.EXPIRE_TIME_HOURS: 2}, "2小时"),
    ],
)
def test_termination_reason_displays_hours(context, expected_duration):
    from django.utils.translation import override

    flow = SimpleNamespace(err_code=FlowErrCode.SYSTEM_TERMINATED_ERROR, context=context)
    ticket = SimpleNamespace(status=TicketStatus.TERMINATED, current_flow=lambda: flow)
    with override("zh-hans"):
        assert expected_duration in Ticket.get_terminate_reason(ticket)


def make_config(config_id=1, *, editable=True, bk_biz_id=0, **configs):
    return SimpleNamespace(
        id=config_id,
        ticket_type="MYSQL_SINGLE_APPLY",
        bk_biz_id=bk_biz_id,
        editable=editable,
        configs={"need_itsm": True, "need_manual_confirm": True, **configs},
        cluster_ids=[],
        cluster_tags=[],
        remark="original",
        save=MagicMock(),
    )


def validate_payload(configs):
    serializer = UpdateTicketFlowConfigSerializer(
        data={
            "bk_biz_id": 0,
            "cluster_ids": [],
            "config_ids": [1],
            "ticket_types": ["MYSQL_SINGLE_APPLY"],
            "configs": configs,
        }
    )
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


@pytest.mark.parametrize("hours", [-1, 1, 2, 24, 2160])
def test_valid_hours_round_trip(hours):
    validated = validate_payload({"expire_config": {"pause": hours}})
    stored = flow_config_hours_to_days(validated["configs"])
    assert stored["expire_config"]["pause"] == (-1 if hours == -1 else hours / 24)
    assert flow_config_days_to_hours(stored)["expire_config"]["pause"] == hours


@pytest.mark.parametrize("hours", [0, -2, 2161, 1.5, 1.0, True, False, "2", None])
def test_reject_invalid_hours(hours):
    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError):
        validate_payload({"expire_config": {"pause": hours}})


@pytest.mark.parametrize("configs", [{}, {"expire_config": {}}, {"expire_config": {"unknown": 1}}, {"unknown": True}])
def test_reject_empty_or_unknown_fields(configs):
    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError):
        validate_payload(configs)


def test_nested_update_preserves_unsubmitted_fields():
    cfg = make_config(expire_config={"pause": 1, "inner_flow_expire": 7, "itsm_expire": -1}, custom="preserved")
    original = copy.deepcopy(cfg.configs)
    payload = {"expire_config": {"pause": 2}}
    merged, errors = plan_flow_config_update(cfg, payload, ConfigFlowBuilder)
    assert errors == []
    assert merged["expire_config"] == {"pause": 2 / 24, "inner_flow_expire": 7, "itsm_expire": -1}
    assert merged["custom"] == "preserved"
    assert merged["need_itsm"] is True
    assert cfg.configs == original
    assert payload == {"expire_config": {"pause": 2}}


@pytest.mark.parametrize("field, expire_type", [("need_itsm", "itsm_expire"), ("need_manual_confirm", "pause")])
def test_uses_merged_switches_to_check_effectiveness(field, expire_type):
    cfg = make_config(**{field: False})
    _, errors = plan_flow_config_update(cfg, {"expire_config": {expire_type: 2}}, ConfigFlowBuilder)
    assert errors[0]["code"] == "inactive"
    _, errors = plan_flow_config_update(cfg, {field: True, "expire_config": {expire_type: 2}}, ConfigFlowBuilder)
    assert errors == []
    cfg.configs[field] = True
    _, errors = plan_flow_config_update(cfg, {field: False, "expire_config": {expire_type: 2}}, ConfigFlowBuilder)
    assert errors[0]["code"] == "inactive"


def test_can_clear_inactive_timeout():
    _, errors = plan_flow_config_update(
        make_config(need_itsm=False), {"expire_config": {"itsm_expire": -1}}, ConfigFlowBuilder
    )
    assert errors == []


def test_unsupported_resource_timeout():
    _, errors = plan_flow_config_update(make_config(), {"expire_config": {"resource_replenish": 2}}, ConfigFlowBuilder)
    assert errors[0]["code"] == "not_applicable"


@pytest.mark.parametrize("field", ["need_itsm", "need_manual_confirm"])
def test_preset_switches_cannot_be_modified(field):
    _, errors = plan_flow_config_update(make_config(editable=False), {field: False}, ConfigFlowBuilder)
    assert any(error["code"] == "preset" for error in errors)


def test_preset_allows_supported_timeout_updates():
    merged, errors = plan_flow_config_update(
        make_config(editable=False), {"expire_config": {"inner_flow_expire": 2}}, ConfigFlowBuilder
    )
    assert errors == []
    assert merged["expire_config"]["inner_flow_expire"] == 2 / 24


def run_update(configs, targets, ids=None):
    queryset = MagicMock()
    queryset.filter.return_value = queryset
    queryset.order_by.return_value = targets
    with (
        patch("backend.ticket.handler.transaction.atomic", return_value=nullcontext()),
        patch("backend.ticket.handler.TicketFlowsConfig.objects.select_for_update", return_value=queryset),
        patch.dict("backend.ticket.handler.BuilderFactory.registry", {"MYSQL_SINGLE_APPLY": ConfigFlowBuilder}),
    ):
        TicketHandler.update_ticket_flow_config(
            bk_biz_id=0,
            cluster_ids=[],
            ticket_types=["MYSQL_SINGLE_APPLY"],
            configs=configs,
            config_ids=ids if ids is not None else [cfg.id for cfg in targets],
            operator="tester",
        )


def test_any_invalid_record_aborts_entire_batch_before_saving():
    targets = [make_config(1, need_itsm=False), make_config(2, editable=False)]
    with pytest.raises(TicketFlowsConfigException) as exc:
        run_update({"need_itsm": True}, targets)
    assert exc.value.data["config_errors"][0]["errors"][0]["code"] == "preset"
    for cfg in targets:
        cfg.save.assert_not_called()
        assert cfg.configs["need_itsm"] == (cfg.id != 1)


def test_unchanged_record_aborts_batch():
    targets = [make_config(1, need_itsm=False), make_config(2, need_itsm=True)]
    with pytest.raises(TicketFlowsConfigException) as exc:
        run_update({"need_itsm": True}, targets)
    assert exc.value.data["config_errors"][0]["errors"][0]["code"] == "unchanged"
    assert all(not cfg.save.called for cfg in targets)


def test_success_preserves_records_and_audit_fields():
    targets = [make_config(1, expire_config={"pause": 1}), make_config(2, expire_config={"pause": 3})]
    run_update({"expire_config": {"inner_flow_expire": 2}}, targets)
    for cfg, days in zip(targets, [1, 3]):
        assert cfg.configs["expire_config"] == {"pause": days, "inner_flow_expire": 2 / 24}
        assert cfg.remark == "original"
        assert cfg.updater == "tester"
        cfg.save.assert_called_once()


def test_missing_or_wrong_scope_id_rejects_entire_batch():
    cfg = make_config()
    with pytest.raises(TicketFlowsConfigException) as exc:
        run_update({"need_itsm": False}, [cfg], ids=[1, 999])
    assert exc.value.data["missing_config_ids"] == [999]
    cfg.save.assert_not_called()


def test_read_conversion_preserves_legacy_days_and_model_data():
    stored = {"expire_config": {"pause": 1, "inner_flow_expire": 90, "itsm_expire": -1}}
    assert flow_config_days_to_hours(stored)["expire_config"] == {
        "pause": 24,
        "inner_flow_expire": 2160,
        "itsm_expire": -1,
    }
    assert stored["expire_config"]["pause"] == 1


@pytest.mark.parametrize("bk_biz_id, expected_pause", [(0, 24), (1, 1)])
@pytest.mark.parametrize("has_optional_nodes", [False, True])
def test_query_excludes_disabled_optional_expire_types(bk_biz_id, expected_pause, has_optional_nodes):
    cfg = make_config(
        bk_biz_id=bk_biz_id,
        need_itsm=False,
        need_manual_confirm=False,
        expire_config={"pause": 1, "itsm_expire": -1},
    )
    cfg.update_at = None
    cfg.get_ticket_type_display = lambda: "MySQL"
    row = {"configs": cfg.configs, "cluster_tags": []}
    builder = (
        ConfigFlowBuilder
        if has_optional_nodes
        else SimpleNamespace(
            describe_ticket_flows=lambda configs: [],
        )
    )
    with (
        patch("backend.ticket.handler.TicketFlowsConfig.objects.filter", return_value=[cfg]),
        patch("backend.ticket.handler.model_to_dict", return_value=row),
        patch.dict("backend.ticket.handler.BuilderFactory.registry", {cfg.ticket_type: builder}),
    ):
        result = TicketHandler.query_ticket_flows_describe(bk_biz_id, "mysql", [cfg.ticket_type])
    assert result[0]["configs"]["expire_config"] == {"pause": expected_pause, "itsm_expire": -1}
    assert result[0]["flow_desc"] == []
    expected_types = {"confirm_modify", "inner_flow_expire", "flow_todo_expire"}
    assert {item["value"] for item in result[0]["supported_expire_types"]} == expected_types
    assert cfg.configs["need_itsm"] is False
    assert cfg.configs["need_manual_confirm"] is False
    assert cfg.configs["expire_config"]["pause"] == 1


def test_single_unchanged_request_is_idempotent():
    cfg = make_config(expire_config={"pause": 2 / 24})
    run_update({"expire_config": {"pause": 2}}, [cfg])
    cfg.save.assert_not_called()


def test_update_does_not_clear_existing_cluster_scope():
    cfg = make_config(need_itsm=False)
    cfg.cluster_ids = [{"id": 1, "immute_domain": "existing.example.com"}]
    run_update({"need_itsm": True}, [cfg])
    assert cfg.cluster_ids == [{"id": 1, "immute_domain": "existing.example.com"}]
    assert "cluster_ids" not in cfg.save.call_args.kwargs["update_fields"]


def test_batch_no_change_compares_hours_against_stored_days():
    targets = [make_config(1, expire_config={"pause": 2 / 24}), make_config(2, expire_config={"pause": 1})]
    with pytest.raises(TicketFlowsConfigException) as exc:
        run_update({"expire_config": {"pause": 2}}, targets)
    assert exc.value.data["config_errors"][0]["errors"][0]["code"] == "unchanged"
    assert all(not cfg.save.called for cfg in targets)


@pytest.mark.parametrize("bk_biz_id", [1, 123])
def test_business_serializer_preserves_legacy_configs_and_defaults(bk_biz_id):
    configs = {"legacy_key": True, "expire_config": {"pause": 0, "enable": True}}
    serializer = UpdateTicketFlowConfigSerializer(
        data={
            "bk_biz_id": bk_biz_id,
            "ticket_types": ["MYSQL_SINGLE_APPLY"],
            "configs": configs,
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["configs"] == configs
    assert serializer.validated_data["remark"] == ""


def test_business_update_keeps_delete_and_recreate_without_platform_validation():
    configs = {"need_itsm": False, "expire_config": {"pause": 2, "enable": True}}
    queryset = MagicMock()
    queryset.filter.return_value = queryset
    queryset.exclude.return_value = queryset
    queryset.values_list.return_value = []
    with (
        patch("backend.ticket.handler.transaction.atomic", return_value=nullcontext()),
        patch("backend.ticket.handler.TicketFlowsConfig.objects.filter", return_value=queryset),
        patch("backend.ticket.handler.TicketFlowsConfig.objects.select_for_update") as platform_query,
        patch("backend.ticket.handler.TicketHandler.create_ticket_flow_config") as create,
        patch("backend.ticket.handler.plan_flow_config_update") as planner,
    ):
        TicketHandler.update_ticket_flow_config(
            bk_biz_id=123,
            cluster_ids=[],
            ticket_types=["MYSQL_SINGLE_APPLY"],
            configs=configs,
            config_ids=[22],
            operator="tester",
            remark="original",
        )
    queryset.delete.assert_called_once()
    create.assert_called_once_with(123, [], ["MYSQL_SINGLE_APPLY"], configs, "tester", "original", [])
    planner.assert_not_called()
    platform_query.assert_not_called()


def test_business_preset_still_rejects_update_before_deletion():
    queryset = MagicMock()
    queryset.filter.return_value = queryset
    queryset.exclude.return_value = queryset
    queryset.values_list.return_value = [(22, "MYSQL_SINGLE_APPLY")]
    with (
        patch("backend.ticket.handler.transaction.atomic", return_value=nullcontext()),
        patch("backend.ticket.handler.TicketFlowsConfig.objects.filter", return_value=queryset),
        patch("backend.ticket.handler.TicketHandler.create_ticket_flow_config") as create,
    ):
        with pytest.raises(TicketFlowsConfigException):
            TicketHandler.update_ticket_flow_config(
                bk_biz_id=123,
                cluster_ids=[],
                ticket_types=["MYSQL_SINGLE_APPLY"],
                configs={"need_itsm": False},
                config_ids=[22],
                operator="tester",
                remark="original",
            )
    queryset.delete.assert_not_called()
    create.assert_not_called()


def run_precheck(configs, targets, ids=None):
    queryset = MagicMock()
    queryset.filter.return_value = queryset
    queryset.order_by.return_value = targets
    with (
        patch("backend.ticket.handler.TicketFlowsConfig.objects.filter", return_value=queryset),
        patch("backend.ticket.handler.TicketFlowsConfig.objects.select_for_update") as lock,
        patch.dict("backend.ticket.handler.BuilderFactory.registry", {"MYSQL_SINGLE_APPLY": ConfigFlowBuilder}),
    ):
        result = TicketHandler.check_update_ticket_flow_config(
            bk_biz_id=0,
            cluster_ids=[],
            ticket_types=["MYSQL_SINGLE_APPLY"],
            configs=configs,
            config_ids=ids if ids is not None else [cfg.id for cfg in targets],
        )
    lock.assert_not_called()
    return result


def test_precheck_success_does_not_change_or_save_configuration():
    cfg = make_config(need_itsm=False, expire_config={"inner_flow_expire": 7})
    original = copy.deepcopy(cfg.configs)
    result = run_precheck({"need_itsm": True, "expire_config": {"itsm_expire": 2}}, [cfg])
    assert result == {
        "valid": True,
        "config_errors": [],
        "missing_config_ids": [],
        "missing_ticket_types": [],
    }
    assert cfg.configs == original
    cfg.save.assert_not_called()


@pytest.mark.parametrize("case", ["inactive", "not_applicable", "unchanged", "preset"])
def test_precheck_and_update_report_the_same_validation_errors(case):
    if case == "inactive":
        targets, configs = [make_config(need_itsm=False)], {"expire_config": {"itsm_expire": 2}}
    elif case == "not_applicable":
        targets, configs = [make_config()], {"expire_config": {"resource_replenish": 2}}
    elif case == "preset":
        targets, configs = [make_config(editable=False)], {"need_itsm": False}
    else:
        targets, configs = [make_config(1), make_config(2)], {"need_itsm": True}
    original = [copy.deepcopy(cfg.configs) for cfg in targets]
    result = run_precheck(configs, targets)
    assert result["valid"] is False
    assert result["config_errors"][0]["errors"][0]["code"] == case
    assert result["config_errors"][0]["ticket_type_display"] == "MySQL 单节点部署"
    assert (
        result["config_errors"][0]["errors"][0]["code_display"]
        == {
            "inactive": "当前不生效",
            "not_applicable": "不适用",
            "unchanged": "无变更",
            "preset": "单据预设",
        }[case]
    )
    assert TicketFlowConfigCheckResultSerializer(result).data == result
    with pytest.raises(TicketFlowsConfigException) as exc:
        run_update(configs, targets)
    assert exc.value.data == result
    for cfg, previous in zip(targets, original):
        assert cfg.configs == previous
        cfg.save.assert_not_called()


def test_precheck_reports_missing_ids_without_writing():
    cfg = make_config()
    result = run_precheck({"need_itsm": False}, [cfg], ids=[1, 999])
    assert result["valid"] is False
    assert result["missing_config_ids"] == [999]
    cfg.save.assert_not_called()


def test_precheck_single_unchanged_request_is_valid():
    cfg = make_config()
    assert run_precheck({"need_itsm": True}, [cfg])["valid"] is True
    cfg.save.assert_not_called()


def test_precheck_serializer_accepts_the_update_payload_and_validates_hours():
    data = {
        "bk_biz_id": 0,
        "config_ids": [1],
        "ticket_types": ["MYSQL_SINGLE_APPLY"],
        "configs": {"expire_config": {"pause": 2}},
    }
    check = CheckUpdateTicketFlowConfigSerializer(data=data)
    update = UpdateTicketFlowConfigSerializer(data=data)
    assert check.is_valid(), check.errors
    assert update.is_valid(), update.errors
    assert check.validated_data == update.validated_data
    data["configs"]["expire_config"]["pause"] = 0
    assert CheckUpdateTicketFlowConfigSerializer(data=data).is_valid() is False


def test_precheck_rejects_non_platform_business():
    serializer = CheckUpdateTicketFlowConfigSerializer(
        data={
            "bk_biz_id": 123,
            "ticket_types": ["MYSQL_SINGLE_APPLY"],
            "configs": {"need_itsm": False},
        }
    )
    assert serializer.is_valid() is False
    assert "bk_biz_id" in serializer.errors
    with patch("backend.ticket.handler.TicketFlowsConfig.objects.filter") as query:
        with pytest.raises(TicketFlowsConfigException):
            TicketHandler.check_update_ticket_flow_config(
                bk_biz_id=123,
                cluster_ids=[],
                ticket_types=["MYSQL_SINGLE_APPLY"],
                configs={"need_itsm": False},
                config_ids=[1],
            )
    query.assert_not_called()


def test_precheck_view_delegates_and_uses_update_permissions():
    from backend.ticket.views import TicketViewSet

    view = TicketViewSet()
    view.action = "check_update_ticket_flow_config"
    view.request = object()
    with patch("backend.ticket.views.ticket_flows_config_permission", return_value=[]) as permission:
        assert view._get_custom_permissions() == []
    permission.assert_called_once_with("update_ticket_flow_config", view.request)
    data = {
        "bk_biz_id": 0,
        "cluster_ids": [],
        "config_ids": [1],
        "ticket_types": ["MYSQL_SINGLE_APPLY"],
        "configs": {"need_itsm": True},
    }
    view.params_validate = MagicMock(return_value=data)
    result = {"valid": True, "config_errors": [], "missing_config_ids": [], "missing_ticket_types": []}
    with patch("backend.ticket.views.TicketHandler.check_update_ticket_flow_config", return_value=result) as check:
        response = view.check_update_ticket_flow_config(view.request)
    check.assert_called_once_with(**data)
    assert response.data == result
    assert TicketViewSet.check_update_ticket_flow_config.mapping["post"] == "check_update_ticket_flow_config"


def test_precheck_route_is_registered():
    from django.urls import resolve

    match = resolve("/apis/tickets/check_update_ticket_flow_config/")
    assert match.func.actions["post"] == "check_update_ticket_flow_config"
