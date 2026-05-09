# -*- coding:utf-8 -*-
import json
import logging

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action

from backend.bk_web import viewsets
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from blueking.bkvision.settings import BKVISION_APIGW_URL, PRE_PROCESS_FUNC
from blueking.bkvision.utils import normalize_request_headers

logger = logging.getLogger("root")


class BkVisionCsrfExemptSessionAuthentication(SessionAuthentication):
    """跳过 DRF 内置的 CSRF 校验，仅用于 BKVision 代理透传场景。"""

    def enforce_csrf(self, request):
        return


def build_headers(request):
    request_headers = normalize_request_headers(request)
    request_headers.update({
        "Content-Type": "application/json; charset=utf-8",
        "X-Bkapi-Authorization": json.dumps({
            "bk_app_code": settings.APP_CODE,
            "bk_app_secret": settings.SECRET_KEY,
        })
    })
    return request_headers


def proxy_request(request, path):
    headers = build_headers(request)
    params = request.GET.copy()
    proxy_response = requests.request(
        method=request.method,
        url=f"{BKVISION_APIGW_URL}{path}",
        params=params,
        data=request.body,
        headers=headers,
        verify=False
    )
    return HttpResponse(
        proxy_response.content,
        status=proxy_response.status_code,
        content_type=proxy_response.headers.get('Content-Type')
    )


@method_decorator(csrf_exempt, name="dispatch")
class BkVisionViewSet(viewsets.SystemViewSet):
    """BKVision 代理视图 - 需要平台管理权限"""

    authentication_classes = [BkVisionCsrfExemptSessionAuthentication]
    default_permission_class = [ResourceActionPermission([ActionEnum.PLATFORM_MANAGE])]

    def initial(self, request, *args, **kwargs):
        # 提前缓存 request.body 到 Django HttpRequest._body：
        # 后续 IAM 权限审计 / DRF parser 会读 request.data 消费底层 stream，
        # 若不预先缓存，视图里再访问 request.body 会抛 RawPostDataException。
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            _ = request.body
        super().initial(request, *args, **kwargs)

    @action(methods=["POST"], detail=False)
    def query_variable(self, request):
        """获取变量数据"""
        try:
            return proxy_request(request, '/api/v1/variable/query/')
        except Exception as e:
            logger.exception("[bkvision] query_variable failed: %s", e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})

    @action(methods=["POST"], detail=False)
    def test_variable(self, request):
        """测试变量数据"""
        try:
            return proxy_request(request, '/api/v1/variable/test/')
        except Exception as e:
            logger.exception("[bkvision] test_variable failed: %s", e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})

    @action(methods=["POST"], detail=False, url_path="preview_field_data/(?P<uid>\\w+)")
    def preview_field_data(self, request, uid):
        """获取字段数据"""
        try:
            return proxy_request(request, f'/api/v1/field/{uid}/preview_data/')
        except Exception as e:
            logger.exception("[bkvision] preview_field_data failed, uid=%s: %s", uid, e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})

    @action(methods=["POST"], detail=False)
    def query_datasource(self, request):
        """查询数据源数据"""
        try:
            request = PRE_PROCESS_FUNC(request)
            return proxy_request(request, '/api/v1/datasource/query/')
        except Exception as e:
            logger.exception("[bkvision] query_datasource failed: %s", e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})

    @action(methods=["POST"], detail=False)
    def query_dataset(self, request):
        """查询数据集数据"""
        try:
            request = PRE_PROCESS_FUNC(request)
            return proxy_request(request, '/api/v1/dataset/query/')
        except Exception as e:
            logger.exception("[bkvision] query_dataset failed: %s", e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})

    @action(methods=["GET"], detail=False)
    def query_meta(self, request):
        """获取配置"""
        try:
            return proxy_request(request, '/api/v1/meta/query/')
        except Exception as e:
            logger.exception("[bkvision] query_meta failed: %s", e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})

    @action(methods=["GET"], detail=False)
    def get_panel(self, request):
        """获取图表配置"""
        try:
            return proxy_request(request, '/api/v1/panel/')
        except Exception as e:
            logger.exception("[bkvision] get_panel failed: %s", e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})

    @action(methods=["GET"], detail=False)
    def get_child_panels(self, request):
        """获取子图列表"""
        try:
            return proxy_request(request, '/api/v1/panel/get_child_panels/')
        except Exception as e:
            logger.exception("[bkvision] get_child_panels failed: %s", e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})

    @action(methods=["GET"], detail=False)
    def get_app_share_list(self, request):
        """获取应用有权限的嵌入列表"""
        try:
            response = proxy_request(request, '/api/v1/share/get_app_share_list/')
            datas = json.loads(response.content)["data"]
            data = next((data["share"] for data in datas if data["name"] == "DBM内部环境"), [])
            return JsonResponse({"result": True, "message": "", "data": data, "code": 200})
        except Exception as e:
            logger.exception("[bkvision] get_app_share_list failed: %s", e)
            return JsonResponse({"result": False, "message": "[bkvision] 服务异常，请稍后重试", "code": 400})
