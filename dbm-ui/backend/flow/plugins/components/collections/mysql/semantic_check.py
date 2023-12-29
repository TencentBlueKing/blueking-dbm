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

from django.core.cache import cache
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components.sql_import.client import SQLSimulationApi
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_services.mysql.sql_import.constants import (
    CACHE_SEMANTIC_AUTO_COMMIT_FIELD,
    CACHE_SEMANTIC_SKIP_PAUSE_FILED,
)
from backend.exceptions import ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class SemanticCheckService(BaseService):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)
    """
    在执行语义分析的SQL场景的专属活动节点
    1：执行SQL(利用db-actuator组件)
    2：释放语义实例
    """

    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 由 kwargs["cluster"] 传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        payload = kwargs["payload"]
        cluster_type = kwargs["cluster_type"]
        payload["root_id"] = kwargs["root_id"]
        payload["node_id"] = kwargs["node_id"]
        payload["task_id"] = f"{payload['task_id']}_{self.extra_log['version_id']}"
        payload["version_id"] = self._runtime_attrs.get("version")
        try:
            if cluster_type == ClusterType.TenDBCluster:
                resp = SQLSimulationApi.spider_simulation(payload, raw=True)
            else:
                resp = SQLSimulationApi.mysql_simulation(payload, raw=True)
            self.log_info(_("创建模拟执行任务resp{}").format(resp))
            code = resp["code"]
            if code != 0:
                errmsg = resp["msg"]
                self.log_error(_("创建模拟任务失败:{}").format(errmsg))
                return False
            self.log_info(_("创建模拟任务成功"))
            return True
        except Exception as e:
            if isinstance(e, ApiResultError):
                error_message = _("「执行语义分析任务异常」{}").format(e.message)
            else:
                error_message = _("「执行语义分析任务异常」{}").format(e)
            self.log_info(_("创建模拟任务失败!"))
            self.log_error("[{}] failed: {}".format(kwargs["node_name"], error_message))
            return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        payload = kwargs["payload"]
        cluster_type = kwargs["cluster_type"]
        try:
            # code:0 成功 code:1 失败 code:2 running
            # -
            resp = SQLSimulationApi.query_simulation_task({"task_id": payload["task_id"]}, raw=True)
            code = resp["code"]
            msg = resp["msg"]

            if code == 0:
                self.log_info("run task success~ ")
                self._prepare_for_ticket(data=data, cluster_type=cluster_type)
                self.finish_schedule()
                return True
            if code == 1:
                rpdata = resp["data"]
                stderr = rpdata["stderr"]
                self.log_error("run task failed,err msg {}".format(msg))
                self.log_error("execute stderr: {}".format(stderr))
                self.finish_schedule()
                return False
            self.log_info("running... msg:{}".format(msg))
            return True
        except Exception as e:
            self.log_exception("[{}] failed: {}".format(kwargs.get("node_name", self.__class__.__name__), e))
            self.finish_schedule()
            return False

    def _prepare_for_ticket(self, data, cluster_type):
        """为创建单据做参数准备"""
        root_id = data.get_one_of_inputs("kwargs").get("root_id")
        bk_biz_id = data.get_one_of_inputs("global_data").get("bk_biz_id")
        auto_commit_key = CACHE_SEMANTIC_AUTO_COMMIT_FIELD.format(bk_biz_id=bk_biz_id, root_id=root_id)
        skip_pause_key = CACHE_SEMANTIC_SKIP_PAUSE_FILED.format(bk_biz_id=bk_biz_id, root_id=root_id)

        # 默认自动创建单据
        is_auto_commit = cache.get(auto_commit_key, True)
        is_skip_pause = cache.get(skip_pause_key, False)
        self.log_info(
            f"-----------auto_commit_key: {auto_commit_key}-{is_auto_commit}, "
            f"skip_pause_key: {skip_pause_key}-{is_skip_pause}-------------"
        )
        ticket_type = TicketType.MYSQL_IMPORT_SQLFILE
        if cluster_type == ClusterType.TenDBCluster:
            ticket_type = TicketType.TENDBCLUSTER_IMPORT_SQLFILE

        # 构造单据信息
        trans_data = {
            "is_auto_commit": is_auto_commit,
            "ticket_data": {
                "remark": _("语义检查出发的自动创建单据"),
                "ticket_type": ticket_type,
                "details": {"root_id": root_id, "skip_pause": is_skip_pause},
            },
        }
        data.outputs["trans_data"] = trans_data


class SemanticCheckComponent(Component):
    name = __name__
    code = "sql_semantic_check"
    bound_service = SemanticCheckService
