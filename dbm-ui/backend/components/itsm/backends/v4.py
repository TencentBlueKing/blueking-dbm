# -*- coding: utf-8 -*-

import json
import time

from ..client import ItsmV4Api
from .base import BaseItsmBackend


class ItsmV4Backend(BaseItsmBackend):
    """ITSM V4 后端，将 V4 接口协议适配为旧版调用协议。"""

    version = "v4"
    SN_PREFIX = "ITSM_V4:"

    @classmethod
    def format_ticket_sn(cls, ticket_id):
        """将 ITSM V4 单据 ID 拼接 'ITSM_V4:'标识 用作和旧版的sn做区分。"""
        return f"{cls.SN_PREFIX}{ticket_id}"

    @classmethod
    def get_ticket_id(cls, sn):
        """从兼容旧版存储的 sn 中解析 ITSM V4 单据 ID。"""
        if isinstance(sn, (list, tuple)):
            sn = sn[0] if sn else ""
        sn = str(sn)
        return sn[len(cls.SN_PREFIX) :] if sn.startswith(cls.SN_PREFIX) else sn

    @classmethod
    def format_ticket_id_params(cls, params):
        """将旧版 sn 查询参数转换为 ITSM V4 详情接口的 id 参数。"""
        return {**params, "id": cls.get_ticket_id(params.get("sn"))}

    @classmethod
    def format_ticket_log_params(cls, params):
        """将旧版 sn 查询参数转换为 ITSM V4 日志接口的 ticket_id 参数。"""
        return {
            **{key: value for key, value in params.items() if key not in ["sn", "id"]},
            "ticket_id": cls.get_ticket_id(params.get("sn")),
        }

    @classmethod
    def normalize_ticket_detail(cls, detail):
        """将 ITSM V4 单据详情转换为旧版详情返回结构。"""
        normalized_detail = {
            **detail,
            "current_status": detail.get("status", "").upper(),
            "ticket_url": detail.get("frontend_url"),
        }
        for step in normalized_detail.get("current_steps", []):
            if "state_id" not in step:
                step["state_id"] = step.get("id") or step.get("task_id")
        return normalized_detail

    @classmethod
    def normalize_ticket_approval_result(cls, detail):
        """将 ITSM V4 单据详情转换为旧版审批结果结构。"""
        return {
            "update_at": detail.get("updated_at"),
            "current_status": detail.get("status", "").upper(),
            "approve_result": detail.get("approve_result"),
            "ticket_url": detail.get("frontend_url"),
        }

    @classmethod
    def normalize_ticket_logs(cls, logs):
        """将 ITSM V4 单据日志转换为旧版日志返回结构。"""
        log_list = logs.get("items", [])
        return {"logs": [{**log, "message": log.get("action_display")} for log in log_list]}

    @classmethod
    def get_approve_action(cls, params):
        """根据旧版审批字段计算 ITSM V4 审批动作。"""
        fields = {field.get("key"): field.get("value") for field in params.get("fields", [])}
        is_approved = fields.get("is_approved")
        if is_approved is None and params.get("fields"):
            is_approved = params["fields"][0].get("value")
        if isinstance(is_approved, str):
            is_approved = json.loads(is_approved.lower())
        return "approve" if is_approved else "refuse"

    @classmethod
    def format_deliver_processors(cls, processors):
        """将旧版转单处理人转换为 ITSM V4 用户对象列表。"""
        if isinstance(processors, str):
            processors = [processor.strip() for processor in processors.split(",") if processor.strip()]
        elif processors is None:
            processors = []
        return [{"id": processor, "type": "user"} for processor in processors]

    @classmethod
    def format_handle_ticket_params(cls, params):
        """将旧版单据处理参数转换为 ITSM V4 处理接口参数。"""
        action_type = params.get("action_type")
        action_method = cls.get_approve_action(params) if action_type == "TRANSITION" else action_type.lower()
        action_params = {"desc": params.get("remark")}
        if action_type == "DELIVER":
            action_params = {
                "to": cls.format_deliver_processors(params.get("processors")),
                "desc": params.get("remark"),
            }
        if action_type == "WITHDRAW":
            action_params["target_activity"] = params.get("activity_key")
        return {
            "ticket_id": cls.get_ticket_id(params.get("sn")),
            "task_id": params.get("task_id"),
            "operator": params.get("operator") or params.get("bk_username"),
            "form_data": params.get("form_data", {}),
            "action": {
                "method": action_method,
                "params": action_params,
            },
        }

    def create_ticket(self, params, *args, **kwargs):
        """创建 ITSM V4 单据，并将返回 ID 兼容为旧版 sn。"""
        data = ItsmV4Api.create_ticket(params, *args, **kwargs)
        if "id" in data:
            data = {**data, "sn": self.format_ticket_sn(data["id"])}
            data.pop("id")
        return data

    def ticket_approval_result(self, params, *args, **kwargs):
        """查询 ITSM V4 单据审批结果，并兼容旧版审批结果结构。"""
        detail = ItsmV4Api.get_ticket_detail(self.format_ticket_id_params(params), *args, **kwargs)
        if detail.get("status", "").lower() == "draft":
            # 提单后 ITSM 状态可能有延迟，这里等待后重试一次。
            time.sleep(1)
            detail = ItsmV4Api.get_ticket_detail(self.format_ticket_id_params(params), *args, **kwargs)
        return [self.normalize_ticket_approval_result(detail)]

    def get_ticket_logs(self, params, *args, **kwargs):
        """查询 ITSM V4 单据日志，并兼容旧版日志结构。"""
        logs = ItsmV4Api.get_ticket_logs(self.format_ticket_log_params(params), *args, **kwargs)
        return self.normalize_ticket_logs(logs)

    def get_ticket_info(self, params, *args, **kwargs):
        """查询 ITSM V4 单据详情，并兼容旧版详情结构。"""
        detail = ItsmV4Api.get_ticket_detail(self.format_ticket_id_params(params), *args, **kwargs)
        return self.normalize_ticket_detail(detail)

    def operate_node(self, params, *args, **kwargs):
        """处理 ITSM V4 单据节点。"""
        return ItsmV4Api.handle_ticket(self.format_handle_ticket_params(params), *args, **kwargs)

    def operate_ticket(self, params, *args, **kwargs):
        """处理 ITSM V4 单据。"""
        return ItsmV4Api.handle_ticket(self.format_handle_ticket_params(params), *args, **kwargs)

    def migrate_system(self, params, *args, **kwargs):
        """迁移 ITSM V4 系统流程。"""
        return ItsmV4Api.migrate_system(params, *args, **kwargs)
