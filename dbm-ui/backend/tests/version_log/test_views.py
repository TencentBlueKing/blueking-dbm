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
import json

import pytest

from backend.utils.pytest import AuthorizedAPIRequestFactory, force_authenticate
from backend.version_log import views

pytestmark = pytest.mark.django_db

factory = AuthorizedAPIRequestFactory()


class TestVersionLogViewSet:
    def test_list_version_logs(self, bk_user):
        """测试获取版本日志列表"""
        request = factory.get("/version_log/version_logs_list/")
        force_authenticate(request, user=bk_user)
        response = views.version_logs_list(request)
        data = json.loads(response.content)
        # 根据实际响应结构进行断言
        assert data["result"] is True
        assert data["code"] == 0
        assert data["message"] == "日志列表获取成功"
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        # 验证data中的每个元素都是包含版本号和日期的列表
        for item in data["data"]:
            assert isinstance(item, list)
            assert len(item) == 2  # 每个元素包含版本号和日期
            assert isinstance(item[0], str)  # 版本号是字符串
            assert isinstance(item[1], str)  # 日期是字符串

    def test_get_version_log_detail(self, bk_user):
        """测试获取单个版本日志详情"""
        request = factory.get("/version_log/version_log_detail/?log_version=V1.5.0-alpha.82")
        force_authenticate(request, user=bk_user)
        response = views.get_version_log_detail(request)
        data = json.loads(response.content)
        assert data["result"] is True
        assert data["code"] == 0
        assert data["message"] == "日志详情获取成功"
        assert isinstance(data["data"], str)
        # 验证data字段包含版本信息
        assert "1.5.0-alpha.82" in data["data"]
        assert "2026-01-30" in data["data"]

    def test_path_traversal_attack(self, bk_user):
        """测试路径穿越攻击防护"""
        # 测试各种路径穿越攻击向量
        path_traversal_vectors = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "V1.5.0/../../../etc/passwd",
            "../../V1.5.0/../../etc/passwd",
            "V1.5.0-alpha.82/../../../../etc/passwd",
            "./../../etc/passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "../../../../../../../../etc/passwd",
            "..%2f..%2f..%2fetc%2fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
        ]

        for vector in path_traversal_vectors:
            request = factory.get(f"/version_log/version_log_detail/?log_version={vector}")
            force_authenticate(request, user=bk_user)
            request.user = bk_user
            response = views.get_version_log_detail(request)
            data = json.loads(response.content)

            # 验证系统正确处理了路径穿越攻击
            assert data["result"] is False
            assert data["code"] == -1
            assert data["data"] is None
            assert data["message"] == "版本参数不合法"

    def test_path_traversal_with_normalized_version(self, bk_user):
        """测试对规范化版本号的路径穿越攻击"""
        # 测试在正常版本号中嵌入路径穿越字符
        malicious_versions = [
            "V1.5.0/../V1.5.0",
            "V1.5.0-alpha.82/../../V1.5.0-alpha.82",
            "V1.5.0\\..\\V1.5.0",
            "V1.5.0%2f..%2fV1.5.0",
        ]

        for version in malicious_versions:
            request = factory.get(f"/version_log/version_log_detail/?log_version={version}")
            force_authenticate(request, user=bk_user)
            request.user = bk_user
            response = views.get_version_log_detail(request)
            data = json.loads(response.content)

            assert data["result"] is False
            assert data["code"] == -1
            assert data["data"] is None
            assert data["message"] == "版本参数不合法"

    def test_has_user_read_latest_with_different_users(self, bk_user):
        """测试不同用户的阅读状态"""
        # 测试当前用户
        request = factory.get("/version_log/has_user_read_latest/")
        force_authenticate(request, user=bk_user)
        request.user = bk_user

        response = views.has_user_read_latest(request)
        data = json.loads(response.content)

        assert data["result"] is True
