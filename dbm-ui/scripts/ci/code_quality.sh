#!/bin/bash

# 单元测试
source "${VENV_DIR}/bin/activate"
DBM_DIR="./dbm-ui"

cd $DBM_DIR
TEST_LOGS=$(pytest --cov)

# TEST_LOGS e.g.
# ============================= test session starts ==============================
# platform linux -- Python 3.6.15, pytest-6.2.4, py-1.11.0, pluggy-0.13.1
# django: settings: config.prod (from env)
# rootdir: /home/runner/work/blueking-dbm/blueking-dbm/dbm-ui, configfile: pytest.ini, testpaths: ./backend
# plugins: cov-2.10.1, celery-4.4.0, django-3.9.0
# collected 103 items
#
# backend/tests/db_meta/api/cluster/tendbha/test_handler.py .              [  0%]
# backend/tests/db_meta/api/db_module/test_apis.py ..                      [  80%]
# TOTAL 66348  39795    40%
# ====== 1 failed, 109 passed, 3 skipped, 580 warnings, 3 errors in 48.02s =======
TEST_RESULT=$(echo "$TEST_LOGS" | tail -n 1)
echo $TEST_RESULT

TEST_TIME=$(echo $TEST_RESULT  | sed 's/.* \([0-9]*\.[0-9]*\)s.*/\1/g')
TEST_FAILURE=$(echo $TEST_RESULT  | sed 's/.* \([0-9]*\).* failed.*/\1/g')
TEST_SUCCESS=$(echo $TEST_RESULT  | sed 's/.* \([0-9]*\).* passed.*/\1/g')
TEST_SKIP=$(echo $TEST_RESULT  | sed 's/.* \([0-9]*\).* skipped.*/\1/g')

TEST_COUNT=$[$TEST_SUCCESS+$TEST_FAILURE+$TEST_SKIP]
TEST_NOT_SUCCESS_COUNT=$TEST_FAILURE

echo "测试时长: $TEST_TIME 秒"
echo "单元测试数: $TEST_COUNT"
echo "成功数: $TEST_SUCCESS"
echo "失败数: $TEST_FAILURE"
echo "跳过数: $TEST_SKIP"
echo "未通过数: $TEST_NOT_SUCCESS_COUNT"


if [[ $TEST_NOT_SUCCESS_COUNT -ne 0 ]];
then
  echo -e "\033[1;31m $TEST_LOGS  \033[0m"
  exit 1
fi

# 打印报告
#coverage report --include "$COVERAGE_INCLUDE_PATH" --omit "$COVERAGE_OMIT_PATH"

exit 0
