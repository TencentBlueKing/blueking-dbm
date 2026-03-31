from rest_framework.routers import DefaultRouter

from backend.db_services.plugin.cluster_entry.views import ClusterEntryOpenAPIViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r"", ClusterEntryOpenAPIViewSet, basename="cluster_entry")
urlpatterns = router.urls
