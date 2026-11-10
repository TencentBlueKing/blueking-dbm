# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

redis-portrait-generator 终局输出（SKILL.md「终局输出契约」）与 PortraitResponseParser 的对齐校验。
"""
from unittest.mock import patch

import pytest

from backend.db_report.portrait.generator.parser import PortraitResponseParser

REPORT_URL = "https://bk-dbm.example.com/ai-chat/share/2c1f0e88-33b0-4a2f-9a2b-1a2b3c4d5e6f/"

AUTO_DONE_OUTPUT = (
    "集群 cache.portrait-redis.test.db 画像已生成，健康状态：warning。\n"
    f'[ai_result]{{"ai_status": true, "report_url": "{REPORT_URL}", "report_score": 72, "message": ""}}[ai_result]'
)

AUTO_DONE_UNKNOWN_SCORE_OUTPUT = (
    f'[ai_result]{{"ai_status": true, "report_url": "{REPORT_URL}", "report_score": -1, "message": ""}}[ai_result]'
)

ABORT_OUTPUT = (
    'ABORT: cluster_basic_overview 未找到集群 "cache.missing.test.db"\n'
    '[ai_result]{"ai_status": false, "report_url": "", "report_score": -1, '
    '"message": "cluster_basic_overview 未找到集群 \\"cache.missing.test.db\\""}[ai_result]'
)

MISSING_PARAM_OUTPUT = (
    "无法继续生成集群画像报告，缺少以下关键参数：\n"
    "- since：画像时间窗起点；请通过 ISO8601 时间提供。\n"
    "请补齐后重新发起。本 Skill 不会自行猜测或反查这些参数。\n"
    '[ai_result]{"ai_status": false, "report_url": "", "report_score": -1, "message": "缺少参数：since"}[ai_result]'
)


@pytest.fixture
def parse():
    parser = PortraitResponseParser()

    def run(raw):
        # Tier 1 must hit on its own; the URL-regex fallback is not allowed to rescue these outputs.
        with patch.object(
            PortraitResponseParser, "_try_share_url_fallback", side_effect=AssertionError("fallback used")
        ):
            return parser.parse(raw)

    return run


def test_auto_done_parses_score_and_url(parse):
    result = parse(AUTO_DONE_OUTPUT)
    assert result.parsed_ok is True
    assert result.ai_ok is True
    assert result.score == 72
    assert result.share_url == REPORT_URL


def test_auto_done_keeps_unknown_score(parse):
    result = parse(AUTO_DONE_UNKNOWN_SCORE_OUTPUT)
    assert result.parsed_ok is True
    assert result.ai_ok is True
    assert result.score == -1


@pytest.mark.parametrize(
    "raw,reason",
    [
        (ABORT_OUTPUT, 'cluster_basic_overview 未找到集群 "cache.missing.test.db"'),
        (MISSING_PARAM_OUTPUT, "缺少参数：since"),
    ],
)
def test_abort_branches_parse_as_ai_rejected(parse, raw, reason):
    result = parse(raw)
    assert result.parsed_ok is True
    assert result.ai_ok is False
    assert result.score == -1
    assert result.share_url == ""
    assert result.summary == reason
