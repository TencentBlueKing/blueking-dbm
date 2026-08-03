# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import pytest

pytestmark = pytest.mark.django_db

_RID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
_OTHER = "11111111-2222-3333-4444-555555555555"
_ABS_URL = f"https://dbm.example.com/ai-chat/share/{_RID}/"


def test_parse_pure_json_success(parse_result_mod):
    res = parse_result_mod.parse_config_ai_inspect_res(
        f'{{"report_id": "{_RID}", "share_url": "{_ABS_URL}", "summary": "ok"}}'
    )
    assert res == {"report_id": _RID, "share_url": _ABS_URL, "summary": "ok"}


def test_parse_fenced_json_with_prose(parse_result_mod):
    url_no_slash = _ABS_URL.rstrip("/")
    text = (
        "分析过程说明若干字...\n"
        "```json\n"
        f'{{"report_id": "{_RID}", "share_url": "{url_no_slash}", "summary": "有建议"}}\n'
        "```\n"
        "补充说明"
    )
    res = parse_result_mod.parse_config_ai_inspect_res(text)
    assert res is not None
    assert res["report_id"] == _RID
    assert res["share_url"] == url_no_slash
    assert res["summary"] == "有建议"


def test_parse_missing_summary_still_success(parse_result_mod):
    res = parse_result_mod.parse_config_ai_inspect_res(f'{{"report_id": "{_RID}", "share_url": "{_ABS_URL}"}}')
    assert res == {"report_id": _RID, "share_url": _ABS_URL, "summary": ""}


def test_parse_relative_share_url_fails(parse_result_mod):
    res = parse_result_mod.parse_config_ai_inspect_res(
        f'{{"report_id": "{_RID}", "share_url": "/ai-chat/share/{_RID}/", "summary": "x"}}'
    )
    assert res is None


def test_parse_missing_report_id_fails(parse_result_mod):
    res = parse_result_mod.parse_config_ai_inspect_res(f'{{"share_url": "{_ABS_URL}", "summary": "x"}}')
    assert res is None


def test_parse_mismatched_uuid_fails(parse_result_mod):
    bad_url = f"https://dbm.example.com/ai-chat/share/{_OTHER}/"
    res = parse_result_mod.parse_config_ai_inspect_res(
        f'{{"report_id": "{_RID}", "share_url": "{bad_url}", "summary": "x"}}'
    )
    assert res is None


def test_parse_regex_fallback_from_prose(parse_result_mod):
    text = f'some prose "report_id": "{_RID}" and link ' f"https://dbm.example.com/ai-chat/share/{_RID}/ done"
    res = parse_result_mod.parse_config_ai_inspect_res(text)
    assert res == {"report_id": _RID, "share_url": _ABS_URL, "summary": ""}


def test_parse_regex_mismatched_uuid_fails(parse_result_mod):
    text = f'"report_id": "{_RID}" url https://dbm.example.com/ai-chat/share/{_OTHER}/'
    assert parse_result_mod.parse_config_ai_inspect_res(text) is None
