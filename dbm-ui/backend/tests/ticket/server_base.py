import copy
from unittest.mock import PropertyMock, patch

from rest_framework.permissions import AllowAny

from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.itsm import ItsmApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.tests.mock_data.ticket.ticket_flow import ROOT_ID, SN
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketStatus
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.flow_manager.pause import PauseFlow
from backend.ticket.models import Flow
from backend.ticket.views import TicketViewSet


class TestFlowBase:
    """
    测试流程的基类。
    """

    patches = [
        patch.object(TicketViewSet, "permission_classes"),
        patch.object(InnerFlow, "_run"),
        patch.object(InnerFlow, "status", new_callable=PropertyMock),
        patch.object(PauseFlow, "status", new_callable=PropertyMock),
        patch.object(TicketViewSet, "get_permissions"),
        patch("backend.ticket.flow_manager.itsm.ItsmApi", ItsmApiMock()),
        patch("backend.db_services.cmdb.biz.CCApi", CCApiMock()),
        patch("backend.components.cmsi.handler.CmsiHandler.send_msg", lambda msg: "有一条待办事项需要您处理"),
        patch("backend.db_services.cmdb.biz.Permission", PermissionMock),
    ]

    def apply_patches(self):
        """
        应用测试所需的所有patches。
        """
        self.mocks = [patcher.start() for patcher in self.patches]

    def setup(self):
        """
        测试的初始设置。
        """
        self.apply_patches()
        self.mocks[0].return_value = [AllowAny]
        self.mocks[1].return_value = ROOT_ID
        self.mocks[2].return_value = TicketStatus.SUCCEEDED
        self.mocks[3].return_value = TicketFlowStatus.SKIPPED

    def teardown(self):
        """
        测试完成后的清理工作。
        """
        for mock in self.mocks:
            if hasattr(mock, "stop"):
                mock.stop()

    def flow_test(self, client, ticket_data, is_pause=True):

        self.setup()
        client.login(username="admin")

        # itsm流程
        itsm_data = copy.deepcopy(ticket_data)
        client.post("/apis/tickets/", data=itsm_data)
        current_flow = Flow.objects.filter(flow_obj_id=SN).first()
        assert current_flow is not None

        if is_pause:
            # PAUSE流程
            client.post(f"/apis/tickets/{current_flow.ticket_id}/callback/")
            current_flow = Flow.objects.exclude(flow_obj_id="").last()
            assert current_flow.flow_type == FlowType.PAUSE

        # INNER_FLOW
        client.post(f"/apis/tickets/{current_flow.ticket_id}/callback/")
        current_flow = Flow.objects.exclude(flow_obj_id="").last()
        assert current_flow.flow_type == FlowType.INNER_FLOW
