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
import hashlib
import json
import logging
import os
import subprocess
import zipfile
from datetime import datetime

import yaml
from bkstorages.backends.bkrepo import TIMEOUT_THRESHOLD, BKGenericRepoClient, BKRepoStorage, urljoin


logger = logging.getLogger("root")


class MediumBKGenericRepoClient(BKGenericRepoClient):
    """代码同backend/core/storage一致"""

    def list_dir(self, key_prefix: str):
        """
        Lists the contents of the specified path, returning a 2-tuple of lists;
        the first item being directories, the second item being files.
        """
        cur_page = 0
        directories, files = [], []
        while True:
            cur_page += 1
            ds, fs, next_page = self.__list_dir(key_prefix, cur_page=cur_page)
            directories.extend(ds)
            files.extend(fs)
            if not next_page:
                break
        return directories, files

    def __list_dir(self, key_prefix: str, cur_page: int = 1):
        """
        返回更多文件信息
        """
        directories, files = [], []
        client = self.get_client()
        url = urljoin(self.endpoint_url, f"/repository/api/node/page/{self.project}/{self.bucket}/{key_prefix}")
        # NOTE: 按分页查询 bkrepo 的文件数, 1000 是一个经验值, 设置仅可能大的数值是避免发送太多次请求到 bk-repo
        params = {"pageSize": 1000, "PageNumber": cur_page, "includeFolder": True}
        resp = client.get(url, params=params, timeout=TIMEOUT_THRESHOLD)
        data = self._validate_resp(resp)
        total_pages = data["totalPages"]
        for record in data["records"]:
            if record["folder"]:
                directories.append(record)
            else:
                # 返回全部文件信息
                files.append(record)
        return directories, files, (cur_page < total_pages)


class MediumHandler:
    def __init__(self, storage=None):
        if storage:
            self.storage = storage
        else:
            self.storage = BKRepoStorage(
                username=os.getenv("BKREPO_USERNAME"),
                password=os.getenv("BKREPO_PASSWORD"),
                project_id=os.getenv("BKREPO_PROJECT"),
                bucket=os.getenv("BKREPO_PUBLIC_BUCKET"),
                endpoint_url=os.getenv("BKREPO_ENDPOINT_URL"),
                file_overwrite=os.getenv("FILE_OVERWRITE", True),
            )
            self.storage.client = MediumBKGenericRepoClient(
                bucket=os.getenv("BKREPO_PUBLIC_BUCKET"),
                project=os.getenv("BKREPO_PROJECT"),
                username=os.getenv("BKREPO_USERNAME"),
                password=os.getenv("BKREPO_PASSWORD"),
                endpoint_url=os.getenv("BKREPO_ENDPOINT_URL"),
            )

    def download_medium(self, option, path, bkrepo_tmp_dir):
        """从制品库下载文件到本地"""
        if not os.path.exists(bkrepo_tmp_dir):
            os.makedirs(bkrepo_tmp_dir)
        os.chdir(bkrepo_tmp_dir)

        if option in ["download", "all"]:
            if path:
                subprocess.call(["wget", self.storage.url(f"/{path}")])
            else:
                with open(os.path.join(bkrepo_tmp_dir, "wget.txt"), "w") as f:
                    for d in self.storage.listdir("/")[0]:
                        f.write(self.storage.url(d["fullPath"]) + "\n")
                subprocess.call(["wget", "-i", "./wget.txt"])

        if option in ["unzip", "all"]:
            for root, dirs, files in os.walk(bkrepo_tmp_dir):
                for file in files:
                    if "?" not in file:
                        continue

                    if path and path not in file:
                        continue

                    db_type = file.split("?")[0]
                    with zipfile.ZipFile(os.path.join(root, file)) as zfile:
                        logger.info("unzip dir: %s", file)
                        zfile.extractall(os.path.join(bkrepo_tmp_dir, db_type))

                    os.remove(os.path.join(root, file))

    def upload_medium(self, path, bkrepo_tmp_dir):
        """将本地文件上传到制品库"""
        if not os.path.exists(bkrepo_tmp_dir):
            os.makedirs(bkrepo_tmp_dir)
        os.chdir(bkrepo_tmp_dir)

        for root, dirs, files in os.walk(bkrepo_tmp_dir):
            for file in files:
                if "?" in file:
                    continue
                if os.getenv("RUN_VER") == "ieod" and "dbbackup-go" in file:
                    # 内部版本不自动上传 dbbackup
                    continue

                for suffix in [
                    "txt",
                    "py",
                    "sql",
                    "xlsx",
                    "secret",
                    "crt",
                    "key",
                    "png",
                    "ppx",
                    "doc",
                    "md",
                    "DS_Store",
                ]:
                    if f".{suffix}" in file:
                        break
                else:
                    if path and f"/{path}" not in root:
                        continue
                    # 分割路径，保留制品路径(db_type/name/version/file)
                    file_path = os.path.join(root, file)
                    file_path_bkrepo = file_path.split(file_path.rsplit("/", 4)[0])[1]
                    logger.info("upload file: %s -> %s", file_path, file_path_bkrepo)
                    with open(file_path, "rb") as f:
                        # 如果当前版本不存在，则更新介质
                        if not self.storage.listdir(file_path_bkrepo.rsplit("/", 1)[0])[1]:
                            self.storage.save(file_path_bkrepo, f)
                        # 如果文件md5不相等，则更新介质
                        bkrepo_file_md5 = self.storage.listdir(file_path_bkrepo.rsplit("/", 1)[0])[1][0]["md5"]
                        pkg_file_md5 = hashlib.md5(f.read()).hexdigest()
                        if bkrepo_file_md5 != pkg_file_md5:
                            self.storage.save(file_path_bkrepo, f)

    def sync_from_bkrepo(self, db_type):
        """将制品库文件同步到dbm"""
        from network import HttpHandler

        http = HttpHandler()
        for pkg_type in self.storage.listdir(f"/{db_type}")[0]:
            # 排除非介质文件
            if pkg_type["name"] in ["keyfiles", "db-remote-service", "sqlfile"]:
                continue

            for version in self.storage.listdir(pkg_type["fullPath"])[0]:
                for media in self.storage.listdir(version["fullPath"])[1]:
                    package_params = {
                        "name": media["name"],
                        "db_type": db_type,
                        "pkg_type": pkg_type["name"],
                        "version": version["name"],
                        "path": media["fullPath"],
                        "size": media["size"],
                        "md5": media["md5"],
                        "create_at": str(datetime.strptime(media["createdDate"], "%Y-%m-%dT%H:%M:%S.%f")),
                        "creator": "system",
                        "update_at": str(datetime.strptime(media["lastModifiedDate"], "%Y-%m-%dT%H:%M:%S.%f")),
                        "updater": "system",
                    }
                    logger.info("sync info %s", json.dumps(package_params, indent=4))
                    http.post(url="apis/packages/update_or_create/", data=package_params)

    @classmethod
    def update_lock(cls, bkrepo_tmp_dir):
        """更新.lock文件"""

        def add_version(version):
            # TODO: 这里版本号叠加规则是怎样？默认只是小版本+1
            x, y, z = version.split(".")
            z = int(z) + 1
            return f"{x}.{y}.{z}"

        if not os.path.exists(bkrepo_tmp_dir):
            os.makedirs(bkrepo_tmp_dir)

        # 加载lock文件，获取介质的版本信息
        medium_lock_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "medium.lock")
        with open(medium_lock_path, "r") as lock_file:
            lock_info = yaml.safe_load(lock_file)

        # 将构建好的介质复制到指定目录，并更新lock info
        for db_type, mediums in lock_info.items():
            for medium in mediums:
                for medium_type, medium_info in medium.items():
                    # 判断commit是否相等，不想等则进行版本号增加
                    dir_commit, commit_date = (
                        subprocess.run(
                            [f"git -C {medium_info['buildPath'].rsplit('/', 2)[0]} log -n 1 --pretty=format:%H,%ci ."],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                        )
                        .stdout.decode("utf-8")
                        .split(",")
                    )
                    if dir_commit != medium_info["commitId"]:
                        medium_info["version"] = add_version(medium_info["version"])
                        medium_info["commitId"] = dir_commit
                        medium_info["commitDate"] = datetime.strptime(commit_date, "%Y-%m-%d %H:%M:%S %z").strftime(
                            "%Y%m%d%H%M"
                        )

        # 更新lock文件
        with open(medium_lock_path, "w") as lock_file:
            lock_file.write(yaml.safe_dump(lock_info))

    @classmethod
    def build_medium(cls, bkrepo_tmp_dir):
        # 加载lock文件，获取介质的版本信息
        medium_lock_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "medium.lock")
        with open(medium_lock_path, "r") as lock_file:
            lock_info = yaml.safe_load(lock_file)

        for db_type, mediums in lock_info.items():
            for medium in mediums:
                for medium_type, medium_info in medium.items():
                    # 将编译好的介质复制到指定目录
                    target_medium_path = f"{bkrepo_tmp_dir}/{db_type}/{medium_type}/{medium_info['version']}"
                    result = subprocess.run(
                        [f"mkdir -p {target_medium_path} && cp {medium_info['buildPath']} {target_medium_path}"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True,
                    )
                    if result.returncode:
                        logger.error("Error: move medium fail! message: %s", result.stderr)
