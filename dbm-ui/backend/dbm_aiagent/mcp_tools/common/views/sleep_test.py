import logging
import time

from rest_framework import serializers
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet

logger = logging.getLogger("root")


class SleepTestOutputSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="测试消息")


class SleepTestMcpToolsViewSet(McpToolsViewSet):
    @mcp_tools_api_decorator(
        description="测试工具：等待 3 分钟后记录日志并返回一条消息",
        request_slz=serializers.Serializer,
        response_slz=SleepTestOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DBM],
        name_prefix="mcp_common",
        permission_classes=[],
        none_schema=True,
    )
    def sleep_test(self, request, *args, **kwargs):
        time.sleep(180)
        message = "MCP sleep test completed after 3 minutes."
        logger.info(message)
        return Response({"message": message})
