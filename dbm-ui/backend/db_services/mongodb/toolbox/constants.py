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

# MongoDB脚本文件在制品库中的存储路径
MONGODB_SCRIPT_PATH = "mongodb/scriptfile/{biz}"

# 最大上传脚本文件大小（单位：字节）
MAX_UPLOAD_SCRIPT_FILE_SIZE = 1024 * 1024 * 1024  # 1GB

# 脚本文件支持的扩展名列表
SCRIPT_FILE_EXTENSIONS = [".js", ".txt"]
