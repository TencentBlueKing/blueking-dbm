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

from bamboo_engine import states
from django.utils import translation
from django.utils.translation import gettext as _
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

from backend import env
from backend.bk_dataview.prometheus import metrics
from backend.bk_dataview.prometheus.handlers import node_label_func, setup_counter, setup_gauge, setup_histogram
from backend.components import JobApi
from backend.components.sops.client import BkSopsApi
from backend.core.translation.constants import Language
from backend.flow.consts import DEFAULT_FLOW_CACHE_EXPIRE_TIME, SUCCESS_LIST, JobOperationCode, WriteContextOpType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.ticket.models import Flow
from backend.utils.excel import ExcelHandler
from backend.utils.redis import RedisConn

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

    @classmethod
    def active_language(cls, data):
        # 激活国际化
        blueking_language = data.get_one_of_inputs("global_data").get("blueking_language", Language.ZH_CN.value)
        translation.activate(blueking_language)

    @classmethod
    def get_flow_output(cls, flow: Union[Flow, str], is_read_cache: bool = False):
        """
        获取流程的缓存数据。只允许在流程成功结束后执行
        @param flow: 当前流程
        @param is_read_cache: 是否直接读cache
        """
        if isinstance(flow, str):
            flow = Flow.objects.get(flow_obj_id=flow)

        # 优先从output取
        if flow.output_data:
            return flow.output_data
        return flow.details.get("__flow_output", [])

    def set_flow_output(self, root_id: str, key: Union[int, str], value: Any, is_sensitive: bool = False):
        """
        TODO: 该方法即将废弃，请使用FlowOutputHandler的insert_data
        在整个流程中存入缓存数据，只允许追加不支持修改，对相同的key会合并为list
        在流程执行成功后，缓存数据会入库到
        @param root_id: 流程id
        @param key: 缓存键值
        @param value: 可json序列化的数据
        @param is_sensitive: 本次缓存是否是敏感数据
        """
        # 序列化
        try:
            flow_cache_key, flow_sensitive_key = f"{root_id}_list", f"{root_id}_is_sensitive"
            data = json.dumps({key: value})
        except TypeError:
            self.log_exception(_("该数据{}:{}无法被序列化，跳过此次缓存").format(key, value))
            return

        # 用list原语缓存数据，不会出现竞态
        RedisConn.lpush(flow_cache_key, data)
        # 只会设置为True，不会出现竞态
        if is_sensitive:
            RedisConn.set(flow_sensitive_key, 1)
        # 每次缓存都刷新过期时间。我们设置一个足够长的过期时间，如果这个任务失败很久不处理，那么数据就会自动清理
        RedisConn.expire(flow_cache_key, DEFAULT_FLOW_CACHE_EXPIRE_TIME)
        RedisConn.expire(flow_sensitive_key, DEFAULT_FLOW_CACHE_EXPIRE_TIME)

    def excel_download(self, root_id: str, match_header: bool = False):
        """
        根据root_id下载Excel文件
        :param root_id: 流程id
        :param key: 缓存键值
        """
        # 获取root_id缓存数据
        flow_details = self.get_flow_output(flow=root_id)

        # 检查 flow_details 是否存在以及是否包含所需的 key
        if not flow_details:
            self.log_error(_("下载excel文件失败，未获取到流程id:{}相关的数据").format(root_id))
            return False

        # flow_details为列表且非空，提取第一个元素
        if isinstance(flow_details, list) and flow_details:
            flow_details = flow_details[0]

        flow_detail = flow_details.get("values", [])

        if not flow_detail:
            self.log_error(_("下载excel文件失败，未获取到流程id:{}相关的数据").format(root_id))
            return False

        # 如果 flow_detail 是一个双重列表，则去掉一个列表
        if isinstance(flow_detail[0], list):
            flow_detail = flow_detail[0]

        if not isinstance(flow_detail[0], dict):
            self.log_error(_("下载excel文件失败，获取数据格式错误"))
            return False

        # 取第一个字典的键作为head
        head_list = list(flow_detail[0].keys())

        excel_name = f"{root_id}.xlsx"
        # 将数据字典序列化为excel对象
        wb = ExcelHandler.serialize(flow_detail, headers=head_list, match_header=match_header)
        # 返回响应
        return ExcelHandler.response(wb, excel_name)

    @setup_gauge([metrics.pipeline_node_execute_running_count], labels=node_label_func)
    @setup_histogram([metrics.pipeline_node_execute_duration_histogram], labels=node_label_func)
    @setup_counter([metrics.pipeline_node_execute_failed_total], labels=node_label_func, check=lambda res: not res)
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

    @setup_gauge([metrics.pipeline_node_execute_running_count], labels=node_label_func)
    @setup_histogram([metrics.pipeline_node_schedule_duration_histogram], labels=node_label_func)
    @setup_counter([metrics.pipeline_node_execute_failed_total], labels=node_label_func, check=lambda res: not res)
    def schedule(self, data, parent_data, callback_data=None):
        self.active_language(data)

        kwargs = data.get_one_of_inputs("kwargs") or {}
        try:
            result = self._schedule(data, parent_data, callback_data)
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
    # 仅针对失败IP重试
    only_failed_retry = False

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

    @staticmethod
    def __url__(job_instance_id: int, link: bool = False):
        """
        获取job任务链接
        """
        url = f"{env.BK_JOB_URL}/api_execute/{job_instance_id}/"
        if link:
            url = _("<a href='{}' target='_blank'>{}</a>").format(url, url)
        return url

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

    def _execute_fail_job(self, data, job_instance_id, step_instance_id):
        """
        针对一个任务进行失败IP重试
        """
        params = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
            "operation_code": JobOperationCode.FAILED_IP_RETRY.value,
        }
        resp = JobApi.operate_step_instance(params, raw=True)
        self.log_info(f"retry job url: {self.__url__(job_instance_id)}")

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        return True

    def execute(self, data, parent_data):
        self.active_language(data)

        root_id, node_id = self.runtime_attrs.get("root_pipeline_id"), self.runtime_attrs.get("id")
        outputs = BambooEngine(root_id).get_node_output_data(node_id).data
        # 针对允许失败IP重试且上次执行失败的job节点，进行失败ip重试。
        if self.only_failed_retry and outputs.get("job_execute") is False:
            execute_info = outputs["job_execute_info"]
            return self._execute_fail_job(data, execute_info["job_instance_id"], execute_info["step_instance_id"])
        else:
            return super().execute(data, parent_data)

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
            # 打印job链接
            if (
                isinstance(ext_result, dict)
                and ext_result["data"]
                and isinstance(ext_result["data"], dict)
                and "job_instance_id" in ext_result["data"]
            ):
                self.log_info(f"job url: {self.__url__(ext_result['data']['job_instance_id'])}")

        if isinstance(ext_result, bool):
            # ext_result 为 布尔类型 表示 不需要任务是同步进行，不需要调用api去监听任务状态
            self.finish_schedule()
            return ext_result

        if not ext_result["result"]:
            # 调用结果检测到失败
            self.log_error(f"[{node_name}] schedule  status failed: {ext_result.get('error')}")
            return False

        if not ext_result["data"]:
            # 没有data返回，可能是job内部服务异常
            self.log_error(f"[{node_name}] job execute failed, request id is {ext_result.get('job_request_id')}")
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
        # ip_dict = {"bk_cloud_id": kwargs["bk_cloud_id"], "ip": exec_ips[0]} if exec_ips else {}
        # ip_dicts = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips] if exec_ips else []
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
                    resp = self.__log__(job_instance_id, step_instance_id, ip_dict)
                    if resp.get("result"):
                        self.log_error(f"{ip_dict}:{resp['data']['log_content']}")

            # job失败后，记录失败的信息，可用于失败IP重试。
            data.outputs.job_execute = False
            data.outputs.job_execute_info = {"job_instance_id": job_instance_id, "step_instance_id": step_instance_id}

            self.finish_schedule()
            return False

        self.log_info(_("[{}]任务调度成功🥳︎").format(node_name))
        data.outputs.job_execute = True

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


class BkShortJobService(BkJobService):
    """
    蓝鲸短作业服务
    """

    interval = StaticIntervalGenerator(1)


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
