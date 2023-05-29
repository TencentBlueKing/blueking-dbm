// Package proxy_user_list TODO
package proxy_user_list

import (
	"bufio"
	"context"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slog"
)

var name = "proxy-user-list"

// Checker TODO
type Checker struct {
	db *sqlx.DB
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	userListFilePath := filepath.Join(
		"/etc",
		fmt.Sprintf(`proxy_user.cnf.%d`, config.MonitorConfig.Port),
	)
	f, err := os.Open(userListFilePath)
	if err != nil {
		slog.Error("read proxy user list file", err)
		return "", err
	}
	defer func() {
		_ = f.Close()
	}()

	var usersFromFile []string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		usersFromFile = append(usersFromFile, scanner.Text())
		err := scanner.Err()
		if err != nil {
			slog.Error("scan proxy user list file", err)
			return "", err
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var usersFromQuery []string
	err = c.db.SelectContext(ctx, &usersFromQuery, `SELECT * FROM USERS`)
	if err != nil {
		slog.Error("query user list", err)
		return "", err
	}

	/*
		这种比较两个 slice, 并抽取各自独有的 element 的算法会更快, 理论上是 O(2(m+n))
		如果用传统的以一个 slice 做循环, 查找另一个 slice, 理论上是 O(mlog(n))

		BenchmarkMapIter-6              1000000000               0.001124 ns/op        0 B/op          0 allocs/op
		BenchmarkMapIter-6              1000000000               0.001228 ns/op        0 B/op          0 allocs/op
		BenchmarkMapIter-6              1000000000               0.001189 ns/op        0 B/op          0 allocs/op
		BenchmarkMapIter-6              1000000000               0.002286 ns/op        0 B/op          0 allocs/op
		BenchmarkMapIter-6              1000000000               0.001106 ns/op        0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1990 ns/op          0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1922 ns/op          0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1985 ns/op          0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1944 ns/op          0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1928 ns/op          0 B/op          0 allocs/op

		测试性能差别还是蛮大的
	*/
	stage := make(map[string]int)
	for _, u := range usersFromFile {
		stage[u] = 1
	}
	for _, u := range usersFromQuery {
		if _, ok := stage[u]; !ok {
			stage[u] = 0
		}
		stage[u] -= 1
	}

	var onlyFile, onlyQuery []string
	for k, v := range stage {
		if v == 1 {
			onlyFile = append(onlyFile, k)
		}
		if v == -1 {
			onlyQuery = append(onlyQuery, k)
		}
	}

	var msgs []string
	var onlyFileMsg string
	var onlyQueryMsg string

	if len(onlyFile) > 0 {
		onlyFileMsg = fmt.Sprintf("user only in file: %s", strings.Join(onlyFile, ","))
		msgs = append(msgs, onlyFileMsg)
	}
	if len(onlyQuery) > 0 {
		onlyQueryMsg = fmt.Sprintf("user only in mem: %s", strings.Join(onlyQuery, ","))
		msgs = append(msgs, onlyQueryMsg)
	}

	return strings.Join(msgs, "\n"), nil
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{db: cc.ProxyAdminDB}
}

// Register TODO
func Register() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return name, New
}
