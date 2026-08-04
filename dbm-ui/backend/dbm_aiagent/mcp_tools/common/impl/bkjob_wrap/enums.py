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
from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, IntStructuredEnum


class BkJobIntEnum(IntStructuredEnum):
    """作业平台状态码基类，未知码降级为动态成员。"""

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, int):
            return None
        pseudo = int.__new__(cls, value)
        pseudo._name_ = f"UNKNOWN_{value}"
        pseudo._value_ = value
        pseudo.__init__(value)
        cls._member_map_[pseudo._name_] = pseudo
        cls._value2member_map_[value] = pseudo
        return pseudo

    @classmethod
    def get_choice_label(cls, value):
        label = super().get_choice_label(value)
        if isinstance(label, int):
            return _("未知状态码({})").format(label)
        return label


class BkJobInstanceStatus(BkJobIntEnum):
    """作业状态码"""

    NORMAL = EnumField(0, _("正常"))
    NOT_RUNNING = EnumField(1, _("未执行"))
    RUNNING = EnumField(2, _("正在执行"))
    SUCCESS = EnumField(3, _("执行成功"))
    FAILED = EnumField(4, _("执行失败"))
    SKIPPED = EnumField(5, _("跳过"))
    IGNORE_ERROR = EnumField(6, _("忽略错误"))
    WAITING = EnumField(7, _("等待用户"))
    MANUAL_TERMINAL = EnumField(8, _("手动结束"))
    ABNORMAL_STATE = EnumField(9, _("状态异常"))
    BEING_FORCIBLY_TERMINATED = EnumField(10, _("步骤强制终止中"))
    SUCCESS_FORCIBLY_TERMINATED = EnumField(11, _("步骤强制终止成功"))


class BkJobStepStatus(BkJobIntEnum):
    """步骤 IP 执行状态码"""

    NORMAL = EnumField(0, _("正常"))
    AGENT_ABNORMAL = EnumField(1, _("Agent异常"))
    WAITING = EnumField(5, _("等待执行"))
    RUNNING = EnumField(7, _("正在执行"))
    SUCCESS = EnumField(9, _("执行成功"))
    FAILED = EnumField(11, _("执行失败"))
    DISPATCH_FAILED = EnumField(12, _("任务下发失败"))
    BEING_FORCIBLY_TERMINATED = EnumField(303, _("任务强制终止中"))
    FORCIBLY_TERMINATED_SUCCESS = EnumField(403, _("任务强制终止成功"))
    FORCIBLY_TERMINATED_FAILED = EnumField(404, _("任务强制终止失败"))


class BkJobHostErrorCode(BkJobIntEnum):
    """主机任务状态码"""

    NORMAL = EnumField(0, _("正常"))
    AGENT_ABNORMAL = EnumField(1, _("Agent异常"))
    LAST_SUCCESS = EnumField(3, _("上次已成功"))
    WAITING = EnumField(5, _("等待执行"))
    RUNNING = EnumField(7, _("正在执行"))
    SUCCESS = EnumField(9, _("执行成功"))
    TASK_FAILED = EnumField(11, _("任务失败"))
    DISPATCH_FAILED = EnumField(12, _("任务下发失败"))
    TIMEOUT = EnumField(13, _("任务超时"))
    LOG_ERROR = EnumField(15, _("任务日志错误"))
    SCRIPT_FAILED = EnumField(101, _("脚本执行失败"))
    SCRIPT_TIMEOUT = EnumField(102, _("脚本执行超时"))
    SCRIPT_TERMINATED = EnumField(103, _("脚本执行被终止"))
    SCRIPT_NON_ZERO_EXIT = EnumField(104, _("脚本返回码非零"))
    GSE_TASK_FORCIBLY_TERMINATED = EnumField(120, _("GSE任务强制终止成功"))
    FILE_TRANSFER_FAILED = EnumField(202, _("文件传输失败"))
    SOURCE_FILE_NOT_FOUND = EnumField(203, _("源文件不存在"))
    AGENT_ERROR = EnumField(310, _("Agent异常"))
    USER_NOT_FOUND = EnumField(311, _("用户名不存在"))
    FILE_FETCH_FAILED = EnumField(320, _("文件获取失败"))
    FILE_SIZE_EXCEEDED = EnumField(321, _("文件超出限制"))
    FILE_TRANSFER_ERROR = EnumField(329, _("文件传输错误"))
    TASK_EXEC_ERROR = EnumField(399, _("任务执行出错"))
