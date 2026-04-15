# -*- coding: utf-8 -*-
"""
TenDBCluster spider layer full disaster recovery — flow debug entry (same Controller as ticket).
"""

from rest_framework.response import Response

from backend.flow.engine.controller.spider import SpiderController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id


class SpiderLayerDisasterRecoverSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/spider_layer_disaster_recover
    POST body: same shape as ticket ticket_data (uid, bk_biz_id, infos, ...).
    """

    def post(self, request):
        root_id = generate_root_id()
        flow = SpiderController(root_id=root_id, ticket_data=request.data)
        flow.tendbcluster_spider_layer_disaster_recover_scene()
        return Response({"root_id": root_id})
