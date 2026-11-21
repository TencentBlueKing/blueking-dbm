from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from backend.components.itsm.backends.v4 import ItsmV4Backend
from backend.ticket.constants import FlowType
from backend.ticket.itsm_callback import get_callback_token, verify_callback


@override_settings(SECRET_KEY="test-callback-secret")
class TestItsmCallback(SimpleTestCase):
    def setUp(self):
        self.flow = SimpleNamespace(flow_type=FlowType.BK_ITSM, flow_obj_id="REQ123")
        self.ticket = SimpleNamespace(pk=123, current_flow=Mock(return_value=self.flow))
        self.api_patch = patch("backend.components.itsm.backends.v3.ItsmV3Backend.verify_token")
        self.verify_token = self.api_patch.start()
        self.addCleanup(self.api_patch.stop)

    def test_missing_and_malformed_tokens_are_rejected(self):
        for token in (None, "", [], {}, 123):
            with self.subTest(token=token), self.assertRaises(PermissionDenied):
                verify_callback(self.ticket, {"token": token})
        self.verify_token.assert_not_called()

    def test_v3_verifies_token_remotely(self):
        self.verify_token.return_value = {"is_passed": True}
        verify_callback(self.ticket, {"token": "remote-token"})
        self.verify_token.assert_called_once_with({"token": "remote-token"}, use_admin=True)

    def test_v3_rejects_invalid_results_and_propagates_verification_failure(self):
        for result in ({"is_passed": False}, {}, None, False, {"is_passed": "true"}, {"is_passed": 1}):
            self.verify_token.return_value = result
            with self.subTest(result=result), self.assertRaises(PermissionDenied):
                verify_callback(self.ticket, {"token": "invalid"})
        self.verify_token.side_effect = RuntimeError("verification unavailable")
        with self.assertRaises(RuntimeError):
            verify_callback(self.ticket, {"token": "invalid"})

    def test_v4_verifies_ticket_bound_token(self):
        self.flow.flow_obj_id = "ITSM_V4:456"
        verify_callback(self.ticket, {"callback_token": get_callback_token(self.ticket.pk)})
        for token in (None, "", [], {}, 123, "invalid", get_callback_token(124)):
            with self.subTest(token=token), self.assertRaises(PermissionDenied):
                verify_callback(self.ticket, {"callback_token": token})
        with self.assertRaises(PermissionDenied):
            verify_callback(self.ticket, {"token": get_callback_token(self.ticket.pk)})
        self.verify_token.assert_not_called()

    def test_non_itsm_and_uncreated_flows_are_rejected(self):
        for flow in (
            None,
            SimpleNamespace(flow_type="INNER_FLOW"),
            SimpleNamespace(flow_type=FlowType.BK_ITSM, flow_obj_id=""),
        ):
            self.ticket.current_flow.return_value = flow
            with self.subTest(flow=flow), self.assertRaises(PermissionDenied):
                verify_callback(self.ticket, {"token": "token"})
        self.verify_token.assert_not_called()

    @patch("backend.components.itsm.backends.v4.ItsmV4Api")
    def test_v4_creation_injects_token_without_mutating_params(self, itsm_api):
        create_ticket = itsm_api.create_ticket
        create_ticket.return_value = {"id": 456}
        for params in (
            {"meta": {"callback_url": "https://dbm.example/apis/tickets/123/callback/"}},
            {"callback_url": "https://dbm.example/apis/tickets/123/callback/", "form_data": {}},
        ):
            with self.subTest(params=params):
                result = ItsmV4Backend().create_ticket(params)
                self.assertEqual(result, {"sn": "ITSM_V4:456"})
                self.assertEqual(create_ticket.call_args.args[0]["callback_token"], get_callback_token(123))
                self.assertNotIn("callback_token", params)
