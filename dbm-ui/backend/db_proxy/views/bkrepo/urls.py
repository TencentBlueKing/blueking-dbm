# -*- coding: utf-8 -*-

from rest_framework.routers import DefaultRouter

from backend.db_proxy.views.bkrepo.views import BKRepoProxyPassViewSet

bkrepo_router = DefaultRouter()
bkrepo_router.register(r"", BKRepoProxyPassViewSet, basename="bkrepo")

urlpatterns = bkrepo_router.urls
