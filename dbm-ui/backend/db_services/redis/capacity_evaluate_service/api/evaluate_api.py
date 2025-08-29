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
import datetime
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_services.redis.capacity_evaluate_service import util
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from backend.db_services.redis.capacity_evaluate_service.repositories.redis_cluster_repo import DbmClusterRepository
from backend.db_services.redis.capacity_evaluate_service.services.evaluate_service import (
    CapacityEvaluateService,
    ResultStatus,
    ResultCode,
)


class EvaluateAPI:
    """容量评估API"""

    def __init__(self):
        """do nothing"""

    @classmethod
    def validate_request(cls, request, action_info):
        """validate request"""
        action_info["start_time"] = parse_datetime(action_info.get("start_time"))
        action_info["end_time"] = parse_datetime(action_info.get("end_time"))

        if action_info["start_time"] > action_info["end_time"]:
            return "start_time is greater than end_time"
        if action_info["end_time"].timestamp() < datetime.datetime.now().timestamp():
            return "end_time is in the past"

        for one_req in request.data.get("req"):
            if not one_req.get("req_capacity_m") and not one_req.get("req_capacity_g"):
                return "req_capacity_m and req_capacity_g are both 0"
            if one_req.get("req_capacity_m") and one_req.get("req_capacity_g"):
                values = f"{one_req.get('req_capacity_g')},{one_req.get('req_capacity_m')}"
                return f"req_capacity_m and req_capacity_g are both not 0 ({values})"
            if one_req.get("req_capacity_g"):
                one_req["req_capacity_m"] = one_req.get("req_capacity_g") * 1024
        if not one_req.get("req_capacity_m"):
            return "req_capacity_m is 0"

        return None  # ok to validate_request

    @classmethod
    def do_evaluate(cls, request):
        """评估用户发过来的请求"""
        bk_biz_id = request.data.get("action_info").get("bk_biz_id")
        action_info = request.data.get("action_info")
        resp = cls.EvaluateResponse(
            bk_biz_id,
            action_info,
            action_info.get("action_id"),
            action_info.get("action_name"),
            action_info.get("user"),
        )

        err_msg = cls.validate_request(request, action_info)
        if err_msg:
            return resp.Error(err_msg)

        result_detail = []
        total, success, failed, error = 0, 0, 0, 0
        time_elapsed_ms = 0
        for one_req in request.data.get("req"):
            cluster_domain = one_req.get("cluster_domain")
            cluster = DbmClusterRepository.get_cluster_by_domain(cluster_domain)
            if not cluster:
                raise Exception(f"cluster not found for instance: {cluster_domain}")
            if not ClusterType.is_redis_cluster_type(cluster.cluster_type):
                if not util.is_dev():
                    raise Exception(f"cluster type {cluster.cluster_type} is not supported")
                else:
                    util.logger_debug(f"cluster type {cluster.cluster_type} is not supported, but in dev environment")
            one_result = CapacityEvaluateService.evaluate_one(action_info, one_req, bk_biz_id, cluster.id)
            result_detail.append(one_result.to_dict())
            total += 1
            time_elapsed_ms += one_result.time_elapsed_ms
            if one_result.status == ResultStatus.SUCCESS.value:
                success += 1
            elif one_result.status == ResultStatus.FAILED.value:
                failed += 1
            else:
                error += 1

        resp.result_detail = result_detail
        time_elapsed_second = round(time_elapsed_ms / 1000, 2)
        resp.time_elapsed_second = time_elapsed_second
        if success == total:
            return resp.Success(
                _("%d个评估需求,全部评估通过, 耗时%s秒") % (total, time_elapsed_second),
            )

        else:
            return resp.Error(
                _("%d个评估需求, %d个通过, %d个失败, %d个出错, 耗时%s秒, 请检查") % (total, success, failed, error, time_elapsed_second),
            )

    class EvaluateResponse:
        """evaluate api response"""

        def __init__(self, bk_biz_id, action_info, action_id, action_name, user):
            self.bk_biz_id = bk_biz_id
            self.action_info = action_info
            self.action_id = action_id
            self.action_name = action_name
            self.user = user
            self.time_elapsed_second = 0
            self.result_code = 0
            self.result_status = ""
            self.result_msg = ""
            self.result_detail = []

        def to_dict(self):
            return {
                "bk_biz_id": self.bk_biz_id,
                "action_info": self.action_info,
                "time_elapsed_second": self.time_elapsed_second,
                "result_code": self.result_code,
                "result_status": self.result_status,
                "result_msg": self.result_msg,
                "result_detail": self.result_detail,
            }

        def Error(self, msg):
            self.result_code = ResultCode.ERROR.value
            self.result_status = ResultStatus.ERROR.value
            self.result_msg = msg
            return self.to_dict()

        def Success(self, msg):
            self.result_code = ResultCode.SUCCESS.value
            self.result_status = ResultStatus.SUCCESS.value
            self.result_msg = msg
            return self.to_dict()
