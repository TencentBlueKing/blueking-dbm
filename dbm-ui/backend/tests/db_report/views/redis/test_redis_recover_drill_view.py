# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import patch


def _make_report_row(bk_biz_id=100):
    return SimpleNamespace(
        bk_biz_id=bk_biz_id,
        ticket_id=123,
        rollback_flow_obj_id="rollback-root",
        delete_flow_obj_id="delete-root",
    )


def test_redis_rollback_exercise_flow_links_use_configured_biz():
    from backend.db_report.views.redis import redis_recover_drill_view as view

    serializer = view.RedisRecoverDrillTaskSerializer()
    obj = _make_report_row(bk_biz_id=100)

    with patch(
        "backend.db_services.redis.rollback.config.RedisRollbackExerciseConfig.from_settings",
        return_value=SimpleNamespace(bk_biz_id=200),
    ) as mock_from_settings:
        assert (
            serializer.get_rollback_flow_link(obj)
            == f"{view.BK_SAAS_HOST}/200/task-history/detail/rollback-root?from=taskHistoryList"
        )
        assert (
            serializer.get_delete_flow_link(obj)
            == f"{view.BK_SAAS_HOST}/200/task-history/detail/delete-root?from=taskHistoryList"
        )

    mock_from_settings.assert_called_once_with()


def test_redis_rollback_exercise_flow_links_fallback_to_report_biz_when_config_unset():
    from backend.db_report.views.redis import redis_recover_drill_view as view

    serializer = view.RedisRecoverDrillTaskSerializer()
    obj = _make_report_row(bk_biz_id=100)

    with patch(
        "backend.db_services.redis.rollback.config.RedisRollbackExerciseConfig.from_settings",
        return_value=SimpleNamespace(bk_biz_id=0),
    ):
        assert (
            serializer.get_rollback_flow_link(obj)
            == f"{view.BK_SAAS_HOST}/100/task-history/detail/rollback-root?from=taskHistoryList"
        )
        assert (
            serializer.get_delete_flow_link(obj)
            == f"{view.BK_SAAS_HOST}/100/task-history/detail/delete-root?from=taskHistoryList"
        )


def test_redis_rollback_exercise_ticket_link():
    from backend.db_report.views.redis import redis_recover_drill_view as view

    serializer = view.RedisRecoverDrillTaskSerializer()
    obj = _make_report_row(bk_biz_id=100)

    assert serializer.get_ticket_link(obj) == f"{view.BK_SAAS_HOST}/ticket/123"


def test_redis_rollback_exercise_ticket_link_missing_ticket_id_returns_none():
    from backend.db_report.views.redis import redis_recover_drill_view as view

    serializer = view.RedisRecoverDrillTaskSerializer()
    obj = _make_report_row(bk_biz_id=100)
    obj.ticket_id = 0

    assert serializer.get_ticket_link(obj) is None
