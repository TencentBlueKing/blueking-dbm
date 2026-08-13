# -*- coding: utf-8 -*-

from ..client import ItsmApi
from .base import BaseItsmBackend


class ItsmV3Backend(BaseItsmBackend):
    """ITSM V3 后端，保持旧版接口协议。"""

    version = "v3"

    def create_ticket(self, params, *args, **kwargs):
        """创建 ITSM V3 单据。"""
        return ItsmApi.create_ticket(params, *args, **kwargs)

    def ticket_approval_result(self, params, *args, **kwargs):
        """查询 ITSM V3 单据审批结果。"""
        return ItsmApi.ticket_approval_result(params, *args, **kwargs)

    def get_ticket_logs(self, params, *args, **kwargs):
        """查询 ITSM V3 单据日志。"""
        return ItsmApi.get_ticket_logs(params, *args, **kwargs)

    def get_ticket_info(self, params, *args, **kwargs):
        """查询 ITSM V3 单据详情。"""
        return ItsmApi.get_ticket_info(params, *args, **kwargs)

    def operate_node(self, params, *args, **kwargs):
        """处理 ITSM V3 单据节点。"""
        return ItsmApi.operate_node(params, *args, **kwargs)

    def operate_ticket(self, params, *args, **kwargs):
        """处理 ITSM V3 单据。"""
        return ItsmApi.operate_ticket(params, *args, **kwargs)

    def get_ticket_status(self, params, *args, **kwargs):
        """查询 ITSM V3 单据状态。"""
        return ItsmApi.get_ticket_status(params, *args, **kwargs)

    def get_service_catalogs(self, params, *args, **kwargs):
        """查询 ITSM V3 服务目录。"""
        return ItsmApi.get_service_catalogs(params, *args, **kwargs)

    def get_services(self, params, *args, **kwargs):
        """查询 ITSM V3 服务列表。"""
        return ItsmApi.get_services(params, *args, **kwargs)

    def create_service_catalog(self, params, *args, **kwargs):
        """创建 ITSM V3 服务目录。"""
        return ItsmApi.create_service_catalog(params, *args, **kwargs)

    def import_service(self, params, *args, **kwargs):
        """导入 ITSM V3 服务。"""
        return ItsmApi.import_service(params, *args, **kwargs)

    def update_service(self, params, *args, **kwargs):
        """更新 ITSM V3 服务。"""
        return ItsmApi.update_service(params, *args, **kwargs)
