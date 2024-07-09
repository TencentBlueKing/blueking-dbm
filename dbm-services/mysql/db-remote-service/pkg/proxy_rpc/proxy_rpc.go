// Package proxy_rpc proxy rpc 实现
package proxy_rpc

import (
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/parser"
	"fmt"
	"log/slog"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql
	"github.com/jmoiron/sqlx"
)

var proxyQueryParseCommands = []string{
	"select",
}

var proxyExecuteParseCommands = []string{
	"refresh_users",
}

// ProxyRPCEmbed proxy 实现
type ProxyRPCEmbed struct {
}

// ParseCommand proxy 解析命令
func (c *ProxyRPCEmbed) ParseCommand(command string) (*parser.ParseQueryBase, error) {
	return &parser.ParseQueryBase{
		QueryId:   0,
		Command:   command,
		ErrorCode: 0,
		ErrorMsg:  "",
	}, nil
}

// MakeConnection proxy 建立连接
func (c *ProxyRPCEmbed) MakeConnection(address string, user string, password string, timeout int, timezone string) (*sqlx.DB, error) {
	// TODO 如果连接的是业务端口（非 admin 端口），也应该设置时区？
	// tz := "loc=Local&time_zone=%27%2B08%3A00%27"
	connectParam := fmt.Sprintf("timeout=%ds", timeout)
	db, err := sqlx.Open(
		"mysql",
		fmt.Sprintf(`%s:%s@tcp(%s)/?%s`, user, password, address, connectParam),
	)

	if err != nil {
		slog.Warn("first time connect to proxy",
			slog.String("err", err.Error()),
			slog.String("address", address),
		)

		time.Sleep(2 * time.Second)

		db, err := sqlx.Open(
			"mysql",
			fmt.Sprintf(`%s:%s@tcp(%s)/?%s`, user, password, address, connectParam),
		)
		if err != nil {
			slog.Error(
				"retry connect to proxy",
				slog.String("error", err.Error()),
				slog.String("address", address),
			)
			return nil, err
		}
		return db, nil
	}

	return db, nil
}

// IsQueryCommand proxy 解析命令
func (c *ProxyRPCEmbed) IsQueryCommand(pc *parser.ParseQueryBase) bool {
	for _, ele := range proxyQueryParseCommands {
		if strings.HasPrefix(strings.ToLower(pc.Command), ele) {
			return true
		}
	}

	return false
}

// IsExecuteCommand proxy 解析命令
func (c *ProxyRPCEmbed) IsExecuteCommand(pc *parser.ParseQueryBase) bool {
	for _, ele := range proxyExecuteParseCommands {
		if strings.HasPrefix(strings.ToLower(pc.Command), ele) {
			return true
		}
	}

	return false
}

// User proxy 用户
func (c *ProxyRPCEmbed) User() string {
	return config.RuntimeConfig.ProxyAdminUser
}

// Password proxy 密码
func (c *ProxyRPCEmbed) Password() string {
	return config.RuntimeConfig.ProxyAdminPassword
}
