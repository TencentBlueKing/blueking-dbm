# -*- coding: utf-8 -*-

from django.conf import settings as django_settings


def default_before_proxy_func(request):
    """预留钩子，可修改转发接口的header和body"""
    return request


# 统一转发前缀
PREFIX_BKVISION = getattr(django_settings, "PREFIX_BKVISION", "bkvision")

# AJAX接口转发前的
PRE_PROCESS_FUNC = getattr(django_settings, "PRE_PROCESS_FUNC", default_before_proxy_func)

# 设置被代理的bkvision接口地址，比如API网关的接口
DEFAULT_BKVISION_APIGW_URL = "https://bk-vision-apigw.example.com"
BKVISION_APIGW_URL = getattr(django_settings, "BKAPP_BKVISION_APIGW_URL", DEFAULT_BKVISION_APIGW_URL)
