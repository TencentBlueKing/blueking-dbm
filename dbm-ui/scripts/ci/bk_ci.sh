#!/bin/bash
# 当前脚本目录
SCRIPT_DIR=$(dirname $(readlink -f "$0"))

cat << EOF
SCRIPT_DIR -> "$SCRIPT_DIR"
EOF

FAILED_COUNT=0

${SCRIPT_DIR}/prepare_services.sh
FAILED_COUNT=$[$FAILED_COUNT+$?]

${SCRIPT_DIR}/install.sh
FAILED_COUNT=$[$FAILED_COUNT+$?]

${SCRIPT_DIR}/code_quality.sh
FAILED_COUNT=$[$FAILED_COUNT+$?]

echo "命令执行失败数量：$FAILED_COUNT"
if [[ $FAILED_COUNT -ne 0 ]];
then
  echo "单元测试未通过!"
  exit 1
else
  echo "单元测试已通过"
fi
