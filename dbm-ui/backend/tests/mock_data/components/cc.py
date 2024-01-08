# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy

from backend.tests.mock_data import constant

MOCK_SEARCH_BUSINESS_RETURN = {"info": [{"bk_biz_id": constant.BK_BIZ_ID, "bk_biz_name": "蓝鲸"}], "count": 1}
MOCK_SEARCH_SET_RETURN = {"info": [{"bk_set_id": constant.BK_SET_ID, "bk_set_name": "mock集群"}], "count": 1}
MOCK_SEARCH_MODULE_RETURN = {"info": [{"bk_module_id": constant.DB_MODULE_ID, "bk_biz_name": "mock模块"}], "count": 1}
MOCK_LIST_SERVICE_INSTANCE_DETAIL_RETURN = {"info": []}
MOCK_SEARCH_OBJECT_ATTRIBUTE_RETURN = []

MOCK_SEARCH_BUSINESS_WITH_MULTI_BIZ_RETURN = {
    "info": [
        {"bk_biz_id": constant.BK_BIZ_ID, "bk_biz_name": "蓝鲸"},
        {"bk_biz_id": constant.BK_BIZ_ID + 1, "bk_biz_name": "DBA业务"},
    ],
    "count": 2,
}
MOCK_FIND_HOST_BIZ_RELATIONS_RETURN = [
    {"bk_host_id": 1, "bk_biz_id": constant.BK_BIZ_ID, "bk_module_id": constant.BK_MODULE_ID}
]

MOCK_GET_BIZ_INTERNAL_MODULE_RETURN = {
    "bk_set_id": constant.BK_SET_ID,
    "bk_set_name": "空闲机池",
    "module": [
        {"default": 1, "bk_module_id": constant.BK_MODULE_ID},
        {"default": 2, "bk_module_id": constant.BK_MODULE_ID2},
    ],
}

NORMAL_IP = "127.0.0.1"
NORMAL_IP2 = "127.0.0.2"
NORMAL_IP3 = "127.0.0.3"
NORMAL_IP4 = "127.0.0.4"
IP_WITH_NOT_REGISTERED_CITY = "127.0.0.5"
IP_NOT_IN_BKCC = "127.0.0.6"

REGISTERED_CITY_ID = 28
REGISTERED_CITY_NAME = "city"
NOT_REGISTERED_CITY_ID = "9999"

MOCK_LIST_HOSTS_WITHOU_BIZ_RETURN = {
    "count": 3,
    "info": [
        {
            "bk_host_innerip": NORMAL_IP,
            "bk_idc_area": "华东",
            "bk_idc_area_id": 5,
            "bk_os_name": "Tencent linux release 1.2 (Final)",
            "bk_svr_device_cls_name": "D2-4-50-10",
            "idc_city_id": REGISTERED_CITY_ID,
            "idc_city_name": "上海",
            "idc_id": 826,
            "idc_name": "上海腾讯宝信DC",
            "rack": "2F-S16",
            "rack_id": "104599",
            "sub_zone": "上海-宝信",
            "sub_zone_id": "154",
            "bk_cloud_id": 1,
            "bk_host_id": 1,
        },
        {
            "bk_host_innerip": NORMAL_IP2,
            "bk_idc_area": "华东",
            "bk_idc_area_id": 5,
            "bk_os_name": "Tencent linux release 1.2 (Final)",
            "bk_svr_device_cls_name": "D2-4-50-10",
            "idc_city_id": REGISTERED_CITY_ID,
            "idc_city_name": "上海",
            "idc_id": 826,
            "idc_name": "上海腾讯宝信DC",
            "rack": "2F-S16",
            "rack_id": "104599",
            "sub_zone": "上海-宝信",
            "sub_zone_id": "154",
            "bk_cloud_id": 1,
            "bk_host_id": 2,
        },
        {
            "bk_host_innerip": NORMAL_IP3,
            "bk_idc_area": "华东",
            "bk_idc_area_id": 5,
            "bk_os_name": "Tencent linux release 1.2 (Final)",
            "bk_svr_device_cls_name": "D2-4-50-10",
            "idc_city_id": REGISTERED_CITY_ID,
            "idc_city_name": "上海",
            "idc_id": 826,
            "idc_name": "上海腾讯宝信DC",
            "rack": "2F-S16",
            "rack_id": "104599",
            "sub_zone": "上海-宝信",
            "sub_zone_id": "154",
            "bk_cloud_id": 1,
            "bk_host_id": 3,
        },
        {
            "bk_host_innerip": NORMAL_IP4,
            "bk_idc_area": "华东",
            "bk_idc_area_id": 5,
            "bk_os_name": "Tencent linux release 1.2 (Final)",
            "bk_svr_device_cls_name": "D2-4-50-10",
            "idc_city_id": REGISTERED_CITY_ID,
            "idc_city_name": "上海",
            "idc_id": 826,
            "idc_name": "上海腾讯宝信DC",
            "rack": "2F-S16",
            "rack_id": "104599",
            "sub_zone": "上海-宝信",
            "sub_zone_id": "154",
            "bk_cloud_id": 1,
            "bk_host_id": 4,
        },
        {
            "bk_host_innerip": IP_WITH_NOT_REGISTERED_CITY,
            "bk_idc_area": "华东",
            "bk_idc_area_id": 5,
            "bk_os_name": "Tencent linux release 1.2 (Final)",
            "bk_svr_device_cls_name": "D2-4-50-10",
            # 未录入DBM系统的 City ID
            "idc_city_id": NOT_REGISTERED_CITY_ID,
            "idc_city_name": "上海",
            "idc_id": 826,
            "idc_name": "上海腾讯宝信DC",
            "rack": "2F-S16",
            "rack_id": "104599",
            "sub_zone": "上海-宝信",
            "sub_zone_id": "154",
            "bk_cloud_id": 1,
            "bk_host_id": 5,
        },
    ],
}

MOCK_CLOUD_AREA = [
    {"bk_cloud_name": "cloud-0", "bk_cloud_id": 0},
    {"bk_cloud_name": "cloud-1", "bk_cloud_id": 1},
]


class CCApiMock(object):
    """
    cc的mock接口
    """

    search_business_return = copy.deepcopy(MOCK_SEARCH_BUSINESS_RETURN)
    list_hosts_without_biz_return = copy.deepcopy(MOCK_LIST_HOSTS_WITHOU_BIZ_RETURN)
    search_set_return = copy.deepcopy(MOCK_SEARCH_SET_RETURN)
    search_module_return = copy.deepcopy(MOCK_SEARCH_MODULE_RETURN)
    find_host_biz_relations_return = copy.deepcopy(MOCK_FIND_HOST_BIZ_RELATIONS_RETURN)
    get_biz_internal_module_return = copy.deepcopy(MOCK_GET_BIZ_INTERNAL_MODULE_RETURN)
    list_service_instance_detail_return = copy.deepcopy(MOCK_LIST_SERVICE_INSTANCE_DETAIL_RETURN)
    search_object_attribute_return = copy.deepcopy(MOCK_SEARCH_OBJECT_ATTRIBUTE_RETURN)

    def __init__(
        self,
        search_business_return=None,
        list_hosts_without_biz_return=None,
        search_set_return=None,
        search_module_return=None,
        find_host_biz_relations_return=None,
        list_service_instance_detail_return=None,
        search_object_attribute_return=None,
    ):
        # 提供接口默认返回值，可根据不同的需求进行构造
        self.search_business_return = search_business_return or self.search_business_return
        self.list_hosts_without_biz_return = list_hosts_without_biz_return or self.list_hosts_without_biz_return
        self.search_set_return = search_set_return or self.search_set_return
        self.search_module_return = search_module_return or self.search_module_return
        self.find_host_biz_relations_return = find_host_biz_relations_return or self.find_host_biz_relations_return
        self.list_service_instance_detail_return = (
            list_service_instance_detail_return or self.list_service_instance_detail_return
        )
        self.search_object_attribute_return = search_object_attribute_return or self.search_object_attribute_return

    def search_business(self, *args, **kwargs):
        return self.search_business_return

    def search_set(self, *args, **kwargs):
        return self.search_set_return

    def search_module(self, *args, **kwargs):
        return self.search_module_return

    def find_host_biz_relations(self, *args, **kwargs):
        return self.find_host_biz_relations_return

    def list_service_instance_detail(self, *args, **kwargs):
        return self.list_service_instance_detail_return

    def search_cloud_area(self, *args, **kwargs):
        return {"result": True, "count": len(MOCK_CLOUD_AREA), "info": MOCK_CLOUD_AREA}

    def list_hosts_without_biz(self, *args, **kwargs):
        return self.list_hosts_without_biz_return

    def list_biz_hosts(self, *args, **kwargs):
        return self.list_hosts_without_biz_return

    def search_object_attribute(self, *args, **kwargs):
        return self.search_object_attribute_return

    @staticmethod
    def batch_update_host(*args, **kwargs):
        if kwargs.get("raw"):
            return {"result": True}
        return

    @staticmethod
    def create_set(*args, **kwargs):
        # 根据集群名生成集群ID
        param = kwargs.get("params") or args[0]
        bk_set_name = param["data"]["bk_set_name"]
        return {"bk_set_id": abs(bk_set_name.__hash__()) % 2147483647}

    @staticmethod
    def create_module(*args, **kwargs):
        # 根据模块名生成集群ID
        param = kwargs.get("params") or args[0]
        bk_module_name = param["data"]["bk_module_name"]
        return {"bk_module_id": abs(bk_module_name.__hash__() % 2147483647)}

    @staticmethod
    def transfer_host_module(*args, **kwargs):
        return {}

    @staticmethod
    def create_biz_custom_field(*args, **kwargs):
        return {}

    @staticmethod
    def add_label_for_service_instance(*args, **kwargs):
        return {}

    @staticmethod
    def create_service_instance(*args, **kwargs):
        return [1000000000]

    @staticmethod
    def get_biz_internal_module(*args, **kwargs):
        return MOCK_GET_BIZ_INTERNAL_MODULE_RETURN

    @staticmethod
    def transfer_host_across_biz(*args, **kwargs):
        if kwargs.get("raw"):
            return {"result": True}
        return

    @staticmethod
    def transfer_host_to_idlemodule(*args, **kwargs):
        if kwargs.get("raw"):
            return {"result": True}
        return
