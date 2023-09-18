import logging
import uuid

from rest_framework.response import Response

from backend.flow.engine.controller.spider import SpiderController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class AddTmpSpiderSceneApiView(FlowTestView):
    def post(self, request):
        root_id = uuid.uuid1().hex
        test = SpiderController(root_id=root_id, ticket_data=request.data)
        test.spider_add_tmp_node_scene()
        return Response({"root_id": root_id})
