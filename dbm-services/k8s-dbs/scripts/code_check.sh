#!/bin/bash

set -euo pipefail  # 保证任何命令失败时脚本立即退出，并打印错误

# 切换到 k8s-dbs 根目录（脚本所在目录的上一级），保证在任何地方执行都一致。
# k8s-dbs 目录下有自己的 go.work（仅挂载本模块及必要的兄弟模块），
# Go 工具会向上查找并优先命中它，从而不再使用外层 dbm-services/go.work。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

echo "🔍 开始代码质量检查... (PWD=$(pwd))"

# 1. 使用 go vet 进行静态分析
echo "🧪 运行 go vet..."
go vet ./...
if [ $? -ne 0 ]; then
    echo "❌ go vet 检查失败"
    exit 1
fi

# 2. 使用 goimports 格式化 import 语句并直接写入文件
echo "📦 运行 goimports..."
goimports -w .
if [ $? -ne 0 ]; then
    echo "❌ goimports 格式化失败"
    exit 1
fi

# 3. 使用 golangci-lint 运行更全面的 lint 检查
echo "🧹 运行 golangci-lint..."
golangci-lint run ./...
if [ $? -ne 0 ]; then
    echo "❌ golangci-lint 检查失败"
    exit 1
fi

echo "✅ 所有代码质量检查通过！"