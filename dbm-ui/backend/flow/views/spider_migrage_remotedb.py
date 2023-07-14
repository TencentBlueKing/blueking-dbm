import logging
import uuid

from rest_framework.response import Response

from backend.flow.engine.controller.spider import SpiderController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class SpiderMigrateRemoteDbSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/install_spider_cluster
        params:
    }
    """

    @staticmethod
    def post(request):
        # logger.info("spider remotedb 成对迁移")
        root_id = uuid.uuid1().hex
        test = SpiderController(root_id=root_id, ticket_data=request.data)
        test.migrate_remotedb()
        return Response({"root_id": root_id})
