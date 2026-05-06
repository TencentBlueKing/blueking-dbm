#!/bin/bash

# 获取脚本所在目录，确保无论从哪里调用都能找到子脚本
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FAILED_SCRIPTS=()

echo "=========================================="
echo "开始运行所有单元测试"
echo "=========================================="

for SCRIPT in metadata_controller.sh metadata_dbaccess.sh metadata_provider.sh; do
    echo ""
    echo ">>> 运行 ${SCRIPT} ..."
    echo "------------------------------------------"
    bash "${SCRIPT_DIR}/${SCRIPT}"
    EXIT_CODE=$?
    if [ ${EXIT_CODE} -ne 0 ]; then
        FAILED_SCRIPTS+=("${SCRIPT}")
    fi
    echo "------------------------------------------"
done

echo ""
echo "=========================================="
if [ ${#FAILED_SCRIPTS[@]} -eq 0 ]; then
    echo "✅ 所有测试脚本运行成功"
else
    echo "❌ 以下测试脚本存在失败："
    for SCRIPT in "${FAILED_SCRIPTS[@]}"; do
        echo "   - ${SCRIPT}"
    done
    exit 1
fi
echo "=========================================="