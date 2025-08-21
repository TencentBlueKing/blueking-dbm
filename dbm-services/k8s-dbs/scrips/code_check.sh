#!/bin/bash

set -euo pipefail  # 保证任何命令失败时脚本立即退出，并打印错误

echo "🔍 开始代码质量检查..."

# 1. 使用 go vet 进行静态分析
echo "🧪 运行 go vet..."
go vet ./k8s-dbs/...
if [ $? -ne 0 ]; then
    echo "❌ go vet 检查失败"
    exit 1
fi

# 2. 使用 goimports 格式化 import 语句并直接写入文件
echo "📦 运行 goimports..."
goimports -w ./k8s-dbs
if [ $? -ne 0 ]; then
    echo "❌ goimports 格式化失败"
    exit 1
fi

# 3. 使用 golangci-lint 运行更全面的 lint 检查
echo "🧹 运行 golangci-lint..."
golangci-lint run ./k8s-dbs/...
if [ $? -ne 0 ]; then
    echo "❌ golangci-lint 检查失败"
    exit 1
fi

echo "✅ 所有代码质量检查通过！"