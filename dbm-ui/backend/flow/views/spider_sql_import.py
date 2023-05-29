import logging

from rest_framework.response import Response

from backend.flow.engine.controller.spider import SpiderController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class SpiderSqlImportSceneApiView(FlowTestView):
    def post(self, request):
        root_id = generate_root_id()
        test = SpiderController(root_id=root_id, ticket_data=request.data)
        test.spider_sql_import_scene()
        return Response({"root_id": root_id})
