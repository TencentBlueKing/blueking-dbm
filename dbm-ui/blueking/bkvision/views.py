# -*- coding:utf-8 -*-
import json

import requests
from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from blueking.bkvision.settings import PRE_PROCESS_FUNC, BKVISION_APIGW_URL
from blueking.bkvision.utils import normalize_request_headers


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


@login_exempt
@csrf_exempt
@require_http_methods(["POST"])
def query_variable(request):
    """获取变量数据"""

    try:
        return proxy_request(request, '/api/v1/variable/query/')
    except Exception as e:
        return JsonResponse({"result": False, "message": "query_variable exception: {}".format(e), "code": 400})


@login_exempt
@csrf_exempt
@require_http_methods(["POST"])
def test_variable(request):
    """测试变量数据"""

    try:
        return proxy_request(request, '/api/v1/variable/test/')
    except Exception as e:
        return JsonResponse({"result": False, "message": "query_variable exception: {}".format(e), "code": 400})


@login_exempt
@csrf_exempt
@require_http_methods(["POST"])
def preview_field_data(request, uid):
    """获取字段数据"""

    try:
        return proxy_request(request, f'/api/v1/field/{uid}/preview_data/')
    except Exception as e:
        return JsonResponse({"result": False, "message": "query_variable exception: {}".format(e), "code": 400})


@login_exempt
@csrf_exempt
@require_http_methods(["POST"])
def query_datasource(request):
    """查询数据源数据"""

    try:
        # 转发前的预处理hook
        request = PRE_PROCESS_FUNC(request)
        return proxy_request(request, '/api/v1/datasource/query/')
    except Exception as e:
        return JsonResponse({"result": False, "message": "query_datasource exception: {}".format(e), "code": 400})


@login_exempt
@csrf_exempt
@require_http_methods(["POST"])
def query_dataset(request):
    """查询数据集数据"""

    try:
        # 转发前的预处理hook
        request = PRE_PROCESS_FUNC(request)
        return proxy_request(request, '/api/v1/dataset/query/')
    except Exception as e:
        return JsonResponse({"result": False, "message": "query_dataset exception: {}".format(e), "code": 400})


@login_exempt
@require_http_methods(["GET"])
def query_meta(request):
    """
    获取配置
        curl -X GET -H 'content-type: application/json' \
            'http://127.0.0.1:8001/bkvision/api/v1/meta/query/?share_uid=FwchfLZSsoaBSzjpW7WBa7'
    """
    try:
        return proxy_request(request, '/api/v1/meta/query/')
    except Exception as e:
        return JsonResponse({"result": False, "message": "query_meta exception: {}".format(e), "code": 400})


@login_exempt
@csrf_exempt
@require_http_methods(["GET"])
def get_panel(request):
    """获取图表配置"""

    try:
        return proxy_request(request, '/api/v1/panel/')
    except Exception as e:
        return JsonResponse({"result": False, "message": "get_panel exception: {}".format(e), "code": 400})


@login_exempt
@csrf_exempt
@require_http_methods(["GET"])
def get_child_panels(request):
    """获取子图列表"""

    try:
        return proxy_request(request, '/api/v1/panel/get_child_panels/')
    except Exception as e:
        return JsonResponse({"result": False, "message": "get_child_panels exception: {}".format(e), "code": 400})


@login_exempt
@csrf_exempt
@require_http_methods(["GET"])
def get_app_share_list(request):
    """获取应用有权限的嵌入列表"""

    try:
        response = proxy_request(request, '/api/v1/share/get_app_share_list/')
        datas = json.loads(response.content)["data"]
        data = next((data["share"] for data in datas if data["name"] == "DBM内部环境"), [])
        return JsonResponse({"result": True, "message": "", "data": data, "code": 200})
    except Exception as e:
        return JsonResponse({"result": False, "message": "get_app_share_list exception: {}".format(e), "code": 400})
