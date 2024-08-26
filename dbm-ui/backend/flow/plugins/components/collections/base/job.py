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
from typing import Dict, Optional

from django.utils.translation import ugettext as _
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend import env
from backend.components import JobApi
from backend.flow.consts import SUCCESS_LIST
from backend.flow.plugins.components.collections.base.base_service import BaseService

logger = logging.getLogger("flow")


class BaseJobService(BaseService, metaclass=ABCMeta):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    @staticmethod
    def get_job_status(instance_id: str) -> Optional[Dict]:
        """
        获取任务状态
        """
        payload = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": instance_id,
            "return_ip_result": True,
        }
        resp = JobApi.get_job_instance_status(payload, raw=True)
        return resp

    def get_job_log(
        self,
        job_instance_id: int,
        step_instance_id: int,
        ip_dict: dict,
    ):
        """
        获取任务日志
        """
        payload = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
        }
        return JobApi.get_job_instance_ip_log({**payload, **ip_dict}, raw=True)

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        ext_result = data.get_one_of_outputs("ext_result")
        exec_ips = data.get_one_of_outputs("exec_ips")
        kwargs = data.get_one_of_inputs("kwargs")
        node_name = kwargs["node_name"]

        # 在轮询的时候ext_result都不会改变，考虑收敛日志
        if not kwargs.get(f"{node_name}_ext_result_cached"):
            kwargs[f"{node_name}_ext_result_cached"] = True
            self.log_info(f"[{node_name}] ext_result: {ext_result}")

        if isinstance(ext_result, bool):
            # ext_result 为 布尔类型 表示 不需要任务是同步进行，不需要调用api去监听任务状态
            self.finish_schedule()
            return ext_result

        if not ext_result["result"]:
            # 调用结果检测到失败
            self.log_error(f"[{node_name}] schedule  status failed: {ext_result['error']}")
            return False

        job_instance_id = ext_result["data"]["job_instance_id"]
        resp = self.get_job_status(job_instance_id)

        # 获取任务状态：
        # """
        # 1.未执行; 2.正在执行; 3.执行成功; 4.执行失败; 5.跳过; 6.忽略错误;
        # 7.等待用户; 8.手动结束; 9.状态异常; 10.步骤强制终止中; 11.步骤强制终止成功; 12.步骤强制终止失败
        # """
        if not (resp["result"] and resp["data"]["finished"]):
            self.log_info(_("[{}] 任务正在执行🤔").format(node_name))
            return True

        # 获取job的状态
        job_status = resp["data"]["job_instance"]["status"]

        # 默认dbm调用job是一个步骤，所以统一获取第一个步骤id
        step_instance_id = resp["data"]["step_instance_list"][0]["step_instance_id"]

        # 获取本次执行的所有ip信息
        ip_dicts = []
        if exec_ips:
            for i in exec_ips:
                if isinstance(i, dict) and i.get("ip") is not None and i.get("bk_cloud_id") is not None:
                    ip_dicts.append(i)
                else:
                    # 兼容之前代码
                    ip_dicts.append({"bk_cloud_id": kwargs["bk_cloud_id"], "ip": i})

        # 判断本次job任务是否异常
        if job_status not in SUCCESS_LIST:
            self.log_info("{} job status: {}".format(node_name, resp))
            self.log_info(_("[{}]  任务调度失败😱").format(node_name))

            # 转载job脚本节点报错日志，兼容多IP执行场景的日志输出
            if ip_dicts:
                for ip_dict in ip_dicts:
                    resp = self.get_job_log(job_instance_id, step_instance_id, ip_dict)
                    if resp.get("result"):
                        self.log_error(f"{ip_dict}:{resp['data']['log_content']}")

            self.finish_schedule()
            return False

        self.log_info(_("[{}]任务调度成功🥳︎").format(node_name))
        self.finish_schedule()
        return True
