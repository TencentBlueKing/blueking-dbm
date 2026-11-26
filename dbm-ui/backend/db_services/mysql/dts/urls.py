from django.urls import path

from backend.db_services.mysql.dts.views import MySQLDtsMigrateViewSet

urlpatterns = [
    path(
        "dts/tasks/reset/",
        MySQLDtsMigrateViewSet.as_view({"post": "reset_task"}),
    ),
    path(
        "dts/schema_sql/",
        MySQLDtsMigrateViewSet.as_view({"post": "schema_sql"}),
    ),
]
