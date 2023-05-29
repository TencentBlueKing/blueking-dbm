import logging

from rest_framework.response import Response

from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class ReduceTBinlogDumperSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/reduce_tbinlogumper
        params:
    }
    """

    def post(self, request):
        # 卸载TBinlogDumper实例
        root_id = generate_root_id()
        test = TBinlogDumperController(root_id=root_id, ticket_data=request.data)
        test.reduce_nodes_scene()
        return Response({"root_id": root_id})
