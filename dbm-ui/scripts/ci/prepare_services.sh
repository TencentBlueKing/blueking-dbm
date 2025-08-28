#!/bin/bash

if [ "$CREATE_PYTHON_VENV" ]; then
  # 创建虚拟环境
  pip install virtualenv pytest pytest-cov
  VENV_DIR="/tmp/ci_py_venv"
  virtualenv "$VENV_DIR"
  virtualenv -p /usr/bin/python3.10 "$VENV_DIR"
  # 激活Python虚拟环境
  source "${VENV_DIR}/bin/activate"
fi

# 更新pip
pip install --upgrade pip

# 检查Python版本
python -V

# 检查
pip list
