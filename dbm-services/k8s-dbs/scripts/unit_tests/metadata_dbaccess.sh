#!/bin/bash
set -euo pipefail

# 自动定位 k8s-dbs 模块根目录（脚本位于 k8s-dbs/scripts/unit_tests/ 下）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# DbAccess 测试函数列表，新增/删除用例在此维护
DBACCESS_TESTS=(
    TestComponentDbAccess
    TestAddonCategoryDbAccess
    TestAddonHelmRepoDbAccess
    TestAddonDbAccess
    TestAddonTopologyDbAccess
    TestAddonTypeDbAccess
    TestAddonClusterHelmRepoDbAccess
    TestAddonClusterReleaseDbAccess
    TestAddonClusterVersionDbAccess
    TestClusterOperationDbAccess
    TestOperationDefinitionDbAccess
    TestClusterDbAccess
    TestK8sClusterConfigDbAccess
    TestClusterRequestDbAccess
    TestClusterServiceDbAccess
    TestClusterTagDbAccess
    TestComponentOperationDbAccess
    TestK8sClusterAddonsDbAccess
    TestOpsRequestDbAccess
    TestAuthUserRoleDbAccess
)

echo "=========================================="
echo "  Running metadata dbaccess unit tests"
echo "  Module root: ${MODULE_ROOT}"
echo "=========================================="

cd "${MODULE_ROOT}"

# 支持传参指定单个测试函数，否则循环执行全部
if [ $# -gt 0 ]; then
    TESTS_TO_RUN=("$1")
else
    TESTS_TO_RUN=("${DBACCESS_TESTS[@]}")
fi

FAILED_TESTS=()

for TEST in "${TESTS_TO_RUN[@]}"; do
    echo ""
    echo "▶ Running ${TEST} ..."
    if go test -v -run "^${TEST}$" ./metadata/dbaccess/testsuite/; then
        echo "✅ ${TEST} passed."
    else
        echo "❌ ${TEST} failed."
        FAILED_TESTS+=("${TEST}")
    fi
done

echo ""
echo "=========================================="
if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo "✅ All dbaccess tests passed."
else
    echo "❌ The following tests failed:"
    for T in "${FAILED_TESTS[@]}"; do
        echo "   - ${T}"
    done
    exit 1
fi