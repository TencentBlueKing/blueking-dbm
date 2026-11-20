# -*- coding: utf-8 -*-
"""Marker node so failed-DTS cleanup can identify Mongo DTS flows by component code."""

from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService

# Keep in sync with MongoDBDtsFlow.MONGO_DTS_COMPONENT_CODE
MONGO_DTS_COMPONENT_CODE = "mongo_dts"


class MongoDtsMarkerService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        return True


class MongoDtsMarkerComponent(Component):
    name = __name__
    code = MONGO_DTS_COMPONENT_CODE
    bound_service = MongoDtsMarkerService
