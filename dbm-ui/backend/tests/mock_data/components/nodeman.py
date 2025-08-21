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

AGENT_DETAILS_DATA = {
    "agent_id": "",
    "ip": "xx.xx.xx.xx",
    "ipv6": "",
    "host_name": "VM",
    "os_name": "Linux",
    "os_type": "Linux",
    "alive": 1,
    "cloud_area": {"id": 0, "name": "xxx"},
    "biz": {"id": 2, "name": "xxx"},
    "bk_agent_id": "",
    "bk_agent_alive": 1,
    "bk_cloud_id": 0,
}

# 添加作业ID常量
JOB_ID = 6227236


class MockResponse:
    """模拟HTTP响应对象"""

    def __init__(self, status_code, response_data=None):
        self.status_code = status_code
        if response_data is None:
            if status_code == 200:
                # 成功状态下的模拟响应数据
                self.response_data = {
                    "code": 0,
                    "result": True,
                    "data": {"status": NodemanApiMock.JobStatusType.SUCCESS},
                }
            else:
                # 错误状态下的模拟响应
                self.response_data = {
                    "code": status_code,
                    "result": False,
                    "message": "Gateway Timeout" if status_code == 504 else "Error",
                }
        else:
            self.response_data = response_data
        self.text = str(self.response_data)
        self.reason = "Gateway Timeout" if status_code == 504 else ""

    def json(self):
        return self.response_data


class NodemanApiMock(object):
    """
    gse 的 mock 接口
    """

    # 模拟作业状态类型
    class JobStatusType:
        PENDING = 1
        RUNNING = 2
        SUCCESS = 3
        FAILED = 4
        PROCESSING_STATUS = [PENDING, RUNNING]

    @classmethod
    def ipchooser_host_details(cls, *args, **kwargs):
        params = args[0]
        host_details = [{"host_id": host["host_id"], **AGENT_DETAILS_DATA} for host in params["host_list"]]
        return host_details

    @classmethod
    def job_details(cls, *args, **kwargs):
        return {"code": 0, "result": True, "data": {"status": cls.JobStatusType.SUCCESS}}

    @classmethod
    def operate_plugin(cls, params=None, **kwargs):
        """模拟插件安装API，返回固定job_id"""
        return {"job_id": JOB_ID, "job_url": f"http://bknodeman.example.com/#/task-list/detail/{JOB_ID}"}

    @classmethod
    def _send(cls, params=None, headers=None):
        """模拟原始HTTP响应，用于测试重试逻辑"""
        return MockResponse(504)
