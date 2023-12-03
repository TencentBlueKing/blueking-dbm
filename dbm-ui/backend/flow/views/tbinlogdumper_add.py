import logging
import uuid

from rest_framework.response import Response

from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class InstallTBinlogDumperSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/install_tbinlogumper
        params:
    }
    """

    def post(self, request):
        # logger.info("开始部署tenDB cluster HA场景")
        root_id = uuid.uuid1().hex
        test = TBinlogDumperController(root_id=root_id, ticket_data=request.data)
        test.add_nodes_scene()
        return Response({"root_id": root_id})


class EnableTBinlogDumperSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/enable_tbinlogumper
        params:
    }
    """

    def post(self, request):
        root_id = uuid.uuid1().hex
        test = TBinlogDumperController(root_id=root_id, ticket_data=request.data)
        test.enable_nodes_scene()
        return Response({"root_id": root_id})


class DisableTBinlogDumperSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/disable_tbinlogumper
        params:
    }
    """

    def post(self, request):
        root_id = uuid.uuid1().hex
        test = TBinlogDumperController(root_id=root_id, ticket_data=request.data)
        test.disable_nodes_scene()
        return Response({"root_id": root_id})
