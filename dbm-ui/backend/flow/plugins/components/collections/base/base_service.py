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
import json
import logging
import re
import sys
from abc import ABCMeta
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from django.utils import translation
from django.utils.translation import ugettext as _
from pipeline.core.flow.activity import Service

from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.core.translation.constants import Language
from backend.flow.consts import DEFAULT_FLOW_CACHE_EXPIRE_TIME
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
            # 由于封装了日志模块，会导致打印的日志文件都在本文件中，因此需找到调用日志的源
            "real_pathname": sys._getframe(2).f_code.co_filename,
            "real_funcName": sys._getframe(2).f_code.co_name,
            "real_lineno": sys._getframe(2).f_lineno,
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
        if flow.details.get("__flow_output") and not is_read_cache:
            return flow.details.get("__flow_output")

        # 获取缓存数据
        flow_cache_key, flow_sensitive_key = f"{flow.flow_obj_id}_list", f"{flow.flow_obj_id}_is_sensitive"
        flow_cache_data = [json.loads(item) for item in RedisConn.lrange(flow_cache_key, 0, -1)]
        # 合并相同的key
        merge_data = defaultdict(list)
        for data in flow_cache_data:
            for k, v in data.items():
                merge_data[k].append(v)

        # 如果是敏感数据，则整体加密
        is_sensitive = int(RedisConn.get(flow_sensitive_key) or False)
        if is_sensitive:
            merge_data = json.dumps(merge_data)
            merge_data = AsymmetricHandler.encrypt(name=AsymmetricCipherConfigType.PASSWORD.value, content=merge_data)

        # 入库到flow的details中，并删除缓存key
        flow.update_details(
            __flow_output={"root_id": flow.flow_obj_id, "is_sensitive": is_sensitive, "data": merge_data}
        )
        RedisConn.delete(flow_cache_key, flow_sensitive_key)

        return flow.details["__flow_output"]

    def set_flow_output(self, root_id: str, key: Union[int, str], value: Any, is_sensitive: bool = False):
        """
        在整个流程中存入缓存数据，只允许追加不支持修改，对相同的key会合并为list
        在流程执行成功后，缓存数据会入库到
        @param root_id: 流程id
        @param key: 缓存键值
        @param value: 可json序列化的数据
        @param is_sensitive: 本次缓存是否是敏感数据
        """
        # 序列化
        try:
            data = json.dumps({key: value})
        except TypeError:
            self.log_exception(_("该数据{}:{}无法被序列化，跳过此次缓存").format(key, value))
            return
        flow_cache_key, flow_sensitive_key = f"{root_id}_list", f"{root_id}_is_sensitive"

        # 用list原语缓存数据，不会出现竞态
        RedisConn.lpush(flow_cache_key, data)
        # 只会设置为True，不会出现竞态
        if is_sensitive:
            RedisConn.set(flow_sensitive_key, 1)
        # 每次缓存都刷新过期时间。我们设置一个足够长的过期时间，如果这个任务失败很久不处理，那么数据就会自动清理
        RedisConn.expire(flow_cache_key, DEFAULT_FLOW_CACHE_EXPIRE_TIME)
        RedisConn.expire(flow_sensitive_key, DEFAULT_FLOW_CACHE_EXPIRE_TIME)

    def excel_download(self, root_id: str, key: Union[int, str], match_header: bool = False):
        """
        根据root_id下载Excel文件
        :param root_id: 流程id
        :param key: 缓存键值
        """
        # 获取root_id缓存数据
        flow_details = self.get_flow_output(flow=root_id, is_read_cache=True)

        # 检查 flow_details 是否存在以及是否包含所需的 key
        if not flow_details or key not in flow_details["data"]:
            self.log_error(_("下载excel文件失败，未获取到{}相关的数据").format(key))
            return False

        flow_detail = flow_details["data"][key]

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
