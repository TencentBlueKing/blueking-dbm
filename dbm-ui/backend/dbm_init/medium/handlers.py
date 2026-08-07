# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-权限中心Python SDK(iam-python-sdk) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import hashlib
import json
import logging
import os
import shutil
import subprocess
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml
from bkstorages.backends.bkrepo import TIMEOUT_THRESHOLD, BKGenericRepoClient, BKRepoStorage, urljoin
from dateutil.parser import parse as time_parse

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

    def _fetch_existing_plugins(self):
        """获取已存在的监控插件列表"""
        from network import HttpHandler

        http = HttpHandler()

        list_url = "/apis/monitor/collect/plugin_list/"
        logger.info(f"正在获取监控插件列表: {list_url}")

        resp = http.get(list_url, data={}, timeout=30)
        if not resp.result:
            raise RuntimeError(f"获取监控插件列表接口返回失败: {resp.message}")

        # 解析响应，获取已有插件列表
        data = resp.data
        existing_plugins = set()

        # 兼容不同响应格式
        plugin_list = []
        if isinstance(data, dict):
            plugin_list = data.get("list", [])
        elif isinstance(data, list):
            plugin_list = data

        for plugin in plugin_list:
            if isinstance(plugin, dict):
                plugin_id = plugin.get("plugin_id") or plugin.get("id") or plugin.get("name")
                if plugin_id:
                    existing_plugins.add(str(plugin_id))
            elif isinstance(plugin, str):
                existing_plugins.add(plugin)

        logger.info(f"已存在的监控插件列表: {existing_plugins}")
        return existing_plugins

    def _collect_monitor_plugins(self):
        """收集所有需要扫描的监控插件"""
        medium_lock_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "medium.lock")

        if not os.path.exists(medium_lock_path):
            logger.error("medium.lock 文件不存在")
            return {}

        with open(medium_lock_path, "r") as lock_file:
            lock_info = yaml.safe_load(lock_file)

        if not lock_info:
            logger.error("medium.lock 文件内容为空")
            return {}

        logger.debug("=" * 80)
        logger.debug("[DEBUG] 读取到的 medium.lock 内容:")
        logger.debug(yaml.dump(lock_info, default_flow_style=False, allow_unicode=True))
        logger.debug("=" * 80)

        # 收集所有需要扫描的监控插件（exporter类型的安装包）
        monitor_plugins = {}
        for db_type, mediums in lock_info.items():
            if not mediums:
                continue
            for medium in mediums:
                if not isinstance(medium, dict):
                    continue
                for medium_type, medium_info in medium.items():
                    # 只处理exporter类型的监控插件
                    if medium_type != "exporter":
                        continue

                    # 验证必要字段
                    if "name" not in medium_info:
                        logger.warn(f"警告: {db_type}/{medium_type} 缺少 name 字段，跳过")
                        continue
                    if "version" not in medium_info:
                        logger.warn(f"警告: {db_type}/{medium_type}/{medium_info['name']} 缺少 version 字段，跳过")
                        continue

                    # plugin_name 代表插件解压后 project.yaml 中的 name（插件唯一标识）
                    # 约定：medium.lock 的 name 字段即制品文件名（如 dbm_mysqld_exporter.tgz），
                    # 去掉 .tgz 后缀即为 project.yaml 的 name，这也是监控平台导入后的唯一标识。
                    # 注意：不能误用 version 字段作为唯一标识，version 仅表示版本号，
                    # 否则会出现「用版本号去比对监控平台的 plugin_id」导致去重/匹配失效。
                    plugin_name = medium_info["name"].replace(".tgz", "")
                    if not plugin_name:
                        logger.warn(f"警告: {db_type}/{medium_type} 解析出的 plugin_name 为空，跳过")
                        continue

                    # 去重，同名插件只需处理一次
                    if plugin_name not in monitor_plugins:
                        monitor_plugins[plugin_name] = {
                            "db_type": db_type,
                            "plugin_name": plugin_name,
                            "file_name": medium_info["name"],
                            "version": medium_info["version"],
                            "bkrepo_path": f"/{db_type}/exporter/{medium_info['version']}/{medium_info['name']}",
                        }

        return monitor_plugins

    def _upload_monitor_plugin(self, plugin_name, plugin_info, clean_tmp=True):
        """上传单个监控插件

        :param clean_tmp: 是否清理临时目录。镜像构建阶段可置为 False，保留下载文件便于排查。
        """
        from network import HttpHandler

        http = HttpHandler()
        bkrepo_path = plugin_info["bkrepo_path"]

        logger.info(f"监控插件 {plugin_name} 不存在，准备从制品库下载并上传，路径: {bkrepo_path}")

        import tempfile

        # 镜像运行场景下临时目录由容器生命周期托管，默认仍清理；
        # 若 clean_tmp=False（如镜像构建期），保留文件以便排查。
        tmp_dir = tempfile.mkdtemp()
        tmp_file_path = os.path.join(tmp_dir, plugin_info["file_name"])

        try:
            # 阶段一：从制品库下载插件文件到临时目录
            plugin_file = self.storage.open(bkrepo_path)
            with open(tmp_file_path, "wb") as f:
                for chunk in plugin_file.chunks():
                    f.write(chunk)

            # 阶段二：调用监控平台导入插件接口（无前端交互版本）
            import_url = "/apis/monitor/collect/plugin_import/"
            logger.info(f"正在上传监控插件 {plugin_name} 到: {import_url}")
            with open(tmp_file_path, "rb") as f:
                # 构造 multipart/form-data 请求（不含 Content-Type，让 requests 自动设置 boundary）
                upload_files = {"file": (plugin_info["file_name"], f, "application/gzip")}  # ← 关键: 字段名 file
                # 显式声明 send_file=True，不依赖 files 参数名判定文件上传分支
                upload_result = http.post(import_url, data={}, files=upload_files, send_file=True, timeout=300)

            if upload_result.result:
                logger.info(f"监控插件 {plugin_name} 上传成功: {upload_result.data}")
                return True

            logger.error(f"监控插件 {plugin_name} 上传失败: {upload_result.data}")
            return False
        except Exception:  # 下载/上传过程中的任何异常已在 HttpHandler 或此处统一记录
            logger.exception(f"监控插件 {plugin_name} 下载或上传异常")
            return False

    def sync_monitor_plugin(self):
        """扫描监控插件，有就忽略，没有就上传"""
        logger.debug("=" * 80)
        logger.debug("[DEBUG] 开始执行 scan_monitor_plugin")
        logger.debug("=" * 80)

        # 收集所有需要扫描的监控插件
        try:
            monitor_plugins = self._collect_monitor_plugins()
        except Exception as e:
            logger.exception(f"收集监控插件信息异常: {str(e)}")
            return

        if not monitor_plugins:
            logger.info("未找到需要扫描的监控插件")
            return

        # 获取已存在的插件列表
        try:
            existing_plugins = self._fetch_existing_plugins()
        except Exception as e:
            logger.exception(f"获取监控插件列表异常: {str(e)}")
            return

        logger.debug(f"[DEBUG] 已存在的插件列表: {existing_plugins}")
        logger.debug(f"[DEBUG] 需要检查的插件列表: {list(monitor_plugins.keys())}")

        # 遍历所有监控插件，不存在则上传
        upload_count = 0
        skip_count = 0
        fail_count = 0

        for plugin_name, plugin_info in monitor_plugins.items():
            if plugin_name in existing_plugins:
                logger.info(f"监控插件 {plugin_name} 已存在，跳过")
                skip_count += 1
                continue

            if self._upload_monitor_plugin(plugin_name, plugin_info):
                upload_count += 1
            else:
                fail_count += 1

        logger.info(f"监控插件扫描完成: 总计 {len(monitor_plugins)}, 跳过 {skip_count}, 上传成功 {upload_count}, 上传失败 {fail_count}")
        if upload_count > 0:
            # 加载采集策略
            self.sync_collect_strategy()
            logger.info("加载采集策略成功")

    def sync_collect_strategy(self):
        """加载采集策略（调用后端接口同步监控采集项到蓝鲸监控）"""
        from network import HttpHandler

        http = HttpHandler()
        try:
            res = http.post(url="/apis/monitor/collect/sync/strategy/", data={}, timeout=600)
            logger.info(f"[sync_collect_strategy] 加载采集策略成功: {res.result}")
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"[sync_collect_strategy] 加载采集策略失败: {e}")

    @staticmethod
    def __load_medium_lock():
        medium_lock_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "medium.lock")
        with open(medium_lock_path, "r") as lock_file:
            lock_info = yaml.safe_load(lock_file)
        return lock_info

    @staticmethod
    def __format_full_version(version):
        # TODO: medium lock的version必须是点六分式
        split_ver = version.split(".")
        if len(split_ver) == 3:
            return f"{version}.0.0.0"
        elif len(split_ver) == 6:
            return version
        else:
            return "1.0.0.0.0.0"

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
                        print("unzip dir: %s", file)
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
                if os.getenv("RUN_VER") == "ieod" and "dbbackup-go-txsql" in file:
                    # 内部版本不自动上传 dbbackup
                    continue

                for suffix in [
                    "txt",
                    "SQL",
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
                    # Django>=4.2 的 Storage.save 会拒绝绝对路径(path traversal 校验)，这里去掉前导斜杠传相对路径
                    save_path_bkrepo = file_path_bkrepo.lstrip("/")
                    print("upload file: %s -> %s", file_path, file_path_bkrepo)
                    with open(file_path, "rb") as f:
                        # 如果当前版本不存在，则更新介质
                        if not self.storage.listdir(file_path_bkrepo.rsplit("/", 1)[0])[1]:
                            self.storage.save(save_path_bkrepo, f)
                        # 如果文件md5不相等，则更新介质
                        bkrepo_file_md5 = self.storage.listdir(file_path_bkrepo.rsplit("/", 1)[0])[1][0]["md5"]
                        pkg_file_md5 = hashlib.md5(f.read()).hexdigest()
                        if bkrepo_file_md5 != pkg_file_md5:
                            f.seek(0)
                            self.storage.save(save_path_bkrepo, f)

    def sync_from_bkrepo(self, db_type):
        """将制品库文件同步到dbm"""

        # 映射版本信息字典
        lock_info = self.__load_medium_lock()
        package_map = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
        for medium in lock_info[db_type]:
            for medium_type, info in medium.items():
                package_map[db_type][medium_type][info["version"]][info["name"]] = info

        from network import HttpHandler

        http = HttpHandler()
        package_sync_params = []
        for pkg_type in self.storage.listdir(f"/{db_type}")[0]:
            # 排除非介质文件
            if pkg_type["name"] in ["keyfiles", "db-remote-service", "sqlfile"]:
                continue

            for version in self.storage.listdir(pkg_type["fullPath"])[0]:
                for media in self.storage.listdir(version["fullPath"])[1]:
                    package_info = package_map[db_type][pkg_type["name"]][version["name"]][media["name"]]
                    # 如果不属于medium.lock维护，则不同步到package
                    if not package_info:
                        continue
                    # 介质基础信息
                    package_params = {
                        "name": media["name"],
                        "db_type": db_type,
                        "pkg_type": pkg_type["name"],
                        "version": version["name"],
                        "path": media["fullPath"],
                        "size": media["size"],
                        "md5": media["md5"],
                        "permit_os_type": package_info.get("os_type", ""),
                        "permit_os": package_info.get("os_version", []),
                        "create_at": time_parse(media["createdDate"]).isoformat(),
                        "creator": "system",
                        "update_at": time_parse(media["lastModifiedDate"]).isoformat(),
                        "updater": "system",
                    }
                    # 介质版本信息
                    full_version = self.__format_full_version(package_info.get("full_version", version["name"]))
                    package_version_params = {
                        "distribution_name": package_info.get("distribution_name", "DBM"),
                        "distribution_engine": package_info.get("distribution_engine", ""),
                        "version_series": package_info.get("version_series", version["name"]),
                        "phase": package_info.get("phase", "release"),
                        "description": package_info.get("description", "auto sync medium"),
                        "full_version": full_version,
                        "version_name": package_info.get("version_name", full_version),
                    }

                    package_params.update(package_version_params)
                    package_sync_params.append(package_params)
                    print("sync info %s", json.dumps(package_params, indent=4))

        data = {"db_type": db_type, "sync_medium_infos": package_sync_params}
        http.post(url="/apis/packages/sync_medium/", data=data)

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
        lock_info = cls.__load_medium_lock()

        # 将构建好的介质复制到指定目录，并更新lock info
        for db_type, mediums in lock_info.items():
            for medium in mediums:
                for medium_type, medium_info in medium.items():
                    # 静态介质文件无需编译，没有版本和commit信息
                    if "commitId" not in medium_info:
                        continue
                    # 判断commit是否相等，不想等则进行版本号增加
                    print("update lock: ", medium_info["buildPath"])
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
                        commit_data = datetime.strptime(commit_date, "%Y-%m-%d %H:%M:%S %z").strftime("%Y%m%d%H%M")
                        medium_info["version"] = add_version(medium_info["version"])
                        medium_info["commitId"] = dir_commit
                        medium_info["commitDate"] = commit_data

        # 更新lock文件
        with open(medium_lock_path, "w") as lock_file:
            lock_file.write(yaml.safe_dump(lock_info))

    @classmethod
    def build_medium(cls, bkrepo_tmp_dir, installation=False):
        # 加载lock文件，获取介质的版本信息
        lock_info = cls.__load_medium_lock()
        for db_type, mediums in lock_info.items():
            for medium in mediums:
                for medium_type, medium_info in medium.items():
                    # 如果介质和安装模式不匹配，忽略
                    if medium_info.get("installation", False) != installation:
                        continue
                    # 将编译好的介质复制到指定目录（使用 pathlib+shutil 替代 shell 命令，避免命令注入风险）
                    target_path = Path(bkrepo_tmp_dir) / db_type / medium_type / medium_info["version"]
                    target_path.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(medium_info["buildPath"], target_path)
                    except OSError as e:
                        print("Error: move medium fail! message: %s", str(e))
