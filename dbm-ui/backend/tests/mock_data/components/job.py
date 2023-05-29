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

JOB_INSTANCE_ID = 10000
STEP_INSTANCE_ID = 10001
JOB_SUCCESS_STATUS = 3


class JobApiMock(object):
    """job平台相关接口的mock类"""

    base_info = {"result": True, "code": 0, "message": "success"}

    @classmethod
    def fast_transfer_file(cls, payload, raw=True):
        data = {
            "job_instance_name": f"API Quick Distribution{payload['bk_biz_id']}",
            "job_instance_id": JOB_INSTANCE_ID,
            "step_instance_id": STEP_INSTANCE_ID,
        }
        return {**cls.base_info, "data": data}

    @classmethod
    def get_job_instance_status(cls, payload, raw=True):
        data = {
            "finished": True,
            "job_instance": {
                "job_instance_id": JOB_INSTANCE_ID,
                "bk_biz_id": payload["bk_biz_id"],
                "name": f"API Quick Distribution{payload['bk_biz_id']}",
                "status": JOB_SUCCESS_STATUS,
            },
            "step_instance_list": [
                {
                    "status": JOB_SUCCESS_STATUS,
                    "name": f"API Quick Distribution{payload['bk_biz_id']}",
                    "step_instance_id": STEP_INSTANCE_ID,
                }
            ],
        }
        return {**cls.base_info, "data": data}

    @classmethod
    def fast_execute_script(cls, payload, raw=True):
        data = {
            "job_instance_name": f"API Quick execution script{payload['bk_biz_id']}",
            "job_instance_id": JOB_INSTANCE_ID,
            "step_instance_id": STEP_INSTANCE_ID,
        }
        return {**cls.base_info, "data": data}
