from datetime import datetime, timezone

from django.db import models

from backend.db_services.risk_memo.constants import Status


class RiskMemoManager(models.Manager):
    """风险备忘录 管理"""

    def handler_risk_status(self, request, validated_data: dict, risk):
        """处理风险状态"""
        if validated_data["status"] == Status.DONE.value:
            # 如果当前状态转为结项 补充结项信息
            risk.final_content = validated_data.pop("final_content", "")
            risk.final_time = datetime.now(timezone.utc)
            risk.finalist = request.user.username
            risk.status = validated_data["status"]
            risk.duration_time = (risk.final_time - risk.create_at).total_seconds()
            risk.save()

        # 如果当前状态是已结项 触发重启时 清除掉结项信息
        elif risk.status == Status.DONE.value and validated_data["status"] != Status.DONE.value:
            risk.final_content = ""
            risk.final_time = None
            risk.finalist = ""
            risk.duration_time = 0
            risk.status = validated_data["status"]
            risk.save()
        else:
            super().update(**validated_data)


class RiskMemoFollowUpManager(models.Manager):
    def get_is_follow_up_owner(self, request, follow_up) -> bool:
        """
        获取当前用户是否为负责人+系统管理员
        """
        if request.user.is_superuser:
            return True
        else:
            return request.user.username == follow_up.creator
