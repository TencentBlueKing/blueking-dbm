from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from rest_framework.exceptions import PermissionDenied

from backend.db_proxy.views.job_callback import token as callback_token


class TestJobCallbackToken(TestCase):
    def setUp(self):
        self.redis_patch = patch.object(callback_token, "RedisConn")
        self.redis = self.redis_patch.start()
        self.addCleanup(self.redis_patch.stop)

    def test_issued_tokens_are_unique_scoped_and_expire_after_24_hours(self):
        with patch.object(callback_token, "env", SimpleNamespace(BK_SAAS_CALLBACK_URL="https://dbm.test")):
            first = callback_token.build_job_callback_url("push_conf_callback")
            second = callback_token.build_job_callback_url("push_conf_callback")
        self.assertNotEqual(first, second)
        token = parse_qs(urlsplit(first).query)["token"][0]
        key, value = self.redis.set.call_args_list[0].args
        self.assertEqual(key, callback_token._token_key("push_conf_callback", token))
        self.assertNotIn(token, key)
        self.assertEqual(value, "valid")
        for call in self.redis.set.call_args_list:
            self.assertEqual(call.kwargs, {"ex": 24 * 60 * 60})
        self.assertNotEqual(key, callback_token._token_key("delete_conf_callback", token))

    def test_missing_and_malformed_tokens_are_rejected_without_redis(self):
        for token in (None, "", "invalid", "a" * 1000, [], 123):
            with self.subTest(token=token), self.assertRaises(PermissionDenied):
                callback_token.verify_job_callback_token("push_conf_callback", token)
        self.redis.exists.assert_not_called()

    def test_valid_token_is_not_deleted_during_verification(self):
        self.redis.exists.return_value = 1
        key = callback_token.verify_job_callback_token("push_conf_callback", "a" * 43)
        self.assertEqual(key, callback_token._token_key("push_conf_callback", "a" * 43))
        self.redis.exists.assert_called_once_with(key)
        self.redis.delete.assert_not_called()

    def test_missing_expired_or_wrong_action_token_is_rejected(self):
        self.redis.exists.return_value = 0
        with self.assertRaises(PermissionDenied):
            callback_token.verify_job_callback_token("restart_callback", "a" * 43)

    def test_redis_failure_does_not_bypass_authentication(self):
        self.redis.exists.side_effect = ConnectionError("Redis unavailable")
        with self.assertRaises(ConnectionError):
            callback_token.verify_job_callback_token("inspect_conf_callback", "a" * 43)


class TestJobCallbackTokenCleanup(TestCase):
    def test_only_successful_authenticated_responses_delete_token(self):
        from rest_framework.response import Response

        from backend.db_proxy.views.job_callback.views import JobCallBackViewSet
        from backend.db_proxy.views.views import BaseProxyPassViewSet

        for status, exception, authenticated, should_delete in (
            (200, False, True, True),
            (400, False, True, False),
            (500, True, True, False),
            (200, True, True, False),
            (403, True, False, False),
        ):
            with self.subTest(status=status, exception=exception, authenticated=authenticated):
                view = JobCallBackViewSet()
                if authenticated:
                    view.callback_token_key = "test-callback-key"
                response = Response(status=status)
                response.exception = exception
                with (
                    patch("backend.db_proxy.views.job_callback.views.RedisConn") as redis,
                    patch.object(BaseProxyPassViewSet, "finalize_response", return_value=response),
                ):
                    view.finalize_response(None, response)
                if should_delete:
                    redis.delete.assert_called_once_with("test-callback-key")
                else:
                    redis.delete.assert_not_called()
