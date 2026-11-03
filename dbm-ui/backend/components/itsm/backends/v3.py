# -*- coding: utf-8 -*-

from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied

from ..client import ItsmApi
from .base import BaseItsmBackend


class ItsmV3Backend(BaseItsmBackend):
    """ITSM V3 后端，保持旧版接口协议。"""

    version = "v3"

    def verify_callback(self, ticket_id, data):
        """校验 V3 回调中的 token。"""
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise PermissionDenied(_("ITSM 回调凭证缺失或格式错误"))
        # 组件接口已解包外层响应，此处读取 data 中的校验结果。
        result = self.verify_token({"token": token}, use_admin=True)
        if not isinstance(result, dict) or result.get("is_passed") is not True:
            raise PermissionDenied(_("无效的 ITSM 回调凭证"))

    def verify_token(self, params, *args, **kwargs):
        return ItsmApi.verify_token(params, *args, **kwargs)

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
