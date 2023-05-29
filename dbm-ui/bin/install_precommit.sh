#!/bin/sh

git config --unset-all core.hooksPath

# 直接使用pip安装即可
pip install pre-commit

# 直接执行此命令，设置git hooks钩子脚本
pre-commit install

# 直接执行此命令，进行全文件检查
pre-commit run --all-files