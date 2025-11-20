#!/bin/bash

# SQL语法检查测试运行脚本

set -e

# 设置测试环境变量，跳过数据库初始化
export TESTING=true
export SKIP_DB_INIT=true
export DB_HOST=""
export DB_PORT="0"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "SQL Syntax Check Tests"
echo "=================================================="
echo ""

# 检查 tmysqlparse 是否存在
if [ ! -f "/tmysqlparse" ]; then
    echo "⚠️  Warning: /tmysqlparse not found"
    echo "   Integration tests will be skipped"
    echo "   Running in short mode..."
    echo ""
    TEST_MODE="-short"
else
    echo "✓ tmysqlparse found at /tmysqlparse"
    echo "  Running full integration tests..."
    echo ""
    TEST_MODE=""
fi

# 函数：运行测试
run_test() {
    local test_name=$1
    local test_pattern=$2
    
    echo "----------------------------------------"
    echo "Running: $test_name"
    echo "----------------------------------------"
    
    if go test -v $TEST_MODE -run "$test_pattern" 2>&1 | grep -E "(PASS|FAIL|RUN|---)" | head -20; then
        echo "✓ Test completed"
    else
        echo "✗ Test failed or skipped"
    fi
    echo ""
}

# 显示菜单
show_menu() {
    echo "Select test to run:"
    echo "  1) All tests"
    echo "  2) Basic functionality (Valid SQL)"
    echo "  3) Invalid syntax"
    echo "  4) High risk commands"
    echo "  5) Banned commands"
    echo "  6) Multi-version tests"
    echo "  7) Spider tests"
    echo "  8) Advanced features"
    echo "  9) Edge cases"
    echo " 10) Table-driven tests"
    echo "  0) Quick check (KeywordFilter only)"
    echo ""
}

# 如果有参数，直接运行对应测试
if [ $# -gt 0 ]; then
    case $1 in
        all)
            go test -v $TEST_MODE ./...
            ;;
        coverage)
            go test -v $TEST_MODE -coverprofile=coverage.out ./...
            go tool cover -html=coverage.out -o coverage.html
            echo "Coverage report generated: coverage.html"
            ;;
        *)
            go test -v $TEST_MODE -run "$1" ./...
            ;;
    esac
    exit 0
fi

# 交互式菜单
show_menu
read -p "Enter choice [0-10]: " choice

case $choice in
    1)
        echo "Running all tests..."
        go test -v $TEST_MODE ./...
        ;;
    2)
        run_test "Basic Functionality" "TestTmysqlParseFile_Do_Valid"
        ;;
    3)
        run_test "Invalid Syntax" "TestTmysqlParseFile_Do_InvalidSQL"
        ;;
    4)
        run_test "High Risk Commands" "TestTmysqlParseFile_Do_HighRiskCommands"
        ;;
    5)
        run_test "Banned Commands" "TestTmysqlParseFile_Do_BannedCommands"
        ;;
    6)
        run_test "Multi-Version" "TestTmysqlParseFile_Do_MySQL_MultiVersion"
        ;;
    7)
        run_test "Spider" "TestTmysqlParseFile_Do_Spider"
        ;;
    8)
        run_test "Advanced Features" "TestTmysqlParseFile_Do_Advanced"
        ;;
    9)
        run_test "Edge Cases" "TestTmysqlParseFile_Do_(Empty|Large|Multiple)"
        ;;
    10)
        run_test "Table-Driven Tests" "TestTmysqlParseFile_Do_TableDriven"
        ;;
    0)
        run_test "Quick Check" "TestKeywordFilter"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo "=================================================="
echo "Tests completed!"
echo "=================================================="

