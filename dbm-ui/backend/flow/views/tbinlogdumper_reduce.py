import logging
import uuid

from rest_framework.response import Response

from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class ReduceTBinlogDumperSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/reduce_tbinlogumper
        params:
    }
    """

    def post(self, request):
        # 卸载TBinlogDumper实例
        root_id = uuid.uuid1().hex
        test = TBinlogDumperController(root_id=root_id, ticket_data=request.data)
        test.reduce_nodes_scene()
        return Response({"root_id": root_id})
