from django.conf import settings
from django.utils.translation import ugettext as _

from backend.components import UserManagerApi
from backend.db_meta.models.app import TenantCache
from backend.exceptions import ApiRequestError
from backend.utils.local import local


class TenantHandler:
    @classmethod
    def init_tenant_config(cls, tenant_id):
        from backend.db_periodic_task.local_tasks.db_meta.update_app_cache import bulk_update_app_cache
        from backend.ticket.handler import TicketHandler

        # 初始化租户和cc数据
        bulk_update_app_cache(tenant_id)

        # 初始化租户的流程配置
        TicketHandler.ticket_flow_config_init(tenant_id)

    @classmethod
    def update_tenant_data(cls):

        tenant_list = UserManagerApi.list_tenant(params={"tenant_id": settings.DEFAULT_TENANT_ID}, raw=True)["data"]
        exists = list(TenantCache.objects.all().values_list("tenant_id", flat=True))

        # todo，补充新增加的租户信息
        new_tenants = [
            TenantCache(tenant_id=tenant["id"], tenant_name=tenant["name"], status=tenant["status"])
            for tenant in tenant_list
            if tenant["id"] not in exists
        ]
        # 查询当前租户的admin
        user_params = {"lookups": "bk_admin", "lookup_field": "login_name"}
        for tenant in new_tenants:
            params = {"tenant_id": tenant.tenant_id, **user_params}
            admin = UserManagerApi.batch_lookup_virtual_user(params=params, raw=True)["data"]
            tenant.admin = admin[0]["bk_username"] if admin else ""
        # 批量创建
        TenantCache.objects.bulk_create(new_tenants)

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
    def get_tenant_id_from_local():
        """从当前请求中获取租户ID"""
        from backend.utils.local import local

        if hasattr(local, "tenant_id"):
            return local.tenant_id
        if hasattr(local, "request") and hasattr(local.request, "user"):
            return local.request.user.tenant_id
        return None

    @classmethod
    def get_tenant_id(cls):
        """获取当前租户ID，确保在所有情况下都有返回值"""
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return settings.DEFAULT_TENANT_ID

        # 其次从线程本地获取
        tenant_id = cls.get_tenant_id_from_local()
        if tenant_id:
            return tenant_id

        raise ApiRequestError(_("无法获取当前请求的租户ID"))
