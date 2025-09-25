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
from django.utils.translation import ugettext as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

BKREPO_RISK_MEMO_PATH = "risk_memo/{biz}/{file}"

# 图片支持的格式
SUPPORTED_IMAGE_TYPES = ["jpeg", "png", "gif"]

# 最大上传图片64M
IMAGE_MAX_MB = 64


class Status(str, StructuredEnum):
    """
    风险状态
    """

    DOING = EnumField("backlog", _("进行中"))
    DONE = EnumField("done", _("结项"))


class BizImpact(str, StructuredEnum):
    """
    业务影响枚举类
    """

    ONLINE = EnumField("online", _("在线"))
    LOGIN = EnumField("login", _("登录"))
    EXPERIENCE = EnumField("experience", _("体验"))
    RECHARGE = EnumField("recharge", _("充值"))
    ACTIVITY = EnumField("activity", _("活动"))
    OTHER = EnumField("other", _("其他"))


class RiskPriority(StructuredEnum):
    """
    风险等级
    """

    LOW = EnumField("Low", _("低"))
    MIDDLE = EnumField("Middle", _("中"))
    HIGH = EnumField("High", _("高"))


class RiskOpType(str, StructuredEnum):
    """风险操作类型枚举"""

    CREATE_RISK = EnumField("create_risk", _("创建风险"))
    CREATE_REQUIRE = EnumField("create_require", _("创建要求"))
    CREATE_FOLLOW_UP = EnumField("create_follow_up", _("添加跟进"))
    UPDATE_RISK = EnumField("update_risk", _("修改风险"))
    UPDATE_REQUIRE = EnumField("update_require", _("修改要求"))
    UPDATE_FOLLOW_UP = EnumField("update_follow_up", _("修改跟进内容"))
    REMOVE_RISK = EnumField("delete_risk", _("删除风险"))
    REMOVE_FOLLOW_UP = EnumField("delete_follow_up", _("删除跟进"))
    RESTART_RISK = EnumField("restart_risk", _("重启风险"))
    RESTART_REQUIRE = EnumField("restart_require", _("重启要求"))
    FINAL = EnumField("final", _("结项"))
    FINAL_REQUIRE = EnumField("final_require", _("标记为失效"))


RISK_REQUIRE_MAP = {
    RiskOpType.CREATE_RISK.value: RiskOpType.CREATE_REQUIRE.value,
    RiskOpType.UPDATE_RISK.value: RiskOpType.UPDATE_REQUIRE.value,
    RiskOpType.RESTART_RISK.value: RiskOpType.RESTART_REQUIRE.value,
    RiskOpType.FINAL.value: RiskOpType.FINAL_REQUIRE.value,
}
