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

    def test_issued_tokens_are_unique_scoped_and_have_no_expiry(self):
        with patch.object(callback_token, "env", SimpleNamespace(BK_SAAS_CALLBACK_URL="https://dbm.test")):
            first = callback_token.build_job_callback_url("push_conf_callback")
            second = callback_token.build_job_callback_url("push_conf_callback")
        self.assertNotEqual(first, second)
        token = parse_qs(urlsplit(first).query)["token"][0]
        key, uses = self.redis.set.call_args_list[0].args
        self.assertEqual(key, callback_token._token_key("push_conf_callback", token))
        self.assertNotIn(token, key)
        self.assertEqual(uses, callback_token.JOB_CALLBACK_TOKEN_MAX_USES)
        for call in self.redis.set.call_args_list:
            self.assertEqual(call.kwargs, {})
        self.redis.expire.assert_not_called()
        self.assertNotEqual(key, callback_token._token_key("delete_conf_callback", token))

    def test_missing_and_malformed_tokens_are_rejected_without_redis(self):
        for token in (None, "", "invalid", "a" * 1000, [], 123):
            with self.subTest(token=token), self.assertRaises(PermissionDenied):
                callback_token.verify_job_callback_token("push_conf_callback", token)
        self.redis.eval.assert_not_called()

    def test_valid_token_is_consumed_atomically(self):
        self.redis.eval.return_value = 1
        callback_token.verify_job_callback_token("push_conf_callback", "a" * 43)
        self.redis.eval.assert_called_once_with(
            callback_token._CONSUME_TOKEN_SCRIPT,
            1,
            callback_token._token_key("push_conf_callback", "a" * 43),
        )

    def test_missing_exhausted_or_wrong_action_token_is_rejected(self):
        self.redis.eval.return_value = 0
        with self.assertRaises(PermissionDenied):
            callback_token.verify_job_callback_token("restart_callback", "a" * 43)

    def test_redis_failure_does_not_bypass_authentication(self):
        self.redis.eval.side_effect = ConnectionError("Redis unavailable")
        with self.assertRaises(ConnectionError):
            callback_token.verify_job_callback_token("inspect_conf_callback", "a" * 43)
