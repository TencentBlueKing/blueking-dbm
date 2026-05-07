# -*- coding: utf-8 -*-

from django.urls import re_path as url

from .views import BkVisionViewSet

urlpatterns = [
    url(r'^api/v1/datasource/query/$', BkVisionViewSet.as_view({"post": "query_datasource"})),
    url(r'^api/v1/dataset/query/$', BkVisionViewSet.as_view({"post": "query_dataset"})),
    url(r'^api/v1/field/(?P<uid>\w+)/preview_data/$', BkVisionViewSet.as_view({"post": "preview_field_data"})),
    url(r'^api/v1/meta/query/$', BkVisionViewSet.as_view({"get": "query_meta"})),
    url(r'^api/v1/variable/query/$', BkVisionViewSet.as_view({"post": "query_variable"})),
    url(r'^api/v1/variable/test/$', BkVisionViewSet.as_view({"post": "test_variable"})),
    url(r'^api/v1/panel/$', BkVisionViewSet.as_view({"get": "get_panel"})),
    url(r'^api/v1/panel/get_child_panels/$', BkVisionViewSet.as_view({"get": "get_child_panels"})),
    url(r'^api/v1/share/get_app_share_list/$', BkVisionViewSet.as_view({"get": "get_app_share_list"})),
]
