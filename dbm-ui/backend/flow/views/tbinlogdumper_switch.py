import logging
import uuid

from rest_framework.response import Response

from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class SwitchTBinlogDumperSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/swtich_tbinlogumper
        params:
    }
    """

    def post(self, request):
        # 迁移部署TBinlogDumper实例
        root_id = uuid.uuid1().hex
        test = TBinlogDumperController(root_id=root_id, ticket_data=request.data)
        test.switch_nodes_scene()
        return Response({"root_id": root_id})
