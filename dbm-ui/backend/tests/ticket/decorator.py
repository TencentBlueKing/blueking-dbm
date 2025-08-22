import functools
from unittest.mock import patch

from backend.tests.mock_data.ticket.ticket_flow import ROOT_ID
from backend.ticket.flow_manager.inner import InnerFlow


def use_pipeline_mock(test_method):
    """
    装饰器：为特定测试方法使用简单的ROOT_ID mock，而不是测试框架
    用于那些无法使用完整测试框架的测试用例
    """

    @functools.wraps(test_method)
    def wrapper(self, *args, **kwargs):
        # 临时替换InnerFlow._run的mock
        with patch.object(InnerFlow, "_run", return_value=ROOT_ID):
            return test_method(self, *args, **kwargs)

    return wrapper
