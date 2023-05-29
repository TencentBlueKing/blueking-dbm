import logging
import uuid

from rest_framework.response import Response

from backend.flow.engine.controller.spider import SpiderController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class SpiderSemanticCheckSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/install_spider_cluster
        params:
    }
    """

    def post(self, request):
        # logger.info("开始部署tenDB cluster HA场景")
        root_id = uuid.uuid1().hex
        test = SpiderController(root_id=root_id, ticket_data=request.data)
        test.spider_semantic_check_scene()
        return Response({"root_id": root_id})
