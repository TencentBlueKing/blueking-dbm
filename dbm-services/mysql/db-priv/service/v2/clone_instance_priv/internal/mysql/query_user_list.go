package mysql

import (
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"errors"
	"fmt"
	"log/slog"
	"strings"
)

func QueryUserList(bkCloudId int64, addr string, excludeUsers []string, targetAddr string, logger *slog.Logger) ([]string, error) {
	targetIp := strings.Split(targetAddr, ":")[0]

	excludeUsersStr := fmt.Sprintf("'%s'", strings.Join(append(systemUsers, excludeUsers...), "', '"))
	logger.Info(
		fmt.Sprintf("query user list, address: %s, execlude users: %s", addr, excludeUsersStr),
	)
	// 必须排除掉 host = targetIp 的账号
	// account@source 克隆后会变成 account@target
	// 如果源上已经存在 account@target, 而且和 account@source 密码不一样, 就可能出问题
	// spider 4 基于 mariadb, 不写成 user as user 这样, 返回的是 User 这样的大写
	sql := fmt.Sprintf(
		`SELECT user as user, host as host FROM mysql.user WHERE user NOT in (%s) AND host <> '%s'`,
		excludeUsersStr, targetIp,
	)

	drsRes, err := drs.RPCMySQL(
		bkCloudId,
		[]string{addr},
		[]string{sql},
		false,
		600,
	)
	if err != nil {
		logger.Error(
			fmt.Sprintf("query mysql user list, address: %s, sql: %s, err: %s", addr, sql, err.Error()),
		)
		return nil, err
	}

	if drsRes[0].ErrorMsg != "" {
		logger.Error(
			fmt.Sprintf("query mysql user list, address: %s, sql: %s, err: %s", addr, sql, drsRes[0].ErrorMsg),
		)
		return nil, errors.New(drsRes[0].ErrorMsg)
	}

	if drsRes[0].CmdResults[0].ErrorMsg != "" {
		logger.Error(
			fmt.Sprintf(
				"query mysql user list, address: %s, sql: %s, err: %s",
				addr, sql, drsRes[0].CmdResults[0].ErrorMsg),
		)
		return nil, errors.New(drsRes[0].CmdResults[0].ErrorMsg)
	}

	var res []string
	for _, row := range drsRes[0].CmdResults[0].TableData {
		user := row["user"].(string)
		host := row["host"].(string)
		res = append(res, fmt.Sprintf("'%s'@'%s'", user, host))
	}

	return res, nil
}
