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
import time

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptService

logger = logging.getLogger("flow")


class ExecSwitchActForSourceService(ExecuteDBActuatorScriptService):
    """
    处理执行切换的活动节点，并判断切换结果返回不同的状态码，作为下一个条件的判断流向
    目前状态码分为以下情况：
    0: 代表切换正常
    1: 代表切换异常
    """

    def _schedule(self, data, parent_data, callback_data=None):
        code = super()._schedule(data, parent_data, callback_data)
        if code:
            # 代表执行切换正常
            data.outputs.switch_code = 0
            return True
        else:
            # 代表执行切换异常
            data.outputs.switch_code = 1
            return False


class ExecSwitchActForSourceComponent(Component):
    name = __name__
    code = "exec_switch_act_for_source"
    bound_service = ExecSwitchActForSourceService


class ExecRollbackActForSourceService(ExecuteDBActuatorScriptService):
    """
    处理执行切换的活动节点，并判断切换结果返回不同的状态码，作为下一个条件的判断流向
    目前状态码分为以下情况：
    0: 代表切换正常
    1: 代表切换异常
    """

    def _schedule(self, data, parent_data, callback_data=None):
        code = super()._schedule(data, parent_data, callback_data)
        if code:
            # 代表执行切换正常
            data.outputs.rollback_code = 0
            return True
        else:
            # 代表执行切换异常
            try:
                # 优先从全局数据获取 root_id（job_root_id）
                global_data = data.get_one_of_inputs("global_data") or {}
                logger.info(f"global_data: {global_data}")
                root_id = global_data.get("job_root_id")
                # 从本节点 kwargs 读取 node_id 与 version_id（框架注入）
                step_kwargs = data.get_one_of_inputs("kwargs") or {}
                node_id = step_kwargs.get("node_id")
                version_id = step_kwargs.get("version_id")

                error_lines = []
                if root_id and node_id and version_id:
                    handler = TaskFlowHandler(root_id)

                    # 添加重试机制，防止日志异步上报导致获取为空
                    # 考虑到日志系统的异步特性，使用指数退避策略
                    max_retries = 4
                    base_interval = 0.5  # 基础间隔（秒）

                    for attempt in range(max_retries):
                        error_lines = []
                        for rec in handler.get_version_error_logs(node_id, version_id):
                            error_lines.append(f"[{node_id}] {rec['timestamp']} {rec['levelname']} {rec['message']}")

                        if error_lines:
                            logger.info(_("成功获取错误日志，共 {} 条，尝试次数: {}").format(len(error_lines), attempt + 1))
                            break

                        if attempt < max_retries - 1:
                            # 使用指数退避：0.5s, 1s, 2s
                            retry_interval = base_interval * (2**attempt)
                            logger.warning(_("第 {} 次尝试获取错误日志为空，等待 {:.1f} 秒后重试...").format(attempt + 1, retry_interval))
                            time.sleep(retry_interval)
                        else:
                            logger.warning(
                                _("尝试 {} 次后仍未获取到错误日志，node_id: {}, version_id: {}").format(
                                    max_retries, node_id, version_id
                                )
                            )

                if error_lines:
                    # 将错误日志写入到 payload 供后续节点读取
                    data.outputs.payload = {"error_logs": "\n".join(error_lines)}
                    # 将错误日志写入到 trans_data，确保后续节点可以读取
                    trans_data = data.get_one_of_inputs("trans_data")
                    if trans_data:
                        trans_data.rollback_error_info = {"error_logs": "\n".join(error_lines)}
                        data.outputs["trans_data"] = trans_data
            except Exception as e:
                logger.warning("collect source_act error logs failed: %s", str(e))

            data.outputs.rollback_code = 1
            return False


class ExecRollbackActForSourceComponent(Component):
    name = __name__
    code = "exec_rollback_act_for_source"
    bound_service = ExecRollbackActForSourceService
