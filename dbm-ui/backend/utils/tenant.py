from django.conf import settings

from backend.db_meta.models.app import TenantCache
from backend.utils.local import local


class TenantHandler:
    @staticmethod
    def local_set_tenant_by_biz(bk_biz_id):
        """
        通过业务ID获取租户ID并注入线程本地存储
        返回注入的租户ID
        """
        tenant_id = TenantCache.get_tenant_with_app(bk_biz_id)
        local.tenant_id = tenant_id
        return tenant_id

    @staticmethod
    def get_tenant_id_by_biz(bk_biz_id):
        """通过业务ID获取租户ID"""
        return TenantCache.get_tenant_with_app(bk_biz_id)

    @staticmethod
    def get_tenant_id_from_params(params):
        """从参数中获取租户ID"""
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return settings.DEFAULT_TENANT_ID
        return params.get("tenant_id")

    @staticmethod
    def get_tenant_id_from_request():
        """从当前请求中获取租户ID"""
        from backend.utils.local import local

        if hasattr(local, "tenant_id"):
            return local.tenant_id
        if hasattr(local, "request") and hasattr(local.request, "user"):
            return local.request.user.tenant_id
        return None
