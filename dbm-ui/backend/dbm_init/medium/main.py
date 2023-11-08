# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-权限中心Python SDK(iam-python-sdk) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import argparse
import logging
import os

from handlers import MediumHandler

logger = logging.getLogger("root")

parser = argparse.ArgumentParser(description="This is a script for automatically synchronizing artifact libraries")
parser.add_argument(
    "--type",
    type=str,
    help="download: Download product library files;\n upload: Upload product library files\n sync: Sync library to DBM",
)
parser.add_argument("--db", type=str, help="Database type", default="")
args = parser.parse_args()

if __name__ == "__main__":
    """版本镜像脚本执行入口"""
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "medium")

    if args.type == "update_lock":
        MediumHandler.update_lock(bkrepo_tmp_dir=path)
    elif args.type == "build":
        MediumHandler.build_medium(bkrepo_tmp_dir=path)
    elif args.type == "upload":
        MediumHandler().upload_medium(path=args.db, bkrepo_tmp_dir=path)
    elif args.type == "sync":
        MediumHandler().sync_from_bkrepo(db_type=args.db)
    else:
        raise Exception("Unsupported operation type")
