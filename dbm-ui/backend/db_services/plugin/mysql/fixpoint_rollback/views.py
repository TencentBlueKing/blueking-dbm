from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.fixpoint_rollback.serializers import (
    BackupLogMySQLResponseSerializer,
    BackupLogTendbResponseSerializer,
    FilterBackupLogSerializer,
)
from backend.db_services.mysql.fixpoint_rollback.views import FixPointRollbackViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class FixPointRollbackApiGwViewSet(BaseOpenAPIViewSet, FixPointRollbackViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("通过获取集群最迟时间的最新一条备份记录"),
        query_serializer=FilterBackupLogSerializer(),
        responses={
            status.HTTP_200_OK: BackupLogTendbResponseSerializer(),
            status.HTTP_202_ACCEPTED: BackupLogMySQLResponseSerializer(),
        },
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=FilterBackupLogSerializer)
    def latest_time_backup_log(self, request, *args, **kwargs):
        return super().latest_time_backup_log(request, *args, **kwargs)
