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
import json

from django.utils import timezone

from backend.db_services.redis.capacity_evaluate_service.models.tb_capacity_evaluate import CapacityEvaluateRecord
from backend.db_services.redis.capacity_evaluate_service.models.tb_evaluate_history import CapacityEvaluateHistory
from backend.db_services.redis.capacity_evaluate_service.repositories.cluster_topo_repo import ClusterCapacityInfo
from backend.db_services.redis.capacity_evaluate_service.util import logger_debug


class EvaluateRecordRepo:
    """evaluate record repo"""

    def get_record_by_instance_id(self, instance_id: int) -> CapacityEvaluateRecord:
        """get evaluate record by instance id"""
        # 注意：模型中可能没有 instance_id 字段，这个方法可能需要重新设计
        # 或者使用 cluster_id 来查找
        try:
            return CapacityEvaluateRecord.objects.get(cluster_id=instance_id)
        except EvaluateRecordRepo.DoesNotExist:
            return None

    def get_record_by_action_id(self, action_id: str) -> CapacityEvaluateRecord:
        """get evaluate record by action id"""
        try:
            return CapacityEvaluateRecord.objects.get(action_id=action_id)
        except CapacityEvaluateRecord.DoesNotExist:
            return None

    def get_not_finished_record(
        self, cluster_id: int, act_start_time: datetime.datetime
    ) -> (int, int, [CapacityEvaluateRecord]):
        """get evaluate record by cluster id and start time"""
        # act_start_time can not in the past
        now_time = timezone.now()
        # start_time = act_start_time if act_start_time.timestamp() > now_time.timestamp() else now_time
        records = CapacityEvaluateRecord.objects.filter(cluster_id=cluster_id, end_time__gte=now_time)
        total_req_capacity_m = 0
        total_req_qps_k = 0
        not_finished_records = []
        for record in records:
            if self.get_status(record) == "finished":
                continue
            else:
                not_finished_records.append(record)
                total_req_capacity_m += record.req_capacity_m
                total_req_qps_k += record.req_qps_k
        return total_req_capacity_m, total_req_qps_k, not_finished_records

    def get_status(self, record: CapacityEvaluateRecord) -> str:
        """get status of record, return not_start, running, finished"""
        now = datetime.datetime.now()
        # if start_time > now
        if record.start_time.timestamp() > now.timestamp():
            return "not_start"
        if record.end_time.timestamp() < now.timestamp():
            return "finished"
        else:
            return "running"

    @classmethod
    def new_record_from_request(
        cls, action_info: dict, request: dict, capacity_info: ClusterCapacityInfo
    ) -> CapacityEvaluateRecord:
        """new record from request and capacity info"""
        record = CapacityEvaluateRecord()
        # cluster info
        cluster_topo_info = capacity_info.topo_info
        record.cluster_id = cluster_topo_info.cluster_id
        record.cluster_domain = cluster_topo_info.cluster_domain
        record.cluster_type = cluster_topo_info.cluster_type
        record.proxy_count = cluster_topo_info.proxy_num
        # record.free_size_mb = int(capacity_info.get_mem_free_m())
        # record.total_size_mb = int(capacity_info.get_mem_total_m())
        # action info
        record.action_id = action_info.get("action_id")
        record.action_name = action_info.get("action_name")
        record.action_type = action_info.get("action_type")
        record.action_user = action_info.get("action_user", "")
        record.bk_biz_id = action_info.get("bk_biz_id")
        record.bk_biz_name = action_info.get("bk_biz_name", "")
        record.evaluate_method = action_info.get("evaluate_method", "")
        record.evaluate_time = timezone.now()
        record.start_time = action_info.get("start_time")
        record.end_time = action_info.get("end_time")
        # request info
        record.req_qps_k = request.get("req_qps_k")
        record.req_capacity_m = request.get("req_capacity_m")
        record.key_pattern = request.get("key_pattern")
        record.req_flag_no_big_key_with_a_lot_of_member = request.get("req_flag_no_big_key_with_a_lot_of_member")
        record.req_flag_no_big_result = request.get("req_flag_no_big_result")
        record.req_flag_no_big_value = request.get("req_flag_no_big_value")
        record.req_flag_no_hot_key = request.get("req_flag_no_hot_key")
        record.req_flag_no_use_dns = request.get("req_flag_no_use_dns", 0)
        record.is_force = request.get("is_force", 0)
        return record

    @classmethod
    def update_or_create(cls, record: CapacityEvaluateRecord) -> (CapacityEvaluateRecord, bool):
        """update_or_create evaluate record"""
        obj, created = CapacityEvaluateRecord.objects.update_or_create(
            cluster_id=record.cluster_id, action_id=record.action_id, defaults=record.__data__()
        )
        return obj, created

    @classmethod
    def update_record_resp(cls, record: CapacityEvaluateRecord, resp: dict):
        """update record resp"""
        logger_debug(f"update_record_resp: <{resp}>")
        CapacityEvaluateRecord.objects.filter(action_id=record.action_id, cluster_id=record.cluster_id).update(
            **{
                "last_approved_time": timezone.now(),
                "last_approved_user": "system",
                "last_approved_status": 1
                if resp.get("proxy_approve_ok") and resp.get("backend_approve_ok") and resp.get("capacity_approve_ok")
                else 0,
            }
        )
        return record

    # 将tb_capacity_evaluate 的记录保存到tb_capacity_evaluate_history
    @classmethod
    def save_history(cls, history: CapacityEvaluateHistory):
        """save history"""
        obj = CapacityEvaluateHistory.objects.create(**history.__data__())
        return obj

    @classmethod
    def new_history_from_request(
        cls,
        action_info: dict,
        request: dict,
        capacity_info: ClusterCapacityInfo,
        resp: dict,
        total_req_capacity_m: float,
        total_req_qps_k: float,
        not_finished_records: list,
    ):
        """new history from request and capacity info"""
        history = CapacityEvaluateHistory()
        # 本次评估的简要信息
        history.action_id = action_info.get("action_id")
        history.action_name = action_info.get("action_name")
        history.action_type = action_info.get("action_type")
        history.bk_biz_id = action_info.get("bk_biz_id")
        history.bk_biz_name = action_info.get("bk_biz_name", "")
        # 当前集群的容量信息
        history.cluster_id = capacity_info.topo_info.cluster_id
        history.cluster_domain = capacity_info.topo_info.cluster_domain
        history.cluster_type = capacity_info.topo_info.cluster_type
        history.free_size_mb = int(capacity_info.get_mem_free_m())
        history.total_size_mb = int(capacity_info.get_mem_total_m())
        history.proxy_count = capacity_info.topo_info.proxy_num
        # 本次评估的简要信息
        history.is_force = action_info.get("is_force", 0)
        history.evaluate_method = action_info.get("evaluate_method", "")
        history.evaluate_time = timezone.now()
        history.req_qps_k = request.get("req_qps_k")
        history.req_capacity_m = request.get("req_capacity_m")
        history.req_flags_json = "todo"
        # 相关评估记录的简要信息
        history.req_qps_k_total = total_req_qps_k
        history.req_capacity_m_total = total_req_capacity_m

        not_finished_records_json = []
        for record in not_finished_records:
            # 跳过本次评估的记录. 因为本次评估的记录已经包含在本次评估的简要信息中
            if record.action_id == action_info.get("action_id"):
                continue
            not_finished_records_json.append(
                {
                    "action_id": record.action_id,
                    "action_name": record.action_name,
                    "action_type": record.action_type,
                    "req_qps_k": record.req_qps_k,
                    "req_capacity_m": record.req_capacity_m,
                    "start_time": record.start_time.strftime("%Y-%m-%d %H:%M:%S:%Z"),
                    "end_time": record.end_time.strftime("%Y-%m-%d %H:%M:%S:%Z"),
                    "action_user": record.action_user,
                    "last_approved_time": record.last_approved_time.strftime("%Y-%m-%d %H:%M:%S:%Z"),
                    "last_approved_user": record.last_approved_user,
                }
            )
        history.not_finished_records_json = json.dumps(not_finished_records_json, ensure_ascii=False)
        # 本次评估结果
        history.action_user = action_info.get("action_user", "")
        history.approved_time = timezone.now()
        history.time_elapsed_ms = resp.get("time_elapsed_ms")
        history.approved_user = resp.get("approved_user")
        history.approved_status = resp.get("status")
        history.approved_comment = resp.get("message")
        return history
