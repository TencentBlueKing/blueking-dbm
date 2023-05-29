// Package proxy_rpc proxy rpc 实现
package proxy_rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/parser"
	"fmt"
	"strings"
	"time"

	"github.com/go-sql-driver/mysql"
	_ "github.com/go-sql-driver/mysql" // mysql
	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slog"
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
func (c *ProxyRPCEmbed) MakeConnection(address string, user string, password string, timeout int) (*sqlx.DB, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(timeout))
	defer cancel()

	db, err := sqlx.ConnectContext(
		ctx,
		"mysql",
		fmt.Sprintf(`%s:%s@tcp(%s)/`, user, password, address),
	)

	if err != nil {
		if merr, ok := err.(*mysql.MySQLError); ok {
			if merr.Number != 1105 {
				slog.Error("connect to proxy", err, slog.String("address", address))
				return nil, merr
			}
		} else {
			slog.Error("connect to proxy", err, slog.String("address", address))
			return nil, err
		}
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
