import logging

from rest_framework.response import Response

from backend.flow.engine.controller.spider import SpiderController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class InstallSpiderClusterSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/install_spider_cluster
        params:
    }
    """

    def post(self, request):
        # logger.info("开始部署tenDB cluster HA场景")
        root_id = generate_root_id()
        test = SpiderController(root_id=root_id, ticket_data=request.data)
        test.spider_cluster_apply_scene()
        return Response({"root_id": root_id})
