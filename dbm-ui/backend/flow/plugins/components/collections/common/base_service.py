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
from typing import Any, Dict, List, Optional, Union

from django.utils import translation
from django.utils.translation import ugettext as _
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

from backend import env
from backend.components import JobApi
from backend.core.translation.constants import Language
from backend.flow.consts import SUCCESS_LIST, WriteContextOpType

logger = logging.getLogger("flow")
cpl = re.compile("<ctx>(?P<context>.+?)</ctx>")  # 非贪婪模式，只匹配第一次出现的自定义tag


class ServiceLogMixin:
    def log_info(self, msg: str):
        logger.info(msg, extra=self.extra_log)

    def log_error(self, msg: str):
        logger.error(msg, extra=self.extra_log)

    def log_warning(self, msg: str):
        logger.warning(msg, extra=self.extra_log)

    def log_debug(self, msg: str):
        logger.debug(msg, extra=self.extra_log)

    def log_exception(self, msg: str):
        logger.exception(msg, extra=self.extra_log)

    def log_dividing_line(self):
        logger.info("*" * 50, extra=self.extra_log)

    @property
    def runtime_attrs(self):
        """pipeline.activity内部运行时属性"""
        return getattr(self, "_runtime_attrs", {})

    @property
    def extra_log(self):
        """Service运行时属性，用于获取 root_id, node_id, version_id 注入日志"""
        return {
            "root_id": self.runtime_attrs.get("root_pipeline_id"),
            "node_id": self.runtime_attrs.get("id"),
            "version_id": self.runtime_attrs.get("version"),
        }


class BaseService(Service, ServiceLogMixin, metaclass=ABCMeta):
    """
    DB Service 基类
    """

    def active_language(self, data):
        # 激活国际化
        blueking_language = data.get_one_of_inputs("global_data").get("blueking_language", Language.ZH_CN.value)
        translation.activate(blueking_language)
        # self.log_info(f"System language: {blueking_language}")

    def execute(self, data, parent_data):
        self.active_language(data)

        kwargs = data.get_one_of_inputs("kwargs") or {}
        try:
            result = self._execute(data, parent_data)
            if result:
                self.log_info(_("[{}] 运行成功").format(kwargs.get("node_name", self.__class__.__name__)))

            return result
        except Exception as e:  # pylint: disable=broad-except
            self.log_exception(_("[{}] 失败: {}").format(kwargs.get("node_name", self.__class__.__name__), e))
            return False

    def _execute(self, data, parent_data):
        raise NotImplementedError()

    def schedule(self, data, parent_data, callback_data=None):
        self.active_language(data)

        kwargs = data.get_one_of_inputs("kwargs") or {}
        try:
            result = self._schedule(data, parent_data)
            return result
        except Exception as e:  # pylint: disable=broad-except
            self.log_exception(f"[{kwargs.get('node_name', self.__class__.__name__)}] failed: {e}")
            self.finish_schedule()
            return False

    def _schedule(self, data, parent_data, callback_data=None):
        self.finish_schedule()
        return True

    @staticmethod
    def splice_exec_ips_list(
        ticket_ips: Optional[Any] = None, pool_ips: Optional[Any] = None, parse_cloud: bool = False
    ) -> Union[List[Dict], List[str]]:
        """
        拼接执行ip列表
        @param ticket_ips: 表示单据预分配好的ip信息
        @param pool_ips:   表示从资源池分配到的ip信息
        @param parse_cloud: 是否需要解析云区域 TODO: 当flow兼容后，默认为云区域
        """

        def _format_to_str(ip: Union[str, dict]) -> Union[str, Dict]:
            """
            {"ip": "127.0.0.1", "bk_cloud_id": 0} -> "127.0.0.1"
            """
            if isinstance(ip, dict):
                if not parse_cloud:
                    return ip["ip"]
                return {"ip": ip["ip"], "bk_cloud_id": ip["bk_cloud_id"]}
            return ip

        def _format_to_list(ip: Optional[Union[list, str]]) -> list:
            # TODO 最终应该使用 _format_to_dict 统一返回 [{"ip": "127.0.0.1", "bk_cloud_id": 0 }]
            #  需 flow 整体配合改造
            if ip is None:
                return []
            if isinstance(ip, list):
                return [_format_to_str(_ip) for _ip in ip]
            return [_format_to_str(ip)]

        return _format_to_list(ticket_ips) + _format_to_list(pool_ips)


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

    def __log__(
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
        resp = self.__log__(job_instance_id, step_instance_id, ip_dict)
        if not resp["result"]:
            # 结果返回异常，则异常退出
            return False
        try:
            # 以dict形式追加写入
            result = json.loads(re.search(cpl, resp["data"]["log_content"]).group("context"))
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
        global_data = data.get_one_of_inputs("global_data")
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

        job_status = resp["data"]["job_instance"]["status"]
        step_instance_id = resp["data"]["step_instance_list"][0]["step_instance_id"]
        ip_dict = {"bk_cloud_id": kwargs["bk_cloud_id"], "ip": exec_ips[0]} if exec_ips else {}

        if job_status not in SUCCESS_LIST:
            self.log_info("{} job status: {}".format(node_name, resp))
            self.log_info(_("[{}]  任务调度失败😱").format(node_name))

            # 转载job脚本节点报错日志
            if ip_dict:
                resp = self.__log__(job_instance_id, step_instance_id, ip_dict)
                if resp.get("result"):
                    self.log_error(resp["data"]["log_content"])

            self.finish_schedule()
            return False

        self.log_info(_("[{}]任务调度成功🥳︎").format(node_name))
        if not write_payload_var:
            self.finish_schedule()
            return True

        # 写入上下文，目前如果传入的ip_list只支持一组ip，多组ip会存在问题,因为这里只拿第一个执行ip来拼接结果到对应的上下文变量
        self.log_info(_("[{}]该节点需要获取执行后日志，赋值到trans_data").format(node_name))
        self.log_info(exec_ips)
        if not self.__get_target_ip_context(
            job_instance_id=job_instance_id,
            step_instance_id=step_instance_id,
            ip_dict=ip_dict,
            data=data,
            trans_data=trans_data,
            write_payload_var=write_payload_var,
            write_op=kwargs.get("write_op", WriteContextOpType.REWRITE.value),
        ):
            self.log_info(_("[{}] 获取执行后日志失败，获取ip[{}]").format(node_name, exec_ips[0]))
            self.finish_schedule()
            return False

        self.finish_schedule()
        return True
