# -*- coding: utf-8 -*-
from backend.flow.utils.exec_host.lease import root_ids_from_tags, tags_after_acquire, tags_after_release


def test_acquire_keeps_existing_holder():
    tags = tags_after_acquire({"dts_root_id": "a"}, "b")
    assert root_ids_from_tags(tags) == ["a", "b"]
    assert tags["dts_root_id"] == "b"


def test_release_creator_while_reuser_remains():
    tags = tags_after_acquire({"dts_root_id": "a", "dts_root_ids": ["a"]}, "b")
    tags, remaining = tags_after_release(tags, "a")
    assert remaining == ["b"]
    assert tags["dts_root_id"] == "b"


def test_release_last_holder_clears_refs():
    tags, remaining = tags_after_release({"dts_root_id": "a", "dts_root_ids": ["a"]}, "a")
    assert remaining == []
    assert tags["dts_root_id"] == ""
    assert tags["dts_root_ids"] == []
