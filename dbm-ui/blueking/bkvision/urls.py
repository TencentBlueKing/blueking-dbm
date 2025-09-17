# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = (
    url(r'^api/v1/datasource/query/$', views.query_datasource),
    url(r'^api/v1/dataset/query/$', views.query_dataset),
    url(r'^api/v1/field/(?P<uid>\w+)/preview_data/$', views.preview_field_data),
    url(r'^api/v1/meta/query/$', views.query_meta),
    url(r'^api/v1/variable/query/$', views.query_variable),
    url(r'^api/v1/variable/test/$', views.test_variable),
    url(r'^api/v1/panel/$', views.get_panel),
    url(r'^api/v1/panel/get_child_panels/$', views.get_child_panels),
    url(r'^api/v1/share/get_app_share_list/$', views.get_app_share_list),
)
