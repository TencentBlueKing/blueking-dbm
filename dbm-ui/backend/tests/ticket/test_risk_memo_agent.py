# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DBM(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging
from unittest.mock import patch

import pytest
from blueapps.account.models import User
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.configuration.constants import DBType
from backend.db_services.risk_memo.constants import BizImpact, RiskOpType, RiskPriority, Status
from backend.db_services.risk_memo.models.risk_memo import RiskMemo, RiskMemoFollowUp, RiskOperateRecord
from backend.tests.mock_data import constant
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")
client = APIClient()


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """禁用中间件以简化测试"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture(scope="class", autouse=True)
def setup_class(django_db_setup, django_db_blocker):
    """设置测试类 - 创建用户并禁用权限验证"""
    with django_db_blocker.unblock():
        from backend.db_services.risk_memo.viewsets.risk_memo import RiskMemoViewSet

        # 使用 force_authenticate 确保认证生效
        admin_user, _ = User.objects.get_or_create(username="admin")
        client.force_authenticate(user=admin_user)

        # 三层权限 Mock
        patch.object(RiskMemoViewSet, "permission_classes", [AllowAny]).start()
        patch.object(RiskMemoViewSet, "get_permissions", lambda x: []).start()
        patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
        yield


# ===== Fixtures =====


@pytest.fixture
def risk_memo_bk_biz_id():
    """提供测试业务 ID"""
    return constant.BK_BIZ_ID


@pytest.fixture
def test_risk_memo(risk_memo_bk_biz_id):
    """创建单条风险备忘录"""
    risk = RiskMemo.objects.create(
        name="测试风险-MySQL主从延迟",
        bk_biz_id=risk_memo_bk_biz_id,
        level=RiskPriority.HIGH.value,
        status=Status.DOING.value,
        db_type=DBType.MySQL.value,
        description="MySQL主从复制延迟超过60秒",
        biz_inpact="online,login",
        inpact_cluster="cluster_a,cluster_b",
        is_special=False,
        creator="admin",
        updater="admin",
    )
    yield risk
    risk.delete()


@pytest.fixture
def test_risk_memo_with_followup(test_risk_memo):
    """创建带跟进记录的风险备忘录"""
    followup = RiskMemoFollowUp.objects.create(
        risk=test_risk_memo,
        content="已联系DBA排查主从延迟原因",
        creator="admin",
        updater="admin",
    )
    yield test_risk_memo, followup
    followup.delete()


@pytest.fixture
def test_risk_memo_special(risk_memo_bk_biz_id):
    """创建特殊业务风险备忘录"""
    risk = RiskMemo.objects.create(
        name="测试特殊风险-Redis内存溢出",
        bk_biz_id=risk_memo_bk_biz_id,
        level=RiskPriority.MIDDLE.value,
        status=Status.DOING.value,
        db_type=DBType.Redis.value,
        description="Redis实例内存超限",
        biz_inpact="experience",
        inpact_cluster="redis_cluster_1",
        is_special=True,
        creator="admin",
        updater="admin",
    )
    yield risk
    risk.delete()


@pytest.fixture
def test_multiple_risks(risk_memo_bk_biz_id):
    """创建多条风险备忘录用于列表测试"""
    risks = []
    configs = [
        {"name": "风险A-MySQL延迟", "level": RiskPriority.HIGH.value, "db_type": DBType.MySQL.value},
        {"name": "风险B-Redis内存", "level": RiskPriority.MIDDLE.value, "db_type": DBType.Redis.value},
        {"name": "风险C-ES磁盘", "level": RiskPriority.LOW.value, "db_type": DBType.Es.value},
    ]
    for cfg in configs:
        risk = RiskMemo.objects.create(
            name=cfg["name"],
            bk_biz_id=risk_memo_bk_biz_id,
            level=cfg["level"],
            status=Status.DOING.value,
            db_type=cfg["db_type"],
            description=f"{cfg['name']}的详细描述",
            biz_inpact="online",
            inpact_cluster="cluster_test",
            is_special=False,
            creator="admin",
            updater="admin",
        )
        risks.append(risk)
    yield risks
    for risk in risks:
        risk.delete()


@pytest.fixture
def test_risk_operate_record(test_risk_memo):
    """创建风险操作记录"""
    record = RiskOperateRecord.objects.create(
        risk=test_risk_memo,
        oper_type=RiskOpType.CREATE_RISK.value,
        creator="admin",
        updater="admin",
    )
    yield test_risk_memo, record
    record.delete()


class TestRiskMemoViewSet:
    """测试 RiskMemoViewSet - 使用 APIClient 通过真实 URL 路由"""

    # ===== Phase 1: 简单 GET action =====

    def test_list_risks(self, test_multiple_risks):
        """测试风险列表查询"""
        url = "/apis/risk_memo/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "results" in data
        assert "count" in data
        assert data["count"] == len(test_multiple_risks)

    def test_list_risks_with_filter(self, test_multiple_risks, risk_memo_bk_biz_id):
        """测试风险列表查询 - 带过滤条件"""
        url = "/apis/risk_memo/"
        response = client.get(
            url,
            {
                "bk_biz_id": risk_memo_bk_biz_id,
                "level": RiskPriority.HIGH.value,
                "status": Status.DOING.value,
                "limit": 10,
                "offset": 0,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        # 过滤结果应只包含 HIGH 等级的风险
        for item in data["results"]:
            assert item["level"] == RiskPriority.HIGH.value

    def test_retrieve_risk(self, test_risk_memo_with_followup):
        """测试风险详情查询（含跟进记录）"""
        risk, followup = test_risk_memo_with_followup
        url = f"/apis/risk_memo/{risk.id}/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["id"] == risk.id
        assert data["name"] == risk.name
        # retrieve 使用 RiskMemoDtailSerializer，应包含 follow_ups 字段
        assert "follow_ups" in data
        assert isinstance(data["follow_ups"], list)
        assert len(data["follow_ups"]) == 1
        # biz_inpact 和 inpact_cluster 应被序列化为列表
        assert isinstance(data["biz_inpact"], list)
        assert isinstance(data["inpact_cluster"], list)

    def test_get_biz_inpact_list(self):
        """测试获取业务影响类型列表"""
        url = "/apis/risk_memo/get_biz_inpact_list/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) == len(BizImpact)
        # 验证每个枚举项都有 value 和 label
        for item in data:
            assert "value" in item
            assert "label" in item

    def test_get_risk_operate_records(self, test_risk_operate_record):
        """测试获取风险操作记录日志"""
        risk, record = test_risk_operate_record
        url = "/apis/risk_memo/get_risk_operate_records/"
        response = client.get(url, {"risk": risk.id, "limit": 10, "offset": 0})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "results" in data
        assert "count" in data
        assert data["count"] == 1
        # 验证记录的操作类型
        record_data = data["results"][0]
        assert record_data["oper_type"] == RiskOpType.CREATE_RISK.value

    # ===== Phase 2: 写操作 action =====

    def test_create_risk(self, risk_memo_bk_biz_id):
        """测试新建风险"""
        url = "/apis/risk_memo/"
        payload = {
            "name": "新建测试风险-Kafka消费延迟",
            "bk_biz_id": risk_memo_bk_biz_id,
            "level": RiskPriority.MIDDLE.value,
            "status": Status.DOING.value,
            "db_type": DBType.Kafka.value,
            "description": "Kafka消费者组延迟超过1000条",
            "biz_inpact": "activity",
            "inpact_cluster": "kafka_cluster_1",
            "is_special": False,
        }
        response = client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()["data"]
        assert data["name"] == payload["name"]
        assert data["bk_biz_id"] == risk_memo_bk_biz_id
        assert data["level"] == RiskPriority.MIDDLE.value

        # DB 状态断言：验证风险已写入数据库
        created_risk = RiskMemo.objects.get(id=data["id"])
        assert created_risk.name == payload["name"]
        assert created_risk.db_type == DBType.Kafka.value

        # 验证 log_operation 装饰器创建了操作记录
        assert RiskOperateRecord.objects.filter(risk=created_risk, oper_type=RiskOpType.CREATE_RISK.value).exists()

        # 清理
        RiskOperateRecord.objects.filter(risk=created_risk).delete()
        created_risk.delete()

    def test_create_risk_special(self, risk_memo_bk_biz_id):
        """测试新建特殊风险 - 验证 is_special 标志和特殊操作类型"""
        url = "/apis/risk_memo/"
        payload = {
            "name": "新建特殊风险-核心业务MySQL故障",
            "bk_biz_id": risk_memo_bk_biz_id,
            "level": RiskPriority.HIGH.value,
            "status": Status.DOING.value,
            "db_type": DBType.MySQL.value,
            "description": "核心业务MySQL集群故障",
            "biz_inpact": "online,recharge",
            "inpact_cluster": "mysql_core_cluster",
            "is_special": True,
        }
        response = client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()["data"]
        assert data["is_special"] is True

        # DB 状态断言
        created_risk = RiskMemo.objects.get(id=data["id"])
        assert created_risk.is_special is True

        # 验证特殊风险使用了 RISK_REQUIRE_MAP 中的操作类型
        assert RiskOperateRecord.objects.filter(risk=created_risk, oper_type=RiskOpType.CREATE_REQUIRE.value).exists()

        # 清理
        RiskOperateRecord.objects.filter(risk=created_risk).delete()
        created_risk.delete()

    def test_update_risk(self, test_risk_memo):
        """测试更新风险"""
        url = f"/apis/risk_memo/{test_risk_memo.id}/"
        payload = {
            "name": "更新后的风险名称-MySQL主从修复中",
            "bk_biz_id": test_risk_memo.bk_biz_id,
            "level": RiskPriority.LOW.value,
            "status": Status.DOING.value,
            "db_type": DBType.MySQL.value,
            "description": "MySQL主从延迟已降低，持续观察中",
            "biz_inpact": "online",
            "inpact_cluster": "cluster_a",
            "is_special": False,
        }
        response = client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["name"] == payload["name"]
        assert data["level"] == RiskPriority.LOW.value

        # DB 状态断言
        test_risk_memo.refresh_from_db()
        assert test_risk_memo.name == payload["name"]
        assert test_risk_memo.level == RiskPriority.LOW.value

        # 验证 log_operation 创建了更新操作记录
        assert RiskOperateRecord.objects.filter(risk=test_risk_memo, oper_type=RiskOpType.UPDATE_RISK.value).exists()

        # 清理操作记录
        RiskOperateRecord.objects.filter(risk=test_risk_memo).delete()

    # ===== Phase 3: 复杂状态管理 action =====

    def test_update_risk_status_to_done(self, test_risk_memo):
        """测试更新风险状态为结项"""
        url = f"/apis/risk_memo/{test_risk_memo.id}/update_risk_status/"
        payload = {
            "status": Status.DONE.value,
            "final_content": "风险已处理完毕，主从延迟恢复正常",
        }
        response = client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["status"] == Status.DONE.value

        # DB 状态断言：验证结项信息已填充
        test_risk_memo.refresh_from_db()
        assert test_risk_memo.status == Status.DONE.value
        assert test_risk_memo.final_content == payload["final_content"]
        assert test_risk_memo.finalist == "admin"
        assert test_risk_memo.final_time is not None
        # 风险刚创建就结项，持续时间应为 0
        assert test_risk_memo.duration_time == 0

        # 验证操作记录
        assert RiskOperateRecord.objects.filter(risk=test_risk_memo, oper_type=RiskOpType.FINAL.value).exists()

        # 清理操作记录
        RiskOperateRecord.objects.filter(risk=test_risk_memo).delete()

    def test_update_risk_status_restart(self, test_risk_memo):
        """测试从结项状态重启风险"""
        # 先将风险设为结项状态
        test_risk_memo.status = Status.DONE.value
        test_risk_memo.final_content = "已结项"
        test_risk_memo.finalist = "admin"
        test_risk_memo.save()

        url = f"/apis/risk_memo/{test_risk_memo.id}/update_risk_status/"
        payload = {
            "status": Status.DOING.value,
        }
        response = client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["status"] == Status.DOING.value

        # DB 状态断言：验证结项信息已清除
        test_risk_memo.refresh_from_db()
        assert test_risk_memo.status == Status.DOING.value
        assert test_risk_memo.final_content == ""
        assert test_risk_memo.finalist == ""
        assert test_risk_memo.final_time is None
        assert test_risk_memo.duration_time == 0

        # 验证操作记录为重启类型
        assert RiskOperateRecord.objects.filter(risk=test_risk_memo, oper_type=RiskOpType.RESTART_RISK.value).exists()

        # 清理操作记录
        RiskOperateRecord.objects.filter(risk=test_risk_memo).delete()

    def test_update_risk_status_special_done(self, test_risk_memo_special):
        """测试特殊风险结项 - 应使用特殊操作类型"""
        risk = test_risk_memo_special
        url = f"/apis/risk_memo/{risk.id}/update_risk_status/"
        payload = {
            "status": Status.DONE.value,
            "final_content": "特殊风险已处理",
        }
        response = client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK

        # DB 状态断言
        risk.refresh_from_db()
        assert risk.status == Status.DONE.value

        # 验证特殊风险使用了 FINAL_REQUIRE 操作类型
        assert RiskOperateRecord.objects.filter(risk=risk, oper_type=RiskOpType.FINAL_REQUIRE.value).exists()

        # 清理操作记录
        RiskOperateRecord.objects.filter(risk=risk).delete()

    def test_update_risk_status_special_restart(self, test_risk_memo_special):
        """测试特殊风险重启 - 应使用 RESTART_REQUIRE 操作类型"""
        risk = test_risk_memo_special
        # 先将风险设为结项状态
        risk.status = Status.DONE.value
        risk.final_content = "已结项"
        risk.finalist = "admin"
        risk.save()

        url = f"/apis/risk_memo/{risk.id}/update_risk_status/"
        payload = {
            "status": Status.DOING.value,
        }
        response = client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK

        # DB 状态断言
        risk.refresh_from_db()
        assert risk.status == Status.DOING.value

        # 验证特殊风险使用了 RESTART_REQUIRE 操作类型
        assert RiskOperateRecord.objects.filter(risk=risk, oper_type=RiskOpType.RESTART_REQUIRE.value).exists()

        # 清理操作记录
        RiskOperateRecord.objects.filter(risk=risk).delete()

    # ===== Phase 4: 异常处理分支 =====

    @patch("backend.db_services.risk_memo.viewsets.risk_memo.RiskMemo.objects.handler_risk_status")
    def test_update_risk_status_exception(self, mock_handler, test_risk_memo):
        """测试更新风险状态异常 - handler_risk_status 抛出异常"""
        mock_handler.side_effect = Exception("数据库连接失败")

        url = f"/apis/risk_memo/{test_risk_memo.id}/update_risk_status/"
        payload = {
            "status": Status.DONE.value,
            "final_content": "测试异常处理",
        }
        response = client.post(url, payload, format="json")

        # 异常被捕获，返回 JsonResponse（code=1）
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 1
        assert "数据库连接失败" in data["msg"]
