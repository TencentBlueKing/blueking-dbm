"""支持的超时类型根据 flow_desc 生成，不依赖 FlowBuilder 能力属性。"""

import copy

import pytest
from django.utils.translation import override

from backend.ticket.constants import TICKET_EXPIRE_TYPE_DISPLAY, FlowType
from backend.ticket.flow_config import FlowNodeDescription, get_described_flow_types, get_supported_expire_types
from backend.ticket.serializers import SupportedExpireTypeSerializer


@pytest.mark.parametrize("approval", [True, False])
@pytest.mark.parametrize("confirm", [True, False])
@pytest.mark.parametrize("resource", [True, False])
def test_supported_types_follow_flow_description(approval, confirm, resource):
    descriptions = []
    expected = {"confirm_modify", "inner_flow_expire", "flow_todo_expire"}
    if approval:
        descriptions.append(FlowType.BK_ITSM)
        expected.add("itsm_expire")
    if confirm:
        descriptions.append(FlowType.PAUSE)
        expected.add("pause")
    if resource:
        descriptions.append(FlowType.RESOURCE_APPLY)
        expected.add("resource_replenish")
    original = copy.deepcopy(descriptions)
    with override("zh-hans"):
        result = get_supported_expire_types(descriptions)
    assert set(result) == expected
    assert len(result) == len(expected)
    assert descriptions == original
    assert "timer" not in result


@pytest.mark.parametrize("language", ["zh-hans", "en"])
def test_custom_node_label_does_not_determine_expire_type(language):
    with override(language):
        nodes = [
            FlowNodeDescription(FlowType.BK_ITSM, "custom label"),
            FlowNodeDescription(FlowType.INNER_FLOW, "PAUSE"),
        ]
        expire_types = get_supported_expire_types(get_described_flow_types(nodes))
        assert "itsm_expire" in expire_types
        assert "pause" not in expire_types


def test_no_optional_types_when_description_has_no_matching_nodes():
    with override("zh-hans"):
        assert set(get_supported_expire_types([FlowType.INNER_FLOW])) == {
            "confirm_modify",
            "inner_flow_expire",
            "flow_todo_expire",
        }


def test_repeated_nodes_do_not_duplicate_expire_types():
    with override("zh-hans"):
        result = get_supported_expire_types([FlowType.BK_ITSM, FlowType.BK_ITSM, FlowType.PAUSE])
    assert result.count("itsm_expire") == 1
    assert result.count("pause") == 1


def test_expire_type_labels():
    expected = {
        "pause": "待执行",
        "itsm_expire": "待审批",
        "confirm_modify": "待确认修改",
        "resource_replenish": "待补货",
        "inner_flow_expire": "已失败",
        "flow_todo_expire": "待继续",
    }
    with override("zh-hans"):
        values = get_supported_expire_types([FlowType.BK_ITSM, FlowType.PAUSE, FlowType.RESOURCE_APPLY])
        items = [{"value": value, "label": TICKET_EXPIRE_TYPE_DISPLAY[value]} for value in values]
        data = SupportedExpireTypeSerializer(items, many=True).data
        assert {item["value"]: item["label"] for item in data} == expected
