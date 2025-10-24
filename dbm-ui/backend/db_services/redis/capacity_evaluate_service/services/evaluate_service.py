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
import time
import traceback
from enum import Enum

from django.utils.translation import gettext as _

from backend.db_services.redis.capacity_evaluate_service.models.tb_capacity_evaluate import CapacityEvaluateRecord
from backend.db_services.redis.capacity_evaluate_service.repositories.cluster_topo_repo import (
    ClusterCapacityInfo,
    ClusterTopoInfo,
)
from backend.db_services.redis.capacity_evaluate_service.repositories.evaluate_record_repo import EvaluateRecordRepo
from backend.db_services.redis.capacity_evaluate_service.util import logger_debug

from .capacity_cal import CapacityCalculateService

logger = logging.getLogger("root")


class Response:
    """单个评估结果"""

    status: str
    message: str
    cluster_domain: str
    approved_user: str
    proxy_approve_ok: bool
    proxy_approve_info: str
    backend_approve_ok: bool
    backend_approve_info: str
    capacity_approve_ok: bool
    capacity_approve_info: str
    related_records_info: str
    related_records: dict
    debug_info: dict
    time_elapsed_ms: int

    def __init__(self):
        """init response"""
        self.debug_info = {}
        self.time_elapsed_ms = 0
        self.status = ""
        self.message = ""
        self.approved_user = ""
        self.cluster_domain = ""
        self.proxy_approve_ok = False
        self.proxy_approve_info = ""
        self.backend_approve_ok = False
        self.backend_approve_info = ""
        self.capacity_approve_ok = False
        self.capacity_approve_info = ""
        self.related_records_info = ""
        self.related_records = {}

    def __dict__(self):
        """转换为字典"""
        return {
            "status": self.status,
            "message": self.message,
            "approved_user": self.approved_user,
            "time_elapsed_ms": self.time_elapsed_ms,
            "cluster_domain": self.cluster_domain,
            "proxy_approve_ok": self.proxy_approve_ok,
            "proxy_approve_info": self.proxy_approve_info,
            "backend_approve_ok": self.backend_approve_ok,
            "backend_approve_info": self.backend_approve_info,
            "capacity_approve_ok": self.capacity_approve_ok,
            "capacity_approve_info": self.capacity_approve_info,
            "related_records_info": self.related_records_info,
            "related_records": self.related_records,
        }

    def is_all_approved_ok(self):
        """是否全部通过"""
        return self.proxy_approve_ok and self.backend_approve_ok and self.capacity_approve_ok

    def to_dict(self):
        """转换为字典"""
        return self.__dict__()


class ResultStatus(Enum):
    """结果状态"""

    ERROR = "error"
    FAILED = "failed"
    SUCCESS = "success"


class ResultCode(Enum):
    """结果代码"""

    SUCCESS = 1
    FAILED = 2
    ERROR = 3


class CapacityEvaluateService:
    """容量评估服务"""

    def __init__(self):
        """初始化容量评估服务"""
        self.model = {
            "proxy_qps": 20000,
            "shard_qps_per_core": 60000,
            "ssd_shard_qps_per_core": 6000,
        }

    @classmethod
    def evaluate_one(cls, action_info: dict, req: dict, bk_biz_id: int, cluster_id: int) -> Response:
        """评估单个集群"""
        start_time = time.time()
        capacity_info = {}
        try:
            capacity_info = cls._calculate_capacity(bk_biz_id, cluster_id)
            model = {
                "proxy_qps": 20000,
                "shard_qps_per_core": 60000,
                "ssd_shard_qps_per_core": 6000,
            }

            resp = cls.evaluate_one_by_model(capacity_info, action_info, req, model, start_time)
            resp.time_elapsed_ms = cls._calculate_elapsed_time(start_time)
            return resp

        except Exception as e:
            resp = cls._create_error_response(capacity_info, e)
            resp.time_elapsed_ms = cls._calculate_elapsed_time(start_time)
            return resp

    @classmethod
    def _calculate_capacity(cls, bk_biz_id: int, cluster_id: int):
        """计算容量信息"""
        return CapacityCalculateService.calculate(bk_biz_id, cluster_id)

    @classmethod
    def _calculate_elapsed_time(cls, start_time: float) -> int:
        """计算耗时（毫秒）"""
        return int((time.time() - start_time) * 1000)

    @classmethod
    def _create_error_response(cls, capacity_info, error: Exception) -> Response:
        """打印错误堆栈到日志，返回简要的错误信息"""
        resp = Response()
        resp.debug_info = None
        resp.status = ResultStatus.ERROR.value
        resp.message = "CapacityEvaluateService_create_error_response"
        logger.error(f"CapacityEvaluateService._create_error_response error: {error} {traceback.format_exc()} end")
        return resp

    @classmethod
    def evaluate_one_by_model(
        cls, capacity_info: ClusterCapacityInfo, action_info: dict, req: dict, model: dict, start_time: float
    ):
        """评估单个实例"""
        record = cls._save_evaluate_record(action_info, req, capacity_info)
        total_req_capacity_m, total_req_qps_k, not_finished_records = EvaluateRecordRepo().get_not_finished_record(
            capacity_info.topo_info.cluster_id, action_info.get("start_time")
        )

        if not not_finished_records:
            raise Exception("no not finished record, bad request")

        resp = cls._evaluate_capacity(
            capacity_info, model, action_info, total_req_capacity_m, total_req_qps_k, not_finished_records
        )
        resp.time_elapsed_ms = cls._calculate_elapsed_time(start_time)
        cls._save_evaluate_history(
            action_info,
            req,
            capacity_info,
            resp.to_dict(),
            total_req_capacity_m,
            total_req_qps_k,
            not_finished_records,
        )
        cls._save_evaluate_record_end(record, resp.to_dict())
        return resp

    @classmethod
    def _save_evaluate_history(
        cls,
        action_info: dict,
        req: dict,
        capacity_info: ClusterCapacityInfo,
        resp: dict,
        total_req_capacity_m: float,
        total_req_qps_k: float,
        not_finished_records: list,
    ):
        """保存评估历史"""
        history = EvaluateRecordRepo().new_history_from_request(
            action_info, req, capacity_info, resp, total_req_capacity_m, total_req_qps_k, not_finished_records
        )
        obj = EvaluateRecordRepo().save_history(history)
        logger_debug(f"save_history: <{obj.__str__()}> success")
        return obj

    @classmethod
    def _save_evaluate_record(cls, action_info: dict, req: dict, capacity_info: ClusterCapacityInfo):
        """保存评估记录"""
        record = EvaluateRecordRepo().new_record_from_request(action_info, req, capacity_info)
        logger_debug(f"new_record_from_request: <{record.__str__()}> success")
        EvaluateRecordRepo().update_or_create(record)
        logger_debug(f"update_or_create: <{record.__str__()}> success")
        return record

    @classmethod
    def _save_evaluate_record_end(cls, record: CapacityEvaluateRecord, resp: dict):
        """保存评估记录结束"""
        EvaluateRecordRepo().update_record_resp(record, resp)

    @classmethod
    def _create_success_response(cls):
        """创建成功响应"""
        return {
            "status": ResultStatus.SUCCESS.value,
            "message": "no not finished record",
        }

    @classmethod
    def _evaluate_capacity(
        cls,
        capacity_info: ClusterCapacityInfo,
        model: dict,
        action_info: dict,
        total_req_capacity_m: float,
        total_req_qps_k: float,
        not_finished_records: list,
    ):
        """评估容量"""
        topo_info = capacity_info.topo_info
        response = cls._create_base_response(total_req_capacity_m, total_req_qps_k, not_finished_records)
        response.cluster_domain = topo_info.cluster_domain

        # 评估各个组件
        cls._evaluate_proxy_qps(response, topo_info, model, total_req_qps_k)
        cls._evaluate_backend_qps(response, topo_info, model, total_req_qps_k)
        cls._evaluate_capacity_usage(response, capacity_info, total_req_capacity_m)
        logger_debug(f"action_info: {action_info}")
        # approved_user = action_info.get("approved_user", "") # deprecated
        user = action_info.get("user", "")
        # response["approved_user"] = approver_user
        # 设置最终状态
        is_force = action_info.get("is_force", 0)  # 0: 不强制评估，1: 强制评估
        # is_force为True时，总是通过，设置评估人为user
        # is_force为False时，如果评估通过，则设置评估人
        response.approved_user = user if is_force > 0 else "system"
        all_approved_ok = response.proxy_approve_ok and response.backend_approve_ok and response.capacity_approve_ok

        if all_approved_ok:
            response.status = ResultStatus.SUCCESS.value
            response.message = _("评估通过,评估人:") + response.approved_user
        elif is_force > 0:
            all_approved_ok = True
            response.status = ResultStatus.SUCCESS.value
            response.message = _("强制评估通过,评估人:") + response.approved_user
        else:
            response.status = ResultStatus.FAILED.value
            response.message = _("评估不通过,评估人:") + response.approved_user
        return response

    @classmethod
    def _create_base_response(
        cls, total_req_capacity_m: float, total_req_qps_k: float, not_finished_records: list
    ) -> "Response":
        """创建基础响应"""
        response = Response()
        response.related_records_info = (
            f"records:{len(not_finished_records)}: total qps:{total_req_qps_k}K, "
            + f"total capacity: {round(total_req_capacity_m/1024, 2)}G"
        )

        response.related_records = {
            "req_qps_k_total": total_req_qps_k,
            "req_capacity_m_total": total_req_capacity_m,
            "req_num": len(not_finished_records),
            "req_list": [record.action_id for record in not_finished_records],
        }
        return response

    @classmethod
    def _evaluate_proxy_qps(cls, response: Response, topo_info, model: dict, req_qps_k: float):
        """评估Proxy QPS"""
        proxy_qps_k = model.get("proxy_qps") / 1000
        proxy_qps_k_total = proxy_qps_k * topo_info.proxy_num
        response.proxy_approve_ok = req_qps_k <= proxy_qps_k_total
        response.proxy_approve_info = _("Proxy:%d个,每个可支持Qps:%dK, 总共可支持Qps:%dK; 总qps需求:%dK; 是否通过:%s") % (
            topo_info.proxy_num,
            proxy_qps_k,
            proxy_qps_k_total,
            req_qps_k,
            response.proxy_approve_ok,
        )

    @classmethod
    def _evaluate_backend_qps(cls, response: Response, topo_info: ClusterTopoInfo, model: dict, req_qps_k: float):
        """评估后端QPS"""
        if topo_info.is_tendis_ssd() or topo_info.is_tendisplus():
            shard_qps_per_core = model.get("ssd_shard_qps_per_core")
        elif topo_info.is_memory_redis():
            shard_qps_per_core = model.get("shard_qps_per_core")
        else:
            shard_qps_per_core = model.get("shard_qps_per_core")
        shard_cpu_core_m = min(topo_info.shard_cpu_core_m, topo_info.get_shard_cpu_core_limit())
        shard_qps_k = shard_qps_per_core * (shard_cpu_core_m / 1000) / 1000
        shard_qps_k_total = shard_qps_k * topo_info.shard_num

        logger_debug(
            f"shard_qps_per_core: {shard_qps_per_core}, shard_cpu_core_m: {shard_cpu_core_m}, "
            "shard_qps_k: {shard_qps_k}, shard_qps_k_total: {shard_qps_k_total}"
        )
        response.backend_approve_ok = req_qps_k <= shard_qps_k_total

        response.backend_approve_info = _("分片规格:[%s],共%d个分片,每分片可支持Qps:%dK, 总共可支持Qps:%dK; " + "总Qps需求:%dK; 是否通过:%s") % (
            topo_info.shard_spec,
            topo_info.shard_num,
            shard_qps_k,
            shard_qps_k_total,
            req_qps_k,
            response.backend_approve_ok,
        )

    @classmethod
    def _evaluate_capacity_usage(cls, response: Response, capacity_info: ClusterCapacityInfo, req_capacity_m: float):
        """评估容量使用"""
        # 如果是memory_redis，检查内存容量是否足够
        storage_type = capacity_info.storage_type
        response.capacity_approve_ok = req_capacity_m <= capacity_info.get_free_capacity_m()
        response.capacity_approve_info = _("总容量(%s):%0.1fG,剩余容量:%0.1fG; 总容量需求:%0.1fG; 是否通过:%s") % (
            storage_type,
            capacity_info.get_total_capacity_m() / 1024,
            capacity_info.get_free_capacity_m() / 1024,
            req_capacity_m / 1024,
            response.capacity_approve_ok,
        )

    @classmethod
    def _determine_final_status(cls, response: Response) -> str:
        """确定最终状态"""
        all_approved = response.proxy_approve_ok and response.backend_approve_ok and response.capacity_approve_ok
        return ResultStatus.SUCCESS.value if all_approved else ResultStatus.FAILED.value
