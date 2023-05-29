#!/bin/bash

# 单元测试
source "${VENV_DIR}/bin/activate"
DBM_DIR="./dbm-ui"

cd $DBM_DIR
TEST_LOGS=$(pytest)
echo "${TEST_LOGS}"
# TEST_LOGS e.g.
# ====== 1 failed, 109 passed, 3 skipped, 580 warnings, 3 errors in 48.02s =======
TEST_RESULT=$(echo "${TEST_LOGS}" | grep "=======" | grep "in" | grep "\." | grep "s")
TEST_TIME=''
TEST_COUNT=0
TEST_SUCCESS=0
TEST_FAILURE=0
TEST_ERROR=0
TEST_NOT_SUCCESS_COUNT=0

echo $TEST_RESULT

TEST_TIME=$(echo $TEST_RESULT  | sed 's/.* \([0-9]*\.[0-9]*\)s.*/\1/g')
if [[ $TEST_RESULT =~ "failed" ]];
then
  TEST_FAILURE=$(echo $TEST_RESULT  | sed 's/.* \([0-9]*\).* failed.*/\1/g')
fi
if [[ $TEST_RESULT =~ "passed" ]];
then
  TEST_SUCCESS=$(echo $TEST_RESULT  | sed 's/.* \([0-9]*\).* passed.*/\1/g')
fi
if [[ $TEST_RESULT =~ "errors" ]];
then
  TEST_ERROR=$(echo $TEST_RESULT  | sed 's/.* \([0-9]*\).* errors.*/\1/g')
fi

TEST_COUNT=$[$TEST_SUCCESS+TEST_FAILURE+$TEST_ERROR]
TEST_NOT_SUCCESS_COUNT=$[TEST_NOT_SUCCESS_COUNT+TEST_FAILURE+TEST_ERROR]

echo "测试时长: $TEST_TIME"
echo "单元测试数: $TEST_COUNT"
echo "成功数: $TEST_SUCCESS"
echo "失败数: $TEST_FAILURE"
echo "报错数: $TEST_ERROR"
echo "未通过数: $TEST_NOT_SUCCESS_COUNT"


if [[ $TEST_NOT_SUCCESS_COUNT -ne 0 ]];
then
  exit 1
fi

# 打印报告
#coverage report --include "$COVERAGE_INCLUDE_PATH" --omit "$COVERAGE_OMIT_PATH"

exit 0
