from rest_framework.routers import DefaultRouter

from .tendbcluster.views import SpiderApiGwViewSet

router = DefaultRouter(trailing_slash=True)

router.register(r"spider_resources", SpiderApiGwViewSet, basename="spider_resource")

urlpatterns = []

urlpatterns += router.urls
