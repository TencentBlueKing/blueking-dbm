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
import copy
import json
import logging
import re
from abc import ABCMeta
from typing import Dict, Optional

from django.utils.translation import ugettext as _
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend import env
from backend.components import JobApi
from backend.flow.consts import SUCCESS_LIST, WriteContextOpType
from backend.flow.plugins.components.collections.base.base_service import BaseService

logger = logging.getLogger("flow")
ACTUATOR_CONTEXT_RE = re.compile("<ctx>(?P<context>.+?)</ctx>")  # 非贪婪模式，只匹配第一次出现的自定义tag


class BkJobService(BaseService, metaclass=ABCMeta):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    @staticmethod
    def __status__(instance_id: str) -> Optional[Dict]:
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

    def __get_target_ip_context(
        self,
        job_instance_id: int,
        step_instance_id: int,
        ip_dict: dict,
        data,
        trans_data,
        write_payload_var: str,
        write_op: str,
    ):
        """
        对单个节点获取执行后log，并赋值给定义好流程上下文的trans_data
        write_op 控制写入变量的方式，rewrite是默认值，代表覆盖写入；append代表以{"ip":xxx} 形式追加里面变量里面
        """
        resp = self.get_job_log(job_instance_id, step_instance_id, ip_dict)
        if not resp["result"]:
            # 结果返回异常，则异常退出
            return False
        try:
            # 以dict形式追加写入
            result = json.loads(re.search(ACTUATOR_CONTEXT_RE, resp["data"]["log_content"]).group("context"))
            if write_op == WriteContextOpType.APPEND.value:
                context = copy.deepcopy(getattr(trans_data, write_payload_var))
                ip = ip_dict["ip"]
                if context:
                    context[ip] = copy.deepcopy(result)
                else:
                    context = {ip: copy.deepcopy(result)}

                setattr(trans_data, write_payload_var, copy.deepcopy(context))

            else:
                # 默认覆盖写入
                setattr(trans_data, write_payload_var, copy.deepcopy(result))
            data.outputs["trans_data"] = trans_data

            return True

        except Exception as e:
            self.log_error(_("[写入上下文结果失败] failed: {}").format(e))
            return False

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        ext_result = data.get_one_of_outputs("ext_result")
        exec_ips = data.get_one_of_outputs("exec_ips")
        kwargs = data.get_one_of_inputs("kwargs")
        write_payload_var = data.get_one_of_inputs("write_payload_var")
        trans_data = data.get_one_of_inputs("trans_data")

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
        resp = self.__status__(job_instance_id)

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
        if not write_payload_var:
            self.finish_schedule()
            return True

        # 写入上下文，支持多IP传入上下文捕捉场景
        # 写入上下文的位置是trans_data.{write_payload_var} 属性上，分别执行覆盖写入和追加写入
        # 覆盖写入是会直接赋值给上下文属性上，不管之前有什么值，这是默认写入 WriteContextOpType.REWRITE
        # 追加写入是特殊行为，如果想IP日志结果都写入，可以选择追加写入，上下文变成list，每个元素是{"ip":"log"} WriteContextOpType.APPEND
        self.log_info(_("[{}]该节点需要获取执行后日志，赋值到流程上下文").format(node_name))

        is_false = False
        for ip_dict in ip_dicts:
            if not self.__get_target_ip_context(
                job_instance_id=job_instance_id,
                step_instance_id=step_instance_id,
                ip_dict=ip_dict,
                data=data,
                trans_data=trans_data,
                write_payload_var=write_payload_var,
                write_op=kwargs.get("write_op", WriteContextOpType.REWRITE.value),
            ):
                self.log_error(_("[{}] 获取执行后写入流程上下文失败，ip:[{}]").format(node_name, ip_dict["ip"]))
                is_false = True

        if is_false:
            self.finish_schedule()
            return False

        self.finish_schedule()
        return True
