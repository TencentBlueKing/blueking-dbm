#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""列出 backend 目录下自有、且需要参与 migrations 检查的 Django app label。

`makemigrations --check` 不传 app label 时会扫描 INSTALLED_APPS 里的所有 app，
包含安装在 site-packages 下的蓝鲸 SDK app（如 aidev_bkplugin、bk_notice_sdk 等）。
这些 SDK 的模型和 migrations 由 SDK 自身维护，SDK 没有生成 migrations 属于它自己的
问题，不应阻断本仓库的流水线。因此这里只输出：

1. app 代码位于 dbm-ui/backend/ 目录下（排除 site-packages 里的第三方依赖，
   也排除仓库内其它目录如 blueking/ 下的 app）；
2. 该 app 已有 migrations 模块（没有 migrations 的 app 属于 unmigrated app，
   表由 run_syncdb 创建，本来也不在 migrations 检查范围内）。

输出：每行一个 app label，供 `python manage.py makemigrations <labels>` 使用。
"""

import importlib
import os
import sys
from pathlib import Path

# 脚本位于 <仓库>/dbm-ui/scripts/ci/ 下，parents[2] 即 dbm-ui 目录
DBM_DIR = Path(__file__).resolve().parents[2]
# migrations 检查只扫描 backend 目录下的自有代码
BACKEND_DIR = DBM_DIR / "backend"
sys.path.insert(0, str(DBM_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.prod")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db.migrations.loader import MigrationLoader  # noqa: E402


def app_root(app_config) -> Path:
    """app 的代码根目录，兜底处理 namespace package（AppConfig.path 可能抛异常）"""
    try:
        return Path(app_config.path).resolve()
    except Exception:
        module = importlib.import_module(app_config.name)
        return Path(module.__file__).resolve().parent


def is_project_app(app_config) -> bool:
    """app 代码是否位于 dbm-ui/backend/ 下（site-packages 里的 SDK app 一律排除）"""
    return app_root(app_config).is_relative_to(BACKEND_DIR)


def has_migrations(loader, app_label) -> bool:
    """app 是否已有 migrations 模块（尊重 MIGRATION_MODULES 配置）

    没有 migrations 的 app 属于 unmigrated app，表由 run_syncdb 创建；
    把它传给 makemigrations 会强制生成 initial 迁移，属于误报。
    """
    return app_label in loader.migrated_apps


def collect_app_labels():
    loader = MigrationLoader(None, ignore_no_migrations=True)
    return sorted(
        app_config.label
        for app_config in apps.get_app_configs()
        if is_project_app(app_config) and has_migrations(loader, app_config.label)
    )


def main() -> int:
    labels = collect_app_labels()
    if not labels:
        print("未找到任何 backend 目录下的 app，拒绝以空范围通过 migrations 检查", file=sys.stderr)
        return 1
    print("\n".join(labels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
