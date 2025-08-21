# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import logging

from qcloud_cos import CosConfig, CosS3Client, CosServiceError

from backend import env
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models.system import SystemSettings
from backend.flow.utils.doris.doris_act_payload import get_key_by_account_id

logger = logging.getLogger("root")


# 内网桶域名
INTERNAL_ENDPOINT_TMPL = env.COS_INTERNAL_ENDPOINT_TMPL
# 服务域名(列举所有桶时使用)
SERVICE_DOMAIN = env.COS_SERVICE_DOMAIN
# COS管控的账号ID
CONTROL_ACCOUNT_ID = env.HCM_COS_ACCOUNT_ID
# COS访问的账号ID
VISIT_ACCOUNT_ID = env.BIGDATA_CLOUD_ACCOUNT_ID


class CosSDK(object):
    def __init__(self, res_info: dict):
        self.res_info = res_info
        cloud_auth = get_key_by_account_id(account_id=CONTROL_ACCOUNT_ID)
        # 账号认证dict
        self.cloud_auth = cloud_auth
        # 使用内网域名接入
        endpoint = INTERNAL_ENDPOINT_TMPL.format(res_info["region"])
        service_domain = SERVICE_DOMAIN

        self.config = CosConfig(
            Region=res_info["region"],
            SecretId=cloud_auth["access_key"],
            SecretKey=cloud_auth["secret_key"],
            Token=None,
            Scheme="https",
            Endpoint=endpoint,
            ServiceDomain=service_domain,
        )
        self.client = CosS3Client(self.config)

    def create_bucket(self) -> bool:
        """
        调用COS SDK 创建存储桶
        """
        # 获取COS内置标签
        cos_tagging = SystemSettings.get_setting_value(key=SystemSettingsEnum.DORIS_COS_TAGGING, default={})
        # 构造标签列表，SDK要求格式是 List[{"Key": ..., "Value": ...}]
        tag_set = [{"Key": k, "Value": v} for k, v in cos_tagging.items()]
        # 由于腾讯云COS SDK不支持创建存储桶同时配置标签，流程中步骤并非事务，存在创建存储桶成功，配置标签失败退出的情况
        try:
            # 1. 创建存储桶
            self.client.create_bucket(Bucket=self.res_info["bucket_name"])
            # 2. 存储桶创建标签
            self.client.put_bucket_tagging(
                Bucket=self.res_info["bucket_name"],
                Tagging={
                    "TagSet": tag_set,
                },
            )
            return True
        except CosServiceError as e:
            # 捕获 COS 服务异常
            logger.error(f"create bucket failed: {e.get_error_msg()} (Code: {e.get_error_code()})")
            return False
        except Exception as e:
            # 捕获其他异常
            logger.error(f"create bucket unknown except: {e}")
            return False

    def put_policy(self) -> bool:
        """
        调用COS SDK创建存储桶权限策略
        """
        # 授权子账号对应的主账号，需要获取

        # 自定义权限策略, 将存储桶的读写权限授予使用者子账号ID
        custom_policy = {
            "Statement": [
                {
                    "Principal": {"qcs": ["qcs::cam::%s" % VISIT_ACCOUNT_ID]},
                    "Effect": "allow",
                    "Action": ["name/cos:*"],
                    "Resource": [
                        "qcs::cos:%s:uid/%s:%s/*"
                        % (self.res_info["region"], self.cloud_auth["appid"], self.res_info["bucket_name"])
                    ],
                }
            ],
            "version": "2.0",
        }
        try:
            self.client.put_bucket_policy(
                Bucket=self.res_info["bucket_name"],
                Policy=custom_policy,
            )
            return True
        except CosServiceError as e:
            # 捕获 COS 服务异常
            logger.error(f"create bucket policy failed: {e.get_error_msg()} (Code: {e.get_error_code()})")
            return False
        except Exception as e:
            # 捕获其他异常
            logger.error(f"create bucket policy unknown except: {e}")
            return False

    def exists_bucket(self) -> bool:
        """
        调用 COS SDK 检查存储桶名称是否已存在
        """
        return self.client.bucket_exists(Bucket=self.res_info["bucket_name"])

    def lsit_buckets(self):
        """
        调用COS SDK 获取桶列表
        """
        return self.client.list_buckets()

    # # 获取存储桶的策略
    # def get_policy(self) -> bool:
    #     response = self.client.get_bucket_policy(
    #         Bucket=self.res_info["bucket_name"],
    #     )
    #     policy = json.loads(response['Policy'])
    #     print(policy)
    #     return True

    def delete_bucket(self) -> bool:
        try:
            self.client.delete_bucket(Bucket=self.res_info["bucket_name"])
            return True
        except CosServiceError as e:
            # 捕获 COS 服务异常
            logger.error(f"delete bucket failed: {e.get_error_msg()} (Code: {e.get_error_code()})")
            return False
        except Exception as e:
            # 捕获其他异常
            logger.error(f"delete bucket unknown except: {e}")
            return False
