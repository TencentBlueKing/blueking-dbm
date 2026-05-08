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
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict

from bamboo_engine import api
from django.utils.translation import gettext as _
from pipeline.core.flow import StaticIntervalGenerator
from pipeline.eri.runtime import BambooDjangoRuntime

from backend.flow.consts import StateType
from backend.flow.plugins.components.collections.common.base_service import BaseService

# 主线程轮询"主流程是否结束/业务线程是否结束"的粒度（秒）
SIDECAR_WORKER_CHECK_INTERVAL = 2


class SidecarServiceABC(BaseService, ABC):
    """
    示例
    class SidecarDemoService(SidecarServiceABC):
        interval = StaticIntervalGenerator(30)

        def sidecar_func(self, *args, **kwargs) -> bool:
            custom_param = kwargs["custom_param"]
            self.log_info("output {}".format(custom_param))
            return True

    class SidecarDemoComponent(Component):
        name = __name__
        code = "sidecar-demo"
        bound_service = SidecarDemoService

    1. 这样就定义了一个每 30s 打印一行日志的 component
    2. 如何使用这个 component 注入子流程可以参考 dbm-ui/backend/flow/engine/bamboo/scene/common/build_sidecar_wrapper.py

    关于"主流程结束后立刻中断"的语义：
        - _schedule 被触发时，会把 sidecar_func 丢到一个 daemon 线程执行；
        - _schedule 主线程每 2s 检查一次主流程状态与业务线程状态；
        - 一旦主流程不再 RUNNING，立刻 finish_schedule 并 return True，
          节点状态被引擎置为 FINISHED（已完成）；
        - 若子类愿意"合作式打断"，可在 sidecar_func 中通过 self.stop_event 感知
          （例如用 self.stop_event.wait(timeout=n) 替代 time.sleep(n)）。

    关于 _schedule 内部为何使用 while True + 短超时 join 的设计取舍：
        - 调度执行模型：本项目中 bamboo-engine 的 _schedule 跑在 celery worker
          的 er_schedule 队列上，每次触发占用的是一个 celery worker 并发槽位，
          并非进程内有限的"调度线程池"，可以通过 -c 参数横向扩展。
        - interval 串行保证：bamboo-engine 的 interval 触发机制是"上一轮
          _schedule 执行完成后，再等 interval 时间间隔才会触发下一轮"，
          同一节点的多次 _schedule 之间是 *严格串行* 的，不会出现"上一轮还在
          跑、下一轮又被拉起"的并发重叠。因此即使本轮 _schedule 长时间阻塞
          在 while True 里，也不会导致 sidecar_func 业务线程堆叠或重复执行。
        - 设计目标：sidecar 节点要在"主流程一旦结束"时秒级感知并停下，单纯
          依赖 interval（默认 30s）粒度太粗，故在 _schedule 内部用 2s 粒度的
          短超时 join 做内嵌轮询，在主流程结束的当下立即 finish_schedule 收尾。
        - 业务线程是 daemon：sidecar_func 跑在 daemon 线程里，即使主流程已结束
          导致 _schedule 提前返回、或 worker 进程退出，daemon 线程也会被
          回收，无需持久化业务线程状态。
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(30)

    def _execute(self, data, parent_data):
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        global_data = data.get_one_of_inputs("global_data")
        root_id = global_data["job_root_id"]

        # 入口先判断一次：主流程已结束 → 立即收尾
        if not self._worker_is_running(root_id=root_id):
            self.finish_schedule()
            return True

        # 为本轮业务线程准备一个"停止信号"，子类可合作式感知
        stop_event = threading.Event()
        result_holder: Dict[str, Any] = {"ret": True, "exc": None}

        def _run():
            try:
                result_holder["ret"] = self.sidecar_func(data, parent_data)
            except Exception as err:
                result_holder["exc"] = err
                result_holder["ret"] = True  # 出错时不要让节点变 FAILED，交给 sidecar_func 内部日志体现

        worker = threading.Thread(target=_run, name="sidecar-worker-{}".format(root_id), daemon=True)
        worker.start()

        # 主线程做两件事：等业务线程完成 / 监听主流程是否已结束
        while True:
            worker.join(timeout=SIDECAR_WORKER_CHECK_INTERVAL)

            # 1) 业务线程已经跑完：按返回值决定本节点是否继续轮询
            if not worker.is_alive():
                if result_holder["exc"] is not None:
                    self.log_error(_("AI单据值守执行异常: {}".format(result_holder["exc"])))
                if result_holder["ret"]:
                    return True
                self.finish_schedule()
                return False

            # 2) 业务线程还在跑：检查主流程是否结束；若已结束，立即收尾（抛弃正在跑的 daemon 线程）
            if not self._worker_is_running(root_id=root_id):
                self.log_info(_("主任务流程已经结束，直接结束单据值守节点状态"))
                stop_event.set()  # 通知子类（若有合作式感知）尽快退出
                self.finish_schedule()
                return True

    def _worker_is_running(self, root_id: str) -> bool:
        ret = api.get_pipeline_states(BambooDjangoRuntime(), root_id, False)
        for child in ret.data[root_id]["children"].values():
            child_id = child["id"]
            if self.runtime_attrs["top_pipeline_id"] == child_id:
                continue

            if child["state"] == StateType.RUNNING:
                return True

        return False

    @abstractmethod
    def sidecar_func(self, data, parent_data) -> bool:
        pass
