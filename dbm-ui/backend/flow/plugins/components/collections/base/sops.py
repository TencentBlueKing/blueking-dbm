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
import logging
from abc import ABCMeta

from bamboo_engine import states
from django.utils.translation import ugettext as _
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components.sops.client import BkSopsApi
from backend.flow.plugins.components.collections.base.base_service import BaseService

logger = logging.getLogger("flow")


class BkSopsService(BaseService, metaclass=ABCMeta):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)
    """
    定义调用标准运维的基类
    """

    def _schedule(self, data, parent_data, callback_data=None):
        kwargs = data.get_one_of_inputs("kwargs")
        bk_biz_id = kwargs["bk_biz_id"]
        task_id = data.get_one_of_outputs("task_id")
        param = {"bk_biz_id": bk_biz_id, "task_id": task_id, "with_ex_data": True}
        rp_data = BkSopsApi.get_task_status(param)
        state = rp_data.get("state", states.RUNNING)
        if state == states.FINISHED:
            self.finish_schedule()
            self.log_info("run success~")
            return True

        if state in [states.FAILED, states.REVOKED, states.SUSPENDED]:
            if state == states.FAILED:
                self.log_error(_("任务失败"))
            else:
                self.log_error(_("任务状态异常{}").format(state))
            # 查询异常日志
            self.log_error(rp_data.get("ex_data", _("查询日志失败")))
            return False
